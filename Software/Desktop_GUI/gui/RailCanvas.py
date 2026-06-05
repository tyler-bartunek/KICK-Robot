
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout


class RailCanvas(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RailCanvas")