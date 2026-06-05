
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

class SLAM_MapWidget(QWidget):
    
    '''Placeholder widget for SLAM map display.'''
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SLAM_MapWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QLabel("SLAM MAP")
        header.setObjectName("PanelSectionHeader")
        layout.addWidget(header)