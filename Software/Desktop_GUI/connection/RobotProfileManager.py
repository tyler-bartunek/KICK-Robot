
"""
Manages saved robot profiles (alias, hostname, username, workspace).
Profiles are stored in %APPDATA%/KICKRobot/robots.json on Windows.
Passwords are stored separately in the OS keychain via keyring.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from ros_bridge import ROS_StreamWorker
 

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

KEYRING_SERVICE = "kickbot_gui"


@dataclass
class RobotProfile:
    
    hostname:  str
    port:  int
    workspace: str = ""   # filled in after first successful connect + detect
    ssh_enabled: bool = False
    has_focus: bool = False
    hardware_connection_points: Optional[dict[int, tuple[int, int]]] = None  # {module_id: (board_connection_point, offset from default for board_connection_point)}

    if ssh_enabled:
        ssh_username: str = "pi"

    def display(self) -> str:
        return f"{self.hostname}:{self.port}"

class RobotProfileManager:
    """
    Manage the list of connected robots, including saving and loading settings from disk.
    """

    def __init__(self):
        self._path = self._config_path()
        self._bridges: dict[str, ROS_StreamWorker] = {} #TODO: Update load to also update this list
        self._profiles: list[RobotProfile] = self._load_profiles()
        
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def profiles(self) -> list[RobotProfile]:
        return list(self._profiles)

    def add_or_update(self, profile: RobotProfile,
                      ros_worker: ROS_StreamWorker,
                      password: str | None = None,
                      remember: bool = False):
        """
        Save or update a profile. If remember=True and password is given,
        store the password in the OS keychain.
        """
        
        # self._profiles = [p for p in self._profiles
        #                   if p.hostname != profile.hostname]
        # self._profiles.append(profile)
        
        for p_idx, p in enumerate(self._profiles):
            
            # Replace existing entry with same hostname
            if p.hostname != profile.hostname:
                self._profiles[p_idx] = p
                self._bridges[profile.hostname] = ros_worker
                
            self._profiles.append(profile)
        self._save()

        if remember and password and profile.ssh_enabled and KEYRING_AVAILABLE:
            keyring.set_password(KEYRING_SERVICE, profile.hostname, password)
            
    def change_focus(self, hostname: str) -> None:
        
        for p in self._profiles:
            if p.hostname != hostname:
                p.has_focus = False
            else:
                p.has_focus = True

    def remove(self, hostname: str):
        self._profiles = [p for p in self._profiles
                          if p.hostname != hostname]
        self._bridges.pop(hostname) #Remove the stream_worker
        self._save()
        if self._profiles[hostname].ssh_enabled and KEYRING_AVAILABLE:
            try:
                keyring.delete_password(KEYRING_SERVICE, hostname)
            except Exception:
                pass

    def get_password(self, hostname: str) -> str | None:
        """Retrieve stored password from keychain, or None if not saved."""
        if not KEYRING_AVAILABLE:
            return None
        try:
            if self._profiles[hostname].ssh_enabled:
                return keyring.get_password(KEYRING_SERVICE, hostname)
            else:
                return None
        except Exception:
            return None

    def update_workspace(self, hostname: str, workspace: str):
        """Update workspace path after successful auto-detect."""
        for p in self._profiles:
            if p.hostname == hostname:
                p.workspace = workspace
                break
        self._save()

    def get(self, hostname: str) -> RobotProfile | None:
        return next((p for p in self._profiles
                     if p.hostname == hostname), None)
        
    def get_bridge(self, hostname: str) -> ROS_StreamWorker:
        
        return self._bridges[hostname]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_profiles(self) -> list[RobotProfile]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            #Ensure no robot has focus to start upon load
            profiles = [RobotProfile(**d) for d in data]
            for p in profiles:
                p.has_focus = False
            return profiles
        except Exception:
            return []
        
    def _load_ros_workers(self) -> dict[str, ROS_StreamWorker]:
        
        for p in self._profiles:
            self._bridges[p.hostname] = ROS_StreamWorker()
            self._bridges[p.hostname].connect()
        

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(p) for p in self._profiles], indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _config_path() -> Path:
        # %APPDATA% on Windows, ~/.config on Linux/Mac
        base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
        return base / "KICKRobot" / "robots.json"
