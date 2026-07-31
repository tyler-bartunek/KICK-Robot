
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

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

KEYRING_SERVICE = "kickbot_gui"


@dataclass
class RobotProfile:
    
    alias:     str
    hostname:  str
    username:  str
    workspace: str = ""   # filled in after first successful connect + detect

    def display(self) -> str:
        return f"{self.alias}  ({self.hostname})"


class RobotProfileManager:
    """
    Load, save, and retrieve robot connection profiles.
    Passwords are never stored in the JSON file.
    """

    def __init__(self):
        self._path = self._config_path()
        self._profiles: list[RobotProfile] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def profiles(self) -> list[RobotProfile]:
        return list(self._profiles)

    def add_or_update(self, profile: RobotProfile,
                      password: str | None = None,
                      remember: bool = False):
        """
        Save or update a profile. If remember=True and password is given,
        store the password in the OS keychain.
        """
        # Replace existing entry with same hostname
        self._profiles = [p for p in self._profiles
                          if p.hostname != profile.hostname]
        self._profiles.append(profile)
        self._save()

        if remember and password and KEYRING_AVAILABLE:
            keyring.set_password(KEYRING_SERVICE, profile.hostname, password)

    def remove(self, hostname: str):
        self._profiles = [p for p in self._profiles
                          if p.hostname != hostname]
        self._save()
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(KEYRING_SERVICE, hostname)
            except Exception:
                pass

    def get_password(self, hostname: str) -> str | None:
        """Retrieve stored password from keychain, or None if not saved."""
        if not KEYRING_AVAILABLE:
            return None
        try:
            return keyring.get_password(KEYRING_SERVICE, hostname)
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

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> list[RobotProfile]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return [RobotProfile(**d) for d in data]
        except Exception:
            return []

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
