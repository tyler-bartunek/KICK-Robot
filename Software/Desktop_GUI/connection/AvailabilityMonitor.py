
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from time import monotonic, sleep
import socket

from .RobotProfileManager import RobotProfileManager, RobotProfile


class RobotAvailabilityMonitor(QObject):
    
    bridge_available = pyqtSignal(str, bool)  # hostname, available

    def __init__(self, profile: RobotProfile):
        super().__init__()
        self.profile = profile
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self.track_availability)

    def start(self):
        self._thread.start()

    def track_availability(self, fast_interval=0.5, slow_interval=7.0, warmup=2.0):
        was_available = False
        print("Tracking availability")
        while True:  # tracking-lifetime condition still TBD, per earlier
            try:
                with socket.create_connection((self.profile.ip_address, self.profile.port), timeout=1):
                    if not was_available:
                        sleep(warmup)
                        print("Device available")
                        was_available = True
                        self.profile.bridge_available = True
                        self.bridge_available.emit(self.profile.hostname, True)
                    sleep(slow_interval)
            except (ConnectionRefusedError, OSError):
                if was_available:
                    self.profile.bridge_available = False
                    self.bridge_available.emit(self.profile.hostname, False)
                was_available = False
                sleep(fast_interval)
                
    def stop(self):
        self._thread.quit()
        self._thread.wait()