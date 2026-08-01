
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot


class FaultLogWidget(QWidget):
    
    '''Placeholder widget for fault log display.'''
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FaultLogWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QLabel("FAULT LOG")
        header.setObjectName("PanelSectionHeader")
        layout.addWidget(header)
        
        #Later: listen to robot status updates from ROS_StreamWorker and display faults in a scrollable list. For now, just a placeholder.
        layout.addWidget(QLabel("No faults detected."))
        
    def update_faults(self, message: str):
        '''Update the fault log with a new message.'''
        #For now, just print the message to the console. Later, this will update the GUI.
        print(f"Fault log update: {message}")