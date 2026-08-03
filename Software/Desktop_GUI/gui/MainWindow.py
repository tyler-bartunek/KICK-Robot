#Load relative paths, be able to open and parse XML files
from pathlib import Path

#PyQt Functionality
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QComboBox, QSizePolicy
)
from PyQt6.QtGui import QFont, QWindow
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtCore import pyqtSignal as signal

#Local imports: Titlebar and Toolbar
from gui._section_title_bar import TitleBar
from gui._section_toolbar import Toolbar

# Local imports: Device adding
from connection import DiscoveryWorker, RobotProfileManager

# Local imports: ROS worker
from ros_bridge.ROS_Stream import ROS_StreamWorker #REMOVE

# Local imports: central canvas
from gui._section_middle import MiddleSection

#Local imports: bottom portion
from gui._section_bottom import BottomSection


IMG_DIR = Path(__file__).parent.parent / "assets" / "img"


class MainWindow(QMainWindow):
    
    
    def __init__(self):
        super().__init__()

        self.setWindowTitle("KICK Robot Desktop")
        self.resize(1280, 720)
        self.setMinimumSize(1024, 600)
        self.setFont(QFont("Segoe UI", 10))

        # Track known robots: hostname -> (QComboBox index)
        self._known_robots: dict[str, int] = {}
        self.profile_manager = RobotProfileManager()
        self._ros_worker: ROS_StreamWorker | None = None
        self._ros_thread: QThread | None = None

        # Central widget + root layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.init_ui()
        self.apply_styles()
        # self.init_discovery()

    # ------------------------------------------------------------------ #
    #  UI Assembly                                                         #
    # ------------------------------------------------------------------ #

    def init_ui(self):
        #TODO: Implement toolbar
        # self.toolbar = Toolbar() 
        
        #Add the title bar, connect relevant signals
        self.title_bar = TitleBar(IMG_DIR / "KICK_shoeprint_logo.png")
        self.title_bar.add_robot_button.clicked.connect(self._on_robot_add_click)
        self.title_bar.robot_combo.currentTextChanged.connect(self._on_robot_selected)
        self.main_layout.addWidget(self.title_bar)

        self.middle_section = MiddleSection()
        self.main_layout.addLayout(self.middle_section, stretch=4)

        self.bottom_section = BottomSection()
        self.main_layout.addLayout(self.bottom_section, stretch=1)
        

    # ------------------------------------------------------------------ #
    #  Discovery                                                         #
    # ------------------------------------------------------------------ #

    # def _on_robot_add_click(self):
        
    #     #Open the AddRobotWizard dialog to add a new robot profile
    #     add_wizard = AddRobotWizard(self.profile_manager)
        
    #     add_wizard.exec()
    
    def _discover_devices(self):
        
        #Initialize the DiscoveryWorker to discover devices on the network
        self.discovery_worker = DiscoveryWorker()
        self.discovery_worker.device_found.connect(self._on_device_found)
        
    def _on_robot_selected(self, hostname: str):
        if hostname == "No robots found":
            self._set_status(connected=False)
            self._teardown_ros_worker()
            return
 
        self._set_status(connected=False, label="connecting…")
        self._teardown_ros_worker()   # clean up any previous connection
        self._init_ros_worker(hostname)
 
    def _init_ros_worker(self, hostname: str):
        
        self._ros_thread = QThread(self)
        self._ros_worker = ROS_StreamWorker()
        self._ros_worker.moveToThread(self._ros_thread)
 
        # Start connection when thread starts
        self._ros_thread.started.connect(lambda: self._ros_worker.connect(host=hostname, port=9090))
 
        # Wire bus_state -> RightPanel
        self._ros_worker.bus_state_updated.connect(self.right_panel.refresh_devices)
        
        #Now to Status_strip
        self._ros_worker.bus_state_updated.connect(self.status_strip.update_bus)
        self._ros_worker.battery_updated.connect(self.status_strip.update_battery)
        self._ros_worker.cmd_vel_active.connect(self.status_strip.update_cmdvel)
        
        #Connect the fault log
        self._ros_worker.log_message.connect(self.fault_log.update_faults)
 
        # Wire velocity commands -> ROS publisher
        self.control.velocity_command.connect(
            lambda velocity: self._ros_worker.publish_velocity(velocity))
 
        self._ros_thread.start()
        self._set_status(connected=True)
 
    def _teardown_ros_worker(self):
        if self._ros_worker is not None:
            self._ros_worker.disconnect()
        if self._ros_thread is not None:
            self._ros_thread.quit()
            self._ros_thread.wait()
        self._ros_worker = None
        self._ros_thread = None
 
    # ------------------------------------------------------------------
    # Update closeEvent to also teardown ROS:
    # ------------------------------------------------------------------
    
    def closeEvent(self, event):
        self._teardown_ros_worker()
        #TODO: Figure out what to do with the wizard
        super().closeEvent(event)

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
