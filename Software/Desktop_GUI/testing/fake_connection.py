
from connection import RobotAvailabilityMonitor, DNSWorker, RobotProfileManager


class FakeAvailabilityMonitor(RobotAvailabilityMonitor):
    """
    A fake implementation of the RobotAvailabilityMonitor class for testing purposes.
    """
    def __init__(self):
        super().__init__()
        self.available_robots = []
    
    def update(self):
        """
        Update the list of available robots. This method is called periodically.
        """
        # For testing, we can simulate the availability of robots
        # For example, we can add a fake robot to the list
        self.available_robots.append("FakeRobot1")
        
class FakeDNSWorker(DNSWorker):
    
    """
    A fake implementation of the DNSWorker class for testing purposes.
    """
    def __init__(self):
        super().__init__()
        self.discovered_robots = []
    
    def update(self):
        """
        Update the list of discovered robots. This method is called periodically.
        """
        # For testing, we can simulate the discovery of robots
        # For example, we can add a fake robot to the list
        self.discovered_robots.append("FakeRobot1")