
from PyQt6.QtCore import QObject, pyqtSignal
import roslibpy
import socket
from time import sleep

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



class ROS_StreamWorker(QObject):
    """
    Manages the ROS connection and subscriptions, and emits signals to update the GUI.
    """
    # Define signals to communicate with the GUI
    connection_failed = pyqtSignal(str)
    bus_state_updated = pyqtSignal(list)  # Emitted when a new bus state message is received
    battery_updated = pyqtSignal(float) #Emitted when a new battery state is received
    last_vel_updated = pyqtSignal(dict)
    cmd_vel_active = pyqtSignal(bool) #Emitted when the cmd_vel publisher is advertised or unadvertised
    log_message = pyqtSignal(str) #Emitted for logging messages to the GUI

    def __init__(self, parent=None):
        
        super().__init__(parent)
        self.client = None
        self.battery_subscriber = None
        self.bus_state_subscriber = None
        self.cmd_vel_publisher = None

    def connect(self, host='localhost', port=9090):
        
        
        #Initialize the ROS client
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()
        print("ROS connection established")

        # Subscribe to bot_state topic
        #TODO: Define these messages on this side perhaps?
        self.bot_state_subscriber = roslibpy.Topic(self.client, 'bot_state', 'kickbot_interfaces/msg/BotState')
        self.bot_state_subscriber.subscribe(self._bot_state_callback)
        
        # Set to publish to cmd_vel topic
        self.cmd_vel_publisher = roslibpy.Topic(self.client, "kickbot/cmd_vel", 'geometry_msgs/Twist')
        self.cmd_vel_publisher.advertise()
        
        self.cmd_vel_active.emit(self.cmd_vel_publisher.is_advertised)
        

    def _bot_state_callback(self, message: dict):
        """
        Parse BotState and emit bot_state_updated(list[dict]).
 
        Expected ROS message fields:
            active_devices : bool[6]  — True = slot occupied
            device_ids     : int[6]   — hardware ID per slot
            voltage        : float    — voltage readout from ADC for battery monitoring
            linear_vel     : float[3] — linear velocity (x, y, z)
            angular_vel    : float[3] — angular velocity (x, y, z)
 
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
        voltage = message.get('voltage', 3.3)
        
        directions = ['x', 'y', 'z']
        vel_type = ['linear', 'angular']
        vel_default = {vel:{basis:0.0 for basis in directions} for vel in vel_type}
        velocity = message.get('velocity', vel_default)
        
        self.battery_updated.emit(voltage)
        self.last_vel_updated.emit(velocity)
 
        devices = []
        for slot in range(6):
            if not active[slot]:
                continue
 
            hw_id      = ids[slot]
 
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
        
        
    def disconnect(self):
        """Clean shutdown — unsubscribe, unadvertise, close connection."""
        if self.bot_state_subscriber:
            self.bot_state_subscriber.unsubscribe()
        if self.cmd_vel_publisher:
            self.cmd_vel_publisher.unadvertise()
        if self.client and self.client.is_connected:
            self.client.terminate()
        