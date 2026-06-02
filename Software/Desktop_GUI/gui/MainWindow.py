from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSizePolicy
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, Qt

from discovery.RobotDiscovery import RobotDiscoveryWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("KICK Robot Desktop")
        self.resize(1280, 720)
        self.setMinimumSize(1024, 600)
        self.setFont(QFont("Segoe UI", 10))

        # Track known robots: hostname -> (QComboBox index)
        self._known_robots: dict[str, int] = {}

        # Central widget + root layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.init_ui()
        self.apply_styles()
        self.init_discovery()

    # ------------------------------------------------------------------ #
    #  UI Assembly                                                         #
    # ------------------------------------------------------------------ #

    def init_ui(self):
        self.title_bar = self.build_title_bar()
        self.main_layout.addWidget(self.title_bar)

        self.middle_section = self.build_middle_section()
        self.main_layout.addLayout(self.middle_section, stretch=4)

        self.bottom_section = self.build_bottom_section()
        self.main_layout.addLayout(self.bottom_section, stretch=1)

    def build_title_bar(self) -> QWidget:
        container = QWidget()
        container.setObjectName("TitleBar")
        container.setFixedHeight(40)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        title = QLabel("KICK Robot Desktop")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addStretch()

        # Robot selector — populated by discovery signals
        self.robot_combo = QComboBox()
        self.robot_combo.setObjectName("RobotCombo")
        self.robot_combo.setMinimumWidth(180)
        self.robot_combo.addItem("No robots found")
        self.robot_combo.currentTextChanged.connect(self._on_robot_selected)
        layout.addWidget(self.robot_combo)

        # Connection status dot + label
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDotDisconnected")
        layout.addWidget(self.status_dot)

        self.status_label = QLabel("disconnected")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

        return container

    def build_middle_section(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(1)

        # Center workspace: tabs + rail canvas + PID strip
        center_container = QWidget()
        center_container.setObjectName("CenterWorkspace")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(QLabel("[ Tab Bar ]"))
        center_layout.addWidget(QLabel("[ Rail Canvas ]"), stretch=1)
        center_layout.addWidget(QLabel("[ PID Strip ]"))

        # Right sidebar: module library + detected devices
        right_container = QWidget()
        right_container.setObjectName("RightPanel")
        right_container.setFixedWidth(190)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(QLabel("[ Module Library ]"))
        right_layout.addWidget(QLabel("[ Detected Devices ]"), stretch=1)

        layout.addWidget(center_container, stretch=1)
        layout.addWidget(right_container)
        return layout

    def build_bottom_section(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(1)

        # Bottom left: fault log | orientation | control
        bottom_left = QWidget()
        bottom_left.setObjectName("BottomLeft")
        bl_layout = QHBoxLayout(bottom_left)
        bl_layout.setContentsMargins(10, 8, 10, 8)
        bl_layout.setSpacing(14)
        bl_layout.addWidget(QLabel("[ Fault Log ]"), stretch=1)
        bl_layout.addWidget(QLabel("[ Orientation ]"), stretch=1)
        bl_layout.addWidget(QLabel("[ Control ]"), stretch=1)

        # Bottom right: launch profile
        bottom_right = QWidget()
        bottom_right.setObjectName("BottomRightLaunch")
        bottom_right.setFixedWidth(190)
        br_layout = QVBoxLayout(bottom_right)
        br_layout.setContentsMargins(10, 8, 10, 8)
        br_layout.addWidget(QLabel("[ Launch Profile ]"))

        layout.addWidget(bottom_left, stretch=1)
        layout.addWidget(bottom_right)
        return layout

    # ------------------------------------------------------------------ #
    #  Discovery                                                           #
    # ------------------------------------------------------------------ #

    def init_discovery(self):
        """
        Moves the discovery worker onto a QThread so it never blocks
        the main (UI) thread. The worker's signals are connected to
        slots here on the main thread — PyQt6 queues the calls safely.
        """
        self._discovery_thread = QThread(self)
        self._discovery_worker = RobotDiscoveryWorker(
            service_type="_kickbot._tcp.local."
        )
        self._discovery_worker.moveToThread(self._discovery_thread)

        # Wire thread start → worker start
        self._discovery_thread.started.connect(
            self._discovery_worker.start_discovery
        )

        # Wire worker signals → UI slots (safe: cross-thread via Qt queue)
        self._discovery_worker.device_found.connect(self._on_device_found)
        self._discovery_worker.device_removed.connect(self._on_device_removed)

        self._discovery_thread.start()

    def _on_device_found(self, hostname: str):
        if hostname in self._known_robots:
            return  # Already listed

        # Remove the placeholder if this is the first real robot
        if "No robots found" in [
            self.robot_combo.itemText(i)
            for i in range(self.robot_combo.count())
        ]:
            self.robot_combo.clear()
            self._known_robots.clear()

        self.robot_combo.addItem(hostname)
        self._known_robots[hostname] = self.robot_combo.count() - 1

    def _on_device_removed(self, hostname: str):
        idx = self._known_robots.pop(hostname, None)
        if idx is not None:
            self.robot_combo.removeItem(idx)
            # Rebuild index map after removal
            self._known_robots = {
                self.robot_combo.itemText(i): i
                for i in range(self.robot_combo.count())
            }

        if self.robot_combo.count() == 0:
            self.robot_combo.addItem("No robots found")

    def _on_robot_selected(self, hostname: str):
        if hostname == "No robots found":
            self._set_status(connected=False)
            return
        # TODO: initiate roslibpy connection to hostname:9090
        self._set_status(connected=False, label=f"connecting…")

    def _set_status(self, connected: bool, label: str | None = None):
        if connected:
            self.status_dot.setObjectName("StatusDotConnected")
            self.status_label.setText(label or "connected")
        else:
            self.status_dot.setObjectName("StatusDotDisconnected")
            self.status_label.setText(label or "disconnected")
        # Force QSS re-evaluation after objectName change
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    # ------------------------------------------------------------------ #
    #  Cleanup                                                             #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        """Ensure background thread is stopped cleanly on window close."""
        self._discovery_worker.stop_discovery()
        self._discovery_thread.quit()
        self._discovery_thread.wait()
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    #  Styles                                                              #
    # ------------------------------------------------------------------ #

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            QWidget#TitleBar {
                background-color: #111111;
                border-bottom: 1px solid #2a2a2a;
            }
            QLabel#TitleLabel {
                font-size: 13px;
                font-weight: 600;
                color: #f0f0f0;
            }
            QComboBox#RobotCombo {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 2px 8px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QComboBox#RobotCombo::drop-down { border: none; }
            QLabel#StatusDotConnected    { color: #1D9E75; font-size: 10px; }
            QLabel#StatusDotDisconnected { color: #555555; font-size: 10px; }
            QLabel#StatusLabel {
                font-size: 11px;
                color: #888888;
            }
            QWidget#CenterWorkspace {
                background-color: #1e1e1e;
                border-right: 1px solid #2a2a2a;
            }
            QWidget#RightPanel {
                background-color: #161616;
            }
            QWidget#BottomLeft {
                background-color: #161616;
                border-top: 1px solid #2a2a2a;
            }
            QWidget#BottomRightLaunch {
                background-color: #111111;
                border-top: 1px solid #2a2a2a;
                border-left: 1px solid #2a2a2a;
            }
        """)
