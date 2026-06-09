
from PyQt6.QtCore import QObject, pyqtSignal
import roslibpy


class ROS_StreamWorker(QObject):
    """
    Manages the ROS connection and subscriptions, and emits signals to update the GUI.
    """
    # Define signals to communicate with the GUI
    bus_state_updated = pyqtSignal(dict)  # Emitted when a new bus state message is received

    def __init__(self, parent=None):
        
        super().__init__(parent)
        self.client = None
        self.bus_state_subscriber = None

    def connect(self, host='localhost', port=9090):
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()
        print("ROS connection established")

        # Subscribe to bus_state topic
        self.bus_state_subscriber = roslibpy.Topic(self.client, '/bus_state', 'kick_msgs/BusState')
        self.bus_state_subscriber.subscribe(self._bus_state_callback)
        
        # Subscribe to vel_cmd topic
        self.vel_cmd_publisher = roslibpy.Topic(self.client, "vel_cmd", 'geometry_msgs/Twist')
        self.vel_cmd_publisher.publish(self._velocity_msg_callback)
        
        #Connect to config service (just listen in?)
        self.kinematic_config_listener = roslibpy.Service(self.client, 'ConfigUpdate', 'kick_interfaces/srv/ConfigUpdate')

    def _bus_state_callback(self, message):
        # Process the bus state message and emit signals to update the GUI
        print("Received bus state:", message)
        
    def _velocity_msg_callback(self, message):
        #Send the new velocity command to the device
        
        pass
        