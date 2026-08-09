
#File navigation functionality
from pathlib import Path

#PyQt Functionality
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout,
    QLabel, QPushButton, QComboBox
)

from connection import RobotProfileManager, RobotProfile


class TitleBar(QWidget):
    
    def __init__(self, img:Path, parent = None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        
        title = QLabel()
        title.setText(
                        f"<h1><img src='{img}' width='30' height='30'> KICK Robot Desktop </h1>"
                        )
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addStretch()
        
        # self.add_robot_button = QPushButton("Add Robot")
        # self.add_robot_button.setObjectName("RobotWizardButton")
        # self.add_robot_button.clicked.connect(self._on_robot_add_click)
        # layout.addWidget(self.add_robot_button)

        # Robot selector — populated by discovery signals
        self.robot_combo = QComboBox()
        self.robot_combo.setObjectName("RobotCombo")
        self.robot_combo.setMinimumWidth(180)
        self.robot_combo.addItem("No robots found")
        # self.robot_combo.currentTextChanged.connect(self._on_robot_selected)
        layout.addWidget(self.robot_combo)

        # Connection status dot + label
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDotDisconnected")
        layout.addWidget(self.status_dot)

        self.status_label = QLabel("disconnected")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)
        
    def add_robot_item(self, name:str, robot: RobotProfile) -> None:
        """Add a robot to the combo box if it doesn't already exist."""
        if name not in [self.robot_combo.itemText(i) for i in range(self.robot_combo.count())]:
            self.robot_combo.addItem(name)
        
    
class RobotItem:
    """A simple data structure to hold robot information for the combo box."""
    def __init__(self, name:str, profile:RobotProfile):
        self.name = name
        self.profile = profile