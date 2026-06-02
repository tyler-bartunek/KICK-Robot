from PyQt6.QtCore import QObject, pyqtSignal
from zeroconf import ServiceBrowser, Zeroconf


class RobotDiscoveryWorker(QObject):
    device_found   = pyqtSignal(str)
    device_removed = pyqtSignal(str)

    def __init__(self, service_type="_kickbot._tcp.local."):
        super().__init__()
        self.service_type = service_type
        self.zeroconf = None
        self.browser  = None

    def start_discovery(self):
        self.zeroconf = Zeroconf()
        self.browser  = ServiceBrowser(self.zeroconf, self.service_type, self)

    def stop_discovery(self):
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            self.zeroconf.close()

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.device_found.emit(info.server.rstrip('.'))

    def remove_service(self, zc, type_, name):
        self.device_removed.emit(name.split('.')[0] + ".local")

    def update_service(self, zc, type_, name):
        pass
