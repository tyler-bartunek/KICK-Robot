
import zeroconf

from .RobotProfileManager import RobotProfileManager, RobotProfile


class DiscoveryWorker:
    
    #DiscoveryWorker is a class that handles the discovery of KICK Robot devices on the network using zeroconf.
    def __init__(self, service_type: str = "_kick-robot._tcp.local."):
        
        self.service_type = service_type
        self.zeroconf = zeroconf.Zeroconf()
        self.browser = zeroconf.ServiceBrowser(self.zeroconf, self.service_type, handlers=[self.on_service_state_change])
        self.discovered_services = {}