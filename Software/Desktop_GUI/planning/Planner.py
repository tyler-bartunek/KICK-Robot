from PyQt6.QtCore import QObject, pyqtSignal

class Planner(QObject):
    
    # Emitted on every state change: (vx, vy, omega)
    velocity_command = pyqtSignal(dict)
    
    ZERO_VEL = {"linear":{
            "x":0.0,
            "y":0.0,
            "z":0.0},
            "angular":{
                "x":0.0,
                "y":0.0,
                "z":0.0}
            }
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.velocity = {"linear":{"x":0.0, "y":0.0, "z":0.0}, 
                                 "angular":{"x":0.0, "y":0.0, "z":0.0}}
    
    def _send(self):
        self.velocity_command.emit(self.velocity)