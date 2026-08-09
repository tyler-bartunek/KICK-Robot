
from PyQt6.QtCore import QObject, pyqtSignal

import zeroconf

from .RobotProfileManager import RobotProfileManager, RobotProfile


class DNSWorker(QObject):
    
    #DNSWorker is a class that handles the discovery of KICK-robots on the local network using Zeroconf (mDNS) protocol.
    # It listens for services of type "_kick._tcp.local." and maintains a list of discovered robots.
    # It also provides methods to start and stop the discovery process, as well as to retrieve the list of discovered robots.
    def __init__(self, parent = None):
        
        super().__init__(parent)
        self.zeroconf = zeroconf.Zeroconf()
        self.browser = None
        self.discovered_robots = []
        self.robot_profile_manager = RobotProfileManager()
        
        #Start the discovery process when the DNSWorker is initialized.
        self.start_discovery()
        
    def start_discovery(self):
        # Start the discovery process by creating a ServiceBrowser that listens for "_kickbot._tcp.local." services.
        if self.zeroconf.started:
            self.zeroconf.close()  # Close any existing Zeroconf instance before starting a new one
        self.zeroconf.start()
        self.browser = zeroconf.ServiceBrowser(self.zeroconf, "_kickbot._tcp.local.", handlers=[self.on_service_state_change])
        
    def on_service_state_change(self, service_type, name, state_change):
        # This method is called whenever a service state changes (added, removed, or updated).
        if state_change == self.zeroconf.ServiceStateChange.Added:
            info = self.zeroconf.get_service_info(service_type, name)
            if info:
                hostname = info.server
                port = info.port
                robot_profile = RobotProfile(hostname=hostname, port=port)
                self.robot_profile_manager.add_robot(robot_profile)
                self.discovered_robots.append(robot_profile)
                print(f"Discovered robot: {hostname}:{port}")
        elif state_change == self.zeroconf.ServiceStateChange.Removed:
            # Handle service removal if needed
            self.on_service_removed(service_type, name)
            pass
        elif state_change == self.zeroconf.ServiceStateChange.Updated:
            # Handle service updates if needed
            pass
        
    def on_service_removed(self, service_type, name):
        # This method is called when a service is removed from the network.
        print(f"Service removed: {name}")
        # Remove the robot from the discovered list and the profile manager
        self.discovered_robots = [robot for robot in self.discovered_robots if robot.hostname != name]
        self.robot_profile_manager.remove_robot(name)
        
    def on_window_close(self):
        # This method should be called when the application window is closed to clean up resources.
        self.zeroconf.close()
        