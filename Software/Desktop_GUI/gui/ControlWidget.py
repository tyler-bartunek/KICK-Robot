from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal


from planning import *


class ControlWidget(QWidget):
    """
    Keyboard / gamepad selector + D-pad jog buttons + live vel readout.
    Keyboard arrow keys are captured at window level and forwarded here.
    """

    # Emitted on every state change: (vx, vy, omega)
    velocity_command = pyqtSignal(dict)
    
    CONTROL_MODES = {"Manual":Manual_Control}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ControlWidget")

        self.velocity = {"linear":{"x":0.0, "y":0.0, "z":0.0}, 
                         "angular":{"x":0.0, "y":0.0, "z":0.0}}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        header_title = QLabel("CONTROL")
        header_title.setObjectName("PanelSectionHeader")
        
        self.control_selector = self.build_control_toggle()
        self.control_selector.currentTextChanged.connect(self.build_widget_from_selection)
        
        header_layout.addWidget(header_title)
        header_layout.addWidget(self.control_selector)
        
        outer.addWidget(header)
        
        #Build widget from current selection: Manual by default
        self.control_widget = self.build_widget_from_selection()
        outer.addWidget(self.control_widget)
        outer.addStretch()
        
    def build_control_toggle(self) -> QComboBox:
        
        dropdown = QComboBox()
        
        #Populate Combo box with Control modes
        dropdown.addItems(self.CONTROL_MODES.keys())
        
        return dropdown
    
    def build_widget_from_selection(self) -> QWidget:
        
        mode = self.control_selector.currentText()
        control_widget = self.CONTROL_MODES[mode](self)
        
        return control_widget
