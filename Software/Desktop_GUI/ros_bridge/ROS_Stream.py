
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
        
        docker_started = False
        
        #Send trigger to get socket message to Pi side.
        while not docker_started:
            try:
                docker_started = self._emit_docker_trigger(host, port)
                
            except ConnectionRefusedError:
                print(f"Unable to connect to device {host}:{port}")
                break
            
        
        #Initialize the ROS client
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()
        print("ROS connection established")

        # Subscribe to bus_state topic
        #TODO: Define these messages on this side perhaps?
        self.bus_state_subscriber = roslibpy.Topic(self.client, 'bus_state', 'kickbot_interfaces/msg/BusState')
        self.bus_state_subscriber.subscribe(self._bus_state_callback)
        
        #Subscribe to the battery topic
        self.battery_subscriber = roslibpy.Topic(self.client, 'battery-info', 'kickbot_interfaces/msg/BatteryInfo')
        
        # Set to publish to cmd_vel topic
        self.cmd_vel_publisher = roslibpy.Topic(self.client, "kickbot/cmd_vel", 'geometry_msgs/Twist')
        self.cmd_vel_publisher.advertise()
        
        self.cmd_vel_active.emit(self.cmd_vel_publisher.is_advertised())
        
    def _emit_docker_trigger(self, host='localhost', port = 9090) -> bool:
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            
            client.connect((host, port))
            
            start_signal = "START"
            client.sendall(start_signal.encode('utf-8'))
            
            #Listen, see if we get the right response
            if client.recv(1024) == b"STARTING":
                print(f"Connecting to {host}:{port}, docker starting...")
                sleep(30) #TODO: Implement logic to know that the docker container has actually started
                return True
            
            return False
            
        
    def _battery_callback(self, message):
        
        self.battery_updated.emit(message)
        

    def _bus_state_callback(self, message: dict):
        """
        Parse BusState and emit bus_state_updated(list[dict]).
 
        Expected ROS message fields:
            active_devices : bool[6]  — True = slot occupied
            device_ids     : int[6]   — hardware ID per slot
            voltage        : float    — voltage readout from ADC for battery monitoring
 
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
                "voltage": voltage
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
        