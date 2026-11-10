"""
FakeStreamWorker: a drop-in ROS_StreamWorker for GUI development without a Pi.

It subclasses the real worker, so the real parsing code (_bot_state_callback,
log_callback) runs unchanged and all signals are inherited -- the fake cannot
drift from the real signal surface. Only the transport (roslibpy) is replaced.
"""
from PyQt6.QtCore import QTimer

from .ROS_Stream import ROS_StreamWorker


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


def _bot_state(ids, voltage=12.0):
    """Build a BotState-shaped dict. `ids` maps slot -> hardware ID for occupied slots."""
    return {
        "active_paths": [slot in ids for slot in range(6)],
        "device_ids": [ids.get(slot, 0) for slot in range(6)],
        "voltage": voltage,
        "velocity": {"linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                     "angular": {"x": 0.0, "y": 0.0, "z": 0.0}},
    }


def default_scenario(tick):
    """Return a list of (topic, message) to emit on this tick.

    Timeline (one tick per interval): nothing attached -> left wheel -> right
    wheel -> unknown ID 0xF3 appears -> unknown unplugged. Voltage sags slowly.
    Log lines at each event, covering every severity level.
    """
    voltage = max(10.5, 12.0 - tick * 0.01)
    events = []
    if tick < 10:
        ids = {}
    elif tick < 20:
        ids = {0: 0x02}
    elif tick < 30:
        ids = {0: 0x02, 1: 0x03}
    elif tick < 40:
        ids = {0: 0x02, 1: 0x03, 3: 0xF3}
    else:
        ids = {0: 0x02, 1: 0x03}

    events.append(("bot_state", _bot_state(ids, voltage)))

    log_at = {
        10: (20, "comms_hub", "Device discovered on path 0 with ID 2"),
        20: (20, "comms_hub", "Device discovered on path 1 with ID 3"),
        30: (30, "comms_hub", "Checksum failure detected on path 3"),
        32: (40, "motor_send", "Unrecognized device configuration"),
        34: (50, "comms_hub", "Fault detected on path 3"),
        5: (10, "comms_hub", "Polling bus"),
    }
    if tick in log_at:
        level, name, msg = log_at[tick]
        events.append(("rosout", {"level": level, "name": name, "msg": msg}))
    return events


class FakeStreamWorker(ROS_StreamWorker):

    def __init__(self, scenario=default_scenario, interval_ms=50, parent=None):
        super().__init__(parent)
        self._scenario = scenario
        self._interval_ms = interval_ms
        self._timer = None
        self._tick = 0

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