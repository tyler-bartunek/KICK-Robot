

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