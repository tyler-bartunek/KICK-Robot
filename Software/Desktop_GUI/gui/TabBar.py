
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel


class TabBar(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TabBar")
        
        self.setFixedHeight(75)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 12, 0)
        self.layout.setSpacing(6)
        
        # Add buttons for each tab
        self.hardware_btn = QPushButton("Hardware Configuration")
        self.sensor_btn = QPushButton("Sensor Configuration")
        self.slam_btn = QPushButton("SLAM Map")
        
        
    def add_widgets(self, widgets: list[QWidget]):
        
        for widget in widgets:
            self.layout.addWidget(widget)

        