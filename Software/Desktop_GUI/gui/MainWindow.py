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
from gui._section_title_bar import TitleBar, RobotItem
from gui._section_toolbar import Toolbar

# Local imports: Device adding
from connection import DNSWorker, RobotProfile, RobotProfileManager

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
        self._ros_threads: dict[str, QThread] | None = None
        self._dns_worker: DNSWorker | None = None
        self._dns_thread: QThread | None = None

        # Central widget + root layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.init_ui()
        self._discover_devices()
        self.apply_styles()
        

    # ------------------------------------------------------------------ #
    #  UI Assembly                                                         #
    # ------------------------------------------------------------------ #

    def init_ui(self):
        #TODO: Implement toolbar
        self.toolbar = Toolbar(self) 
        self.main_layout.addWidget(self.toolbar)
        
        #Add the title bar, connect relevant signals
        self.title_bar = TitleBar(IMG_DIR / "KICK_shoeprint_logo.png")
        # self.title_bar.robot_combo.currentTextChanged.connect(self._on_device_found)
        self.main_layout.addWidget(self.title_bar)

        self.middle_section = MiddleSection()
        self.main_layout.addLayout(self.middle_section, stretch=4)

        self.bottom_section = BottomSection()
        self.main_layout.addLayout(self.bottom_section, stretch=1)
        

    # ------------------------------------------------------------------ #
    #  Discovery                                                         #
    # ------------------------------------------------------------------ #
    def _discover_devices(self):
        
        #Initialize the DiscoveryWorker to discover devices on the network
        self._dns_thread = QThread(self)
        self.dns_worker = DNSWorker()
        self.dns_worker.moveToThread(self._dns_thread)
        self._dns_thread.start()
        self.dns_worker.start_discovery()
        self.dns_worker.device_discovered.connect(self._on_device_found)
        
    def _on_device_found(self, hostname: str):
            
        if hostname in self._known_robots:
            return  # Already listed

        #Instantiate a RobotProfile and RobotItem for the discovered robot, connect signals, and add to the combo box
        profile = RobotProfile(hostname=hostname, port=self.dns_worker.port)
        robot_item = RobotItem(name=hostname, profile = profile)
        self.profile_manager.add_or_update(profile, ROS_StreamWorker())
        robot_item.connect_robot.connect(self._on_robot_selected)
        robot_item.remove_robot.connect(self._on_device_removed)
        
        self.title_bar.robot_combo.add_robot(robot_item)
        # self.title_bar.robot_combo.addItem(hostname)
        self._known_robots[hostname] = profile
    
    def _on_device_removed(self, hostname: str):
        
        self.title_bar.robot_combo.remove_robot(hostname)
        self._known_robots.pop(hostname, None)
        self.profile_manager.remove(hostname)

        
    def _on_robot_selected(self, hostname: str):
        
        if hostname == "No robots found":
            self._set_status(connected=False)
            self._teardown_ros_worker()
            return
 
        #Set status flags
        self._set_status(connected=False, label="connecting…")
        self.profile_manager.change_focus(hostname)
        
        self._teardown_ros_worker(hostname)   # clean up any previous connection
        self._init_ros_worker(hostname)
 
    def _init_ros_worker(self, hostname: str):
        
        self._ros_threads[hostname] = QThread(self)
        ros_worker = self.profile_manager.get_bridge(hostname)
        ros_worker.moveToThread(self._ros_threads[hostname])
 
        # Start connection when thread starts
        self._ros_threads[hostname].started.connect(lambda: self._ros_worker.connect(host=hostname, port=9090))
 
        # Wire bus_state -> RightPanel
        ros_worker.bus_state_updated.connect(self.middle_section.right_panel.refresh_devices)
        
        #Now to Status_strip
        ros_worker.bus_state_updated.connect(self.middle_section.status_strip.update_bus)
        ros_worker.battery_updated.connect(self.middle_section.status_strip.update_battery)
        ros_worker.cmd_vel_active.connect(self.middle_section.status_strip.update_cmdvel)
        
        #Connect the fault log
        ros_worker.log_message.connect(self.bottom_section.fault_log.update_faults)
 
        # Wire velocity commands -> ROS publisher
        self.bottom_section.control.velocity_command.connect(
            lambda velocity: ros_worker.publish_velocity(velocity))
 
        self._ros_threads[hostname].start()
        self._set_status(connected=True)
 
    def _teardown_ros_worker(self, hostname:str = None):
        
        try:
            if hostname:
                ros_worker = self.profile_manager.get_bridge(hostname)
                ros_thread = self._ros_threads[hostname]
                if ros_worker is not None:
                    ros_worker.disconnect()
                if ros_thread is not None:
                    ros_thread.quit()
                    ros_thread.wait()
                    
                #Remove the worker and thread objects from profile management 
                self.profile_manager.pop(hostname)
                self._ros_threads.pop(hostname)
            
            #If hostname not specified, close all workers and threads recursively 
            else:
                for p in self.profile_manager._profiles:
                    self._teardown_ros_worker(p.hostname)
                
        except KeyError: #Ros worker not found at index, nothing to do
            if self._ros_threads or self.profile_manager._bridges:
                print(f"Could not find either specified worker or thread at {hostname}")
            pass
        
        # self._ros_worker = None
        # self._ros_thread = None
 
    # ------------------------------------------------------------------
    # Update closeEvent to also teardown ROS:
    # ------------------------------------------------------------------
    def _teardown_dns_worker(self):
        if self.dns_worker is not None:
            self.dns_worker.on_window_close()
        if self._dns_thread is not None:
            self._dns_thread.quit()
            self._dns_thread.wait()
        self.dns_worker = None
        self._dns_thread = None
    
    def closeEvent(self, event):
        self._teardown_ros_worker()
        self._teardown_dns_worker()
        #TODO: Figure out what to do with the wizard
        super().closeEvent(event)


    def _set_status(self, connected: bool, label: str | None = None):
        if connected:
            self.title_bar.status_dot.setObjectName("StatusDotConnected")
            self.title_bar.status_label.setText(label or "connected")
        else:
            self.title_bar.status_dot.setObjectName("StatusDotDisconnected")
            self.title_bar.status_label.setText(label or "disconnected")
        # Force QSS re-evaluation after objectName change
        self.title_bar.status_dot.style().unpolish(self.title_bar.status_dot)
        self.title_bar.status_dot.style().polish(self.title_bar.status_dot)


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
