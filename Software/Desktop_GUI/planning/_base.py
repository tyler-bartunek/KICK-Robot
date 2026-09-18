

from PyQt6.QtCore import QObject

from connection import RobotProfileManager
from ros_bridge import ROS_StreamWorker


from .Planner import Planner
from .manual import Manual_Control

widget_types = {'manual':Manual_Control}


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
        self.planner:Planner = None  # This will be set when the planner is initialized
        
    def assign_planner(self, type:str):
        
        self.planner = widget_types[type].planner
        self.planner.velocity_command.connect(lambda velocity: self.ros_bridge._velocity_msg_callback(velocity))
        


class SessionManager:
    
    def __init__(self):
        
        self._sessions: list[Session] = []
        
    def add_or_update(self, session:Session):
        #Add the session if it isn't already in the list
        self._sessions = [s for s in self._sessions if s.name != session.name]
        self._sessions.append(session)
        
    def get_session(self, hostname:str):
        
        session_names = [s.name for s in self._sessions]
        if hostname in session_names:
            matching_sessions = [s for s in self._sessions if s.name == hostname]
            return matching_sessions[0]
        else:
            pass #TODO: Decide if we want this to automatically make a session or throw an error