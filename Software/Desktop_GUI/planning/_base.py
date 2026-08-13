

from PyQt6.QtCore import QObject, pyqtSignal

from connection import RobotProfileManager
from ros_bridge import ROS_StreamWorker


class Session(QObject):
    """
    A Session represents a single connection to a robot, and is responsible for managing the state of that connection.
    It holds references to the robot profile, and any other relevant state information. Management of ROS bridge 
    connections is to be determined, as it is not clear if the ROS bridge should persist when the GUI
    does not have the robot selected, or if the planner will need access to the ROS bridge in order to do what
    it needs to do. For now, the ROS bridge is managed by the GUI and is not part of the Session.
    """
    
    def __init__(self, hostname: str, bridge:ROS_StreamWorker, parent=None):
        self.name = hostname
        self.ros_bridge = bridge # This will be set when the ROS bridge is connected
        self.planner = None  # This will be set when the planner is initialized
        
    def assign_planner(self):
        
        pass
        
        
class SessionManager:
    
    def __init__(self):
        
        self._sessions: list[Session] = None
        
    def add_or_update(self, profile_manager:RobotProfileManager):
        #Always called after updating the profile manager
        self._sessions = [Session(p.hostname, p.bridge) for p in profile_manager]