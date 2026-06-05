
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

    def _bus_state_callback(self, message):
        # Process the bus state message and emit signals to update the GUI
        print("Received bus state:", message)