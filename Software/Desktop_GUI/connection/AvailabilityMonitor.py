
from PyQt6.QtCore import QObject, pyqtSignal, QThread


from time import sleep
import socket

from .RobotProfileManager import RobotProfileManager, RobotProfile


class RobotAvailabilityMonitor(QObject):
    
    bridge_available = pyqtSignal(str, bool)  # hostname, available
    request_shutdown = pyqtSignal(QThread, bool)

    def __init__(self, profile: RobotProfile):
        super().__init__()
        self.profile = profile
        
        self.request_shutdown.connect(self.stop)

    def track_availability(self, fast_interval=0.5, slow_interval=7.0, warmup=2.0):
        was_available = False
        self.profile.bridge_available = True  # Assume available until proven otherwise
        
        while self.profile.bridge_available:  # tracking-lifetime condition still TBD, per earlier
            try:
                with socket.create_connection((self.profile.ip_address, self.profile.port), timeout=1):
                    if not was_available:
                        sleep(warmup)
                        # print("Device available")
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
                
    def stop(self, thread:QThread, confirm:bool):
        
        if confirm:
            self.profile.bridge_available = False
            thread.quit()
            thread.wait()
            
            # Clean up thread to avoid "Current thread is not the object's thread" error
            thread.deleteLater()
        