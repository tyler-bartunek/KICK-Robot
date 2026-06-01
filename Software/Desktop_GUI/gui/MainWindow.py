

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    
    def __init__(self):
        
        super().__init__()
        self.setWindowTitle("KICK Robot Control Panel")
        self.setGeometry(100, 100, 400, 300)
        
        # Create central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Add a label to display robot status
        self.status_label = QLabel("Robot Status: Disconnected")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Add a button to connect to the robot
        self.connect_button = QPushButton("Connect to Robot")
        layout.addWidget(self.connect_button)
        
        # Set the layout and central widget
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)