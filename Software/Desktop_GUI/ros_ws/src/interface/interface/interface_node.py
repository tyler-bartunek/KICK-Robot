
#Import PyQt6 tools
from PyQt6.QtCore import QObject, pyqtSignal

#Import ROS tooling
import rclpy
from rclpy.node import Node

#Import message formats
from geometry_msgs.msg import Twist
from kickbot_interfaces.msg import BusState, BatteryInfo


#Basic definitions
_MODULE_TYPE_MAP: dict[int, str] = {
    0x00: "NA",   # Not applicable, no connection
    0x01: "ECH",  # Echo- Debug case
    0x02: "MW-L",   # Left Mecanum Wheel
    0x03: "MW-R",   # Right Mechanum Wheel
    0x04: "QL-A",   # Quadruped leg A
    0x05: "QL-B",   # Quadruped leg B
}
 
def _hw_id_to_type(hw_id: int) -> str:
    return _MODULE_TYPE_MAP.get(hw_id, f"UNK({hw_id:#04x})")


# How many bytes of device_data are allocated per device slot
DEVICE_DATA_STRIDE = 4


class InterfaceNode(Node):
    """
    Manages the ROS connection and subscriptions, and emits signals to update the GUI.
    """
    # Define signals to communicate with the GUI
    bus_state_updated = pyqtSignal(list)  # Emitted when a new bus state message is received
    battery_updated = pyqtSignal(float) #Emitted when a new battery state is received
    # cmd_vel_active = pyqtSignal(bool) #Emitted when the cmd_vel publisher is advertised or unadvertised
    # log_message = pyqtSignal(str) #Emitted for logging messages to the GUI
    
    def __init__(self, robot_namespace:str):
        #Set it up as a node
        super().__init__('interface_node')
        #TODO: Create the custom message formats on gui-side,  
        # Subscribe to bus_state topic
        self.bus_state_subscriber = self.create_subscription(BusState, robot_namespace + '/bus_state', self._bus_state_callback, 10)
        
        #Subscribe to the battery topic
        self.battery_subscriber = self.create_subscription(BatteryInfo, robot_namespace + '/battery-info', self._battery_callback, 10)
        
        # Set to publish to cmd_vel topic
        timer_period = 1. / 20. #Publish at 20 Hz
        self.cmd_vel_publisher = self.create_publisher(Twist, robot_namespace + '/cmd_vel')
        self.timer = self.create_timer(timer_period, self._velocity_msg_callback)
        
    def _battery_callback(self, message):
            
        self.battery_updated.emit(message)
            
    
    def _bus_state_callback(self, message: dict):
        """
        Parse BusState and emit bus_state_updated(list[dict]).
    
        Expected ROS message fields:
            active_devices : bool[6]  — True = slot occupied
            device_ids     : int[6]   — hardware ID per slot
            device_data    : int[24]  — 4 bytes per device slot
    
        Emitted list item format (matches RightPanel.refresh_devices):
            {
                "address":  "0xNN",
                "position": "N",
                "type":     "MW" | "SJ" | ...,
                "fault":    bool,
            }
        """
        active = message.get('active_devices', [False] * 6)
        ids    = message.get('device_ids',     [0]     * 6)
        data   = message.get('device_data',    [0]     * 24)
    
        devices = []
        for slot in range(6):
            if not active[slot]:
                continue
    
            hw_id      = ids[slot]
            offset     = slot * DEVICE_DATA_STRIDE
            slot_bytes = data[offset : offset + DEVICE_DATA_STRIDE]
    
            # # Fault detection — adapt to your firmware's convention.
            # # Current assumption: byte 0 bit 0 = fault flag.
            # fault = bool(slot_bytes[0] & 0x01) if slot_bytes else False
    
            devices.append({
                "address":  f"0x{hw_id:02X}",
                "position": str(slot),
                "type":     _hw_id_to_type(hw_id),
            })
    
        self.bus_state_updated.emit(devices)
        
    def _velocity_msg_callback(self, velocity:dict[str,dict[str,float]]):
        #Send the new velocity command to the device 
        self.cmd_vel_publisher.publish(velocity)
        
