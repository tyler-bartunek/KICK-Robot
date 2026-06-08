
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget, QFrame
from PyQt6.QtGui import QWindow


class _Sensor(QWidget):
    
    
    def __init__(self, sensor_name:str, parent = None):
        
        super().__init__(parent)
        
        #Store the name as an attribute
        self.full_name = sensor_name
        
        #Simplify the name
        simple_name = sensor_name.strip(" ")
        self.setObjectName(simple_name)  
        
        self.item_container = QHBoxLayout(self)
        
        name = QLabel(sensor_name)
        
        self.configure_button = QPushButton("Configure")
        self.remove_button = QPushButton("Remove")
        
        self.item_container.addWidget(name)
        self.item_container.addWidget(self.configure_button)
        self.item_container.addWidget(self.remove_button)
        

class SensorConfigWidget(QWidget):
    
    '''Sensor configuration UI, which allows users to select which sensors are active from a fixed list of devices, appending it to the active sensor list.
    The active sensor list allows the user to configure the settings of each sensor, and also allows the user to remove sensors from the active list.'''
    
    sensor_names = ["6-axis IMU", "9-axis IMU", "Ultrasonic Distance", "LIDAR"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SensorConfigWidget")
        
        #initialize sensor dict
        self.sensor_dict = {sensor:-1 for sensor in self.sensor_names}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(14)

        #Selection list
        selection_list = self.build_selection_list()
        
        #Active sensor list
        active_list_section = self.build_active_list_widget()
        
        outer.addWidget(selection_list)
        outer.addWidget(active_list_section)
        
        
    def build_selection_list(self) -> QWidget:
        
        selections = QWidget()
        sl = QVBoxLayout(selections)
        
        selection_list_title = QLabel("Select Sensor: ")
        self.slist = QListWidget()
        self.slist.setObjectName("SelectionList")
        self.slist.setMinimumWidth(180)
        for sensor in self.sensor_names:
            self.slist.addItem(sensor)
            
        #Add pushbutton to push to active list
        add_button = QPushButton("Add Sensor")
        add_button.clicked.connect(self._on_add_button_press)
        
        sl.addWidget(selection_list_title)
        sl.addWidget(self.slist)
        sl.addWidget(add_button)
        sl.addStretch(1)
        
        return selections
        
    def build_active_list_widget(self) -> QWidget:
        
        a_list = QWidget()
        al = QVBoxLayout(a_list)
        
        active_sensor_title = QLabel("Active Sensors")
        
        al.addWidget(active_sensor_title)
        
        #Add the list as its own widget
        list_container = QWidget()
        self.active_list = QVBoxLayout(list_container)
        
        al.addWidget(list_container)
        al.addStretch(1) 
        
        return a_list
        
    def _on_add_button_press(self):
        
        current = self.slist.currentItem()
        current_name = current.text()
        
        #Give the sensor a unique name
        new_sensor_name = self.generate_unique_active(current_name)
        
        #Append to active list, connect the configure and remove buttons
        new_sensor = _Sensor(new_sensor_name)
        new_sensor.remove_button.clicked.connect(lambda sensor: self._on_remove_button_press(new_sensor))
        
        self.active_list.addWidget(new_sensor)
        
    def _on_remove_button_press(self, sensor:_Sensor):
        
        #Remove the sensor from the widget
        self.active_list.removeWidget(sensor)
           
                
    def generate_unique_active(self, new_sensor: str):
        
        name = f"{new_sensor}_{self.sensor_dict[new_sensor]+1}"
        self.sensor_dict[new_sensor] += 1
                
        return name
    
    
                