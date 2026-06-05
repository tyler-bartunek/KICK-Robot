
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget, QFrame


class _Sensor(QWidget):
    
    
    def __init__(self, sensor_name:str, parent = None):
        
        super().__init__(parent)
        #Replace spaces with _
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
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SensorConfigWidget")
        
        self.active_sensor_names = []

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(14)

        #Selection list
        selection_list = QWidget()
        sl = QVBoxLayout(selection_list)
        
        selection_list_title = QLabel("Select Sensor: ")
        self.slist = QListWidget()
        self.slist.setObjectName("SelectionList")
        self.slist.setMinimumWidth(180)
        self.slist.addItem("6-axis IMU")
        self.slist.addItem("9-axis IMU")
        self.slist.addItem("Ultrasonic Distance")
        self.slist.addItem("LIDAR")
        
        #Add pushbutton to push to active list
        add_button = QPushButton("Add Sensor")
        add_button.clicked.connect(self._on_add_button_press)
        
        sl.addWidget(selection_list_title)
        sl.addWidget(self.slist)
        sl.addWidget(add_button)
        sl.addStretch(1)
        
        #Active sensor list
        active_list = QWidget()
        self.al = QVBoxLayout(active_list)
        
        active_sensor_title = QLabel("Active Sensors")
        
        self.al.addWidget(active_sensor_title)
        
        self.al.addStretch(1)
        
        outer.addWidget(selection_list)
        outer.addWidget(active_list)
        
    def _on_add_button_press(self):
        
        current = self.slist.currentItem()
        current_name = current.text()
        
        #Give the sensor a unique name
        new_sensor_name = self.generate_unique_active(current_name)
        
        #Append to active list
        self.al.addWidget(_Sensor(new_sensor_name))
        
                
    def generate_unique_active(self, new_sensor: str):
        
        if len(self.active_sensor_names) == 0:
            name = new_sensor + "_0"
            self.active_sensor_names.append(new_sensor + "_0")
            return name
        
        for sensor in self.active_sensor_names:
            sensor_type = sensor.split("_")[0]
            num_of_type = int(sensor.split("_")[1])
            
            if (sensor_type.lower() == new_sensor.lower()):
                name = new_sensor + "_" + str(num_of_type + 1)
                self.active_sensor_names.append(name)
            else:
                name = new_sensor + "_0"
                
        return name
                