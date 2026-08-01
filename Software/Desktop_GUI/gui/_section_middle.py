
#PyQt Functionality
from PyQt6.QtWidgets import (
    QWidget, QStackedWidget, 
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QComboBox
)

# Local imports: Side panel, status strip, tab bar
from gui.StatusStrip import StatusStrip
from gui.TabBar import TabBar
from gui.RightPanel import RightPanel

# Local imports: main area widgets
from gui.RailCanvas import RailCanvas
from gui.SensorConfig import SensorConfigWidget
from gui.SLAM_Map import SLAM_MapWidget


class MiddleSection(QHBoxLayout):
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.setSpacing(1)
        
        # Center workspace: tabs + rail canvas
        center_container = QWidget()
        center_container.setObjectName("CenterWorkspace")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        self.central_canvas_layout = self.build_central_stacked_window()
        
        tab_bar = TabBar()
        tab_bar.hardware_btn.clicked.connect(lambda: self.central_canvas_layout.setCurrentIndex(0))
        tab_bar.sensor_btn.clicked.connect(lambda: self.central_canvas_layout.setCurrentIndex(1))
        tab_bar.slam_btn.clicked.connect(lambda: self.central_canvas_layout.setCurrentIndex(2))
        tab_bar.add_widgets([tab_bar.hardware_btn, tab_bar.sensor_btn, tab_bar.slam_btn])
        tab_bar.layout.addStretch()
    
        center_layout.addWidget(tab_bar)
        self.status_strip = StatusStrip()
        center_layout.addWidget(self.status_strip)
        
        #Add the main window's central canvas (stacked widget) to the center layout
        center_layout.addWidget(self.central_canvas_layout, stretch=1)

        # Right sidebar: module library + detected devices
        right_container = QWidget()
        right_container.setObjectName("RightPanel")
        right_container.setFixedWidth(190)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.right_panel = RightPanel()
        right_layout.addWidget(self.right_panel, stretch=1)

        self.addWidget(center_container, stretch=1)
        self.addWidget(right_container)
        
    def build_central_stacked_window(self) -> QStackedWidget:
            
        #Create the central stacked window, which will hold the different tab contents
        stacked_widget = QStackedWidget()
        
        self.rail_canvas = RailCanvas()
        self.sensor_canvas = SensorConfigWidget()
        self.slam_canvas = SLAM_MapWidget()
        
        stacked_widget.addWidget(self.rail_canvas)
        stacked_widget.addWidget(self.sensor_canvas)
        stacked_widget.addWidget(self.slam_canvas)    
        
        return stacked_widget