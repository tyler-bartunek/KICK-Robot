
import roslibpy


class FakeModule:
    
    def __init__(self, id: int):
        self.id = id
        pass
    
    def update(self):
        pass


class FakeRobot:
    
    message = {"bot_state":
        {"active_devices": [False] * 6,
        "device_ids": [0] * 6,
        "voltage": 3.3,
        "velocity": {
            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.0}},
        "rosout": {"level": 0, "name": "", "msg": "", "topics": []}
        }
    }
    
    def __init__(self):
        
        self.connected_modules: list[FakeModule] = [None] * 6
        self.module_ids: list[int] = [0] * 6
        
        self.robot_velocity = {"linear": {"x": 0.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}}
        self.voltage = 3.3
        pass
    
    def update(self, cmd: dict):
        """
        Update event for all connected modules. This handles data transfers to/from fake modules, 
        and updates the necessary messages for the fake ROS streams. 
        
        For simplicity for testing, we'll have the robot velocity be exactly the commanded velocity, and the voltage will be a constant value. 
        In a real robot, these would be updated based on sensor readings and control algorithms.
        
        Args:
            cmd (dict): The commanded velocity for the robot, in the format:
                {
                    "linear": {"x": float, "y": float, "z": float},
                    "angular": {"x": float, "y": float, "z": float}
                }
        """
        
        self.robot_velocity = cmd
        # Update each module: Do later, for now we'll just let the fake robot echo back the commanded velocity and a constant voltage. 
        self.message["bot_state"]["velocity"] = self.robot_velocity
        self.message["bot_state"]["voltage"] = self.voltage
        self.message["bot_state"]["active_devices"] = [module is not None for module in self.connected_modules]
        self.message["bot_state"]["device_ids"] = [module.id if module is not None else 0 for module in self.connected_modules] 
        # for module in self.connected_modules:
        #     if module is not None:
        #         module.update()
    
    def connect_module(self, module: FakeModule, slot: int):
        
        self.connected_modules[slot] = module
        self.module_ids[slot] = module.id
    
    def disconnect_module(self, slot: int):
       
        if self.connected_modules[slot]:
            self.connected_modules[slot] = None

    
