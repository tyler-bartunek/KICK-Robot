from pathlib import Path

#Common directories
IMG_DIR = Path(__file__).parent.parent / "assets" / "img"
MODULE_DEF_DIR = Path(__file__).parent.parent / "assets" / "_define" / "modules"
SENSOR_DEF_DIR = Path(__file__).parent.parent / "assets" / "_define" / "sensors"

#Define the basic module types for the rail canvas and the ROS bridge. 
MODULE_TYPE_MAP: dict[int, str] = {
    0x00: "NA",   # Not applicable, no connection
    0x01: "ECH",  # Echo- Debug case
    0x02: "MW-L",   # Left Mecanum Wheel
    0x03: "MW-R",   # Right Mechanum Wheel
    0x04: "QL-A",   # Quadruped leg A
    0x05: "QL-B",   # Quadruped leg B
}

MODULE_TYPE_ALT_NAMES = {
    "ECH": "Echo",
    "MW-L": "Wheels L",
    "MW-R": "Wheels R",
    "QL-A": "Quad Leg A",
    "QL-B": "Quad Leg B",
}

MODULE_COLOR_MAP: dict[str, str] = {
    "ECH": "#5BA8A0",  # muted teal — sensor/comms feel
    "MW-L": "#7B68EE",  # slate purple
    "MW-R": "#9B88FF",  # lighter purple — related to L
    "QL-A": "#E07B54",  # terracotta
    "QL-B": "#C45A35",  # darker terracotta
}

MODULE_FILE_MAP: dict[str, str] = {
    "MW-L":"mecanum",
    "MW-R":"mecanum",
    "QL-A":"quad",
    "QL-B":"quad",
}

#Control widget types for the planning GUI.
# Might need some thinking to keep things from getting too circular. 
# As-is, concerns are separated somewhat. It would be nice to migrate the widget dict
# to live here, but it might not be tractable. 