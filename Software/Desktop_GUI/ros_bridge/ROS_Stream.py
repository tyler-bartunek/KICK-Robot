
from PyQt6.QtCore import QObject, pyqtSignal
import roslibpy


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


class ROS_StreamWorker(QObject):
    """
    Manages the ROS connection and subscriptions, and emits signals to update the GUI.
    """
    # Define signals to communicate with the GUI
    bus_state_updated = pyqtSignal(list)  # Emitted when a new bus state message is received
    battery_updated = pyqtSignal(float) #Emitted when a new battery state is received
    cmd_vel_active = pyqtSignal(bool) #Emitted when the cmd_vel publisher is advertised or unadvertised
    log_message = pyqtSignal(str) #Emitted for logging messages to the GUI

    def __init__(self, parent=None):
        
        super().__init__(parent)
        self.client = None
        self.battery_subscriber = None
        self.bus_state_subscriber = None
        self.cmd_vel_publisher = None

    def connect(self, host='localhost', port=9090):
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()
        print("ROS connection established")

        # Subscribe to bus_state topic
        self.bus_state_subscriber = roslibpy.Topic(self.client, 'kickbot/bus_state', 'kickbot_interfaces/msg/BusState')
        self.bus_state_subscriber.subscribe(self._bus_state_callback)
        
        #Subscribe to the battery topic
        self.battery_subscriber = roslibpy.Topic(self.client, 'battery-info', 'kickbot_interfaces/msg/BatteryInfo')
        
        # Set to publish to cmd_vel topic
        self.cmd_vel_publisher = roslibpy.Topic(self.client, "kickbot/cmd_vel", 'geometry_msgs/Twist')
        self.cmd_vel_publisher.advertise()
        
        self.cmd_vel_active.emit(self.cmd_vel_publisher.is_advertised())
        
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
        
        
    def disconnect(self):
        """Clean shutdown — unsubscribe, unadvertise, close connection."""
        if self.bus_state_subscriber:
            self.bus_state_subscriber.unsubscribe()
        if self.cmd_vel_publisher:
            self.cmd_vel_publisher.unadvertise()
        if self.client and self.client.is_connected:
            self.client.terminate()
        