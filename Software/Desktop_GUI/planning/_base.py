

from PyQt6.QtCore import QObject, pyqtSignal

from ros_bridge import ROS_StreamWorker


from .Planner import Planner
from .manual import Manual_Control

widget_types = {'manual':Manual_Control}


class Session(QObject):
    """
    A Session represents a single connection to a robot, and is responsible for managing the state of that connection.
    It holds the robot hostname, the ROS bridge connection for that robot, and keeps track of what planner instance the 
    robot is connected to. May get refactored as time goes on to add flexibility/profile info, hard to say. 
    """
    
    def __init__(self, hostname: str, bridge:ROS_StreamWorker, parent=None):
        self.name = hostname
        self.ros_bridge = bridge # This will be set when the ROS bridge is connected
        self.planner:Planner = None  # This will be set when the planner is initialized
        
    def assign_planner(self, type:str):
        
        self.planner = widget_types[type].planner
        self.planner.velocity_command.connect(lambda velocity: self.ros_bridge._velocity_msg_callback(velocity))
        


class SessionManager(QObject):
    
    invalid_session_id = pyqtSignal(str)
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self._sessions: list[Session] = []
        
    def add_or_update(self, session:Session):
        #Add the session if it isn't already in the list
        self._sessions = [s for s in self._sessions if s.name != session.name]
        self._sessions.append(session)
        
    def get_session(self, hostname:str):
        
        session_names = [s.name for s in self._sessions]
        if hostname in session_names:
            matching_sessions = [s for s in self._sessions if s.name == hostname]
            return matching_sessions[0] #Assumption that only one item will kick back
        else:
            #TODO: figure out what to do with a non-matching hostname. 
            # Technically, this should be impossible with the code as-intended.
            # Only issue is if this is possible as-written for us to end up here.
            
            #For now, let's set this to send something to the logger.
            self.invalid_session_id.emit(f"No control session exists for {hostname}")
            pass 