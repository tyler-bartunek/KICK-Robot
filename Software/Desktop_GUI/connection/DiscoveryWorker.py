
from PyQt6.QtCore import QObject, pyqtSignal

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange

from .RobotProfileManager import RobotProfileManager, RobotProfile


class DNSWorker(QObject):
    
    #DNSWorker is a class that handles the discovery of KICK-robots on the local network using Zeroconf (mDNS) protocol.
    # It listens for services of type "_kick._tcp.local." and maintains a list of discovered robots.
    # It also provides methods to start and stop the discovery process, as well as to retrieve the list of discovered robots.
    
    device_discovered = pyqtSignal(str)  # Emitted when a new robot is discovered, passing the hostname
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        self.zeroconf = Zeroconf()
        self.browser = None
        
        #Start the discovery process when the DNSWorker is initialized.
        self.start_discovery()
        
    def start_discovery(self):
        # Start the Zeroconf service browser to discover KICK-robots on the local network.
        self.browser = ServiceBrowser(self.zeroconf, "_kickbot._tcp.local.", handlers=[self.on_service_state_change])
        
    def on_service_state_change(self, zeroconf, service_type, name, state_change):
        # This method is called whenever a service state changes (added, removed, or updated).
        #TODO: Implement the logic to handle service state updates
        service_state_behavior = {
            ServiceStateChange.Added: self.on_service_added,
            ServiceStateChange.Updated: self.on_service_updated,
        }
        
        service_state_behavior.get(state_change, lambda *args: None)(service_type, name)

    def on_service_added(self, service_type, name):
        
        info = self.zeroconf.get_service_info(service_type, name)
        if info:
            self.hostname = info.server
            self.ip_address = info.parsed_addresses()[0]
            self.port = info.port
            
            print(f"Discovered robot: {self.hostname}:{self.port}")
            self.device_discovered.emit(self.hostname)  # Emit signal to notify that a new robot has been discovered
        
    def on_service_updated(self, service_type, name):
        # This method is called when a service is updated on the network.
        print(f"Service updated: {name}")
        
    def on_window_close(self):
        # This method should be called when the application window is closed to clean up resources.
        self.zeroconf.close()
        