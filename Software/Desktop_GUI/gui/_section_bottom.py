

#PyQt Functionality
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QComboBox
)


#Local imports: bottom widgets
from gui.FaultLog import FaultLogWidget
from gui.OrientationWidget import OrientationWidget
from gui.ControlWidget import ControlWidget


class BottomSection(QHBoxLayout):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setSpacing(1)

        # Bottom left: fault log | orientation | control
        bottom_left = QWidget()
        bottom_left.setObjectName("BottomLeft")
        bl_layout = QHBoxLayout(bottom_left)
        bl_layout.setContentsMargins(10, 8, 10, 8)
        bl_layout.setSpacing(14)
        self.fault_log = FaultLogWidget()
        bl_layout.addWidget(self.fault_log, stretch=1)
        
        self.control = ControlWidget()
        self.orientation = OrientationWidget()
        bl_layout.addWidget(self.orientation, stretch=1)
        bl_layout.addWidget(self.control, stretch=1)

        self.addWidget(bottom_left, stretch=1)
