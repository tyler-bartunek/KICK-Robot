"""
FakeStreamWorker: a drop-in ROS_StreamWorker for GUI development without a Pi.

It subclasses the real worker, so the real parsing code (_bot_state_callback,
log_callback) runs unchanged and all signals are inherited -- the fake cannot
drift from the real signal surface. Only the transport (roslibpy) is replaced.
"""
from PyQt6.QtCore import QTimer

from ros_bridge.ROS_Stream import ROS_StreamWorker
from .fake_robot import FakeRobot


class FakeROSClient:
    """Stands in for roslibpy.Ros: just the attributes/methods the worker touches."""

    def __init__(self):
        self.is_connected = False

    def run(self):
        self.is_connected = True

    def terminate(self):
        self.is_connected = False


class FakeTopic:
    """Stands in for roslibpy.Topic. Records publishes so tests can assert on them."""

    def __init__(self, client, name, message_type):
        self.client = client
        self.name = name
        self.message_type = message_type
        self.is_advertised = False
        self.published = []
        self._callback = None

    def subscribe(self, callback):
        self._callback = callback

    def unsubscribe(self):
        self._callback = None

    def advertise(self):
        self.is_advertised = True

    def unadvertise(self):
        self.is_advertised = False

    def publish(self, message):
        self.published.append(message)



class FakeStreamWorker(ROS_StreamWorker):

    def __init__(self, robot: FakeRobot, interval_ms=50, parent=None):
        super().__init__(parent)
        self._interval_ms = interval_ms
        self._timer = None
        self._tick = 0
        self._robot = robot

    def connect(self, host="localhost", port=9090):
        self.client = FakeROSClient()
        self.client.run()

        self.bot_state_subscriber = FakeTopic(self.client, "/bot_state", "kickbot_interfaces/msg/BotState")
        self.bot_state_subscriber.subscribe(self._bot_state_callback)
        self.rosout_subscriber = FakeTopic(self.client, "/rosout", "rcl_interfaces/msg/Log")
        self.rosout_subscriber.subscribe(self.log_callback)
        self.cmd_vel_publisher = FakeTopic(self.client, "/cmd_vel", "geometry_msgs/Twist")
        self.cmd_vel_publisher.advertise()
        self.cmd_vel_active.emit(self.cmd_vel_publisher.is_advertised)

        # Created here so it lives in whichever thread connect() runs on
        # (the worker thread when started via QThread.started).
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._emit_next)
        self._timer.start(self._interval_ms)

    def _emit_next(self):
        for topic, message in self._scenario(self._tick):
            self.inject(topic, message)
        self._tick += 1

    def inject(self, topic, message):
        """Push one message through the real callback for that topic (also usable from tests)."""
        if topic == "bot_state":
            self._bot_state_callback(message)
        elif topic == "rosout":
            self.log_callback(message)

    def disconnect(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        super().disconnect()