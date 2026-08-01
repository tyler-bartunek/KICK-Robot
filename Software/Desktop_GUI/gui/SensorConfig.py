from pathlib import Path
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QLabel, QPushButton, QListWidget, QDialog, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal


sensor_names = ["6-axis IMU", "9-axis IMU", "LIDAR", "Ultrasonic Distance"]
sensor_config_path = Path(__file__).parent.parent / "assets" / "_define" / "sensors"


class _Sensor(QWidget):
    
    def __init__(self, sensor_name:str, parent = None):
        
        super().__init__(parent)
        
        #Store the name as an attribute
        self.full_name = sensor_name
        
        self.configured = False
        
        #Simplify the name
        simple_name = sensor_name.strip(" ")
        self.setObjectName(simple_name)  
        
        self.item_container = QHBoxLayout(self)
        
        name = QLabel(sensor_name)
        
        self.configure_button = QPushButton("Configure")
        self.remove_button = QPushButton("Remove")
        
        self.configure_button.clicked.connect(self._on_configure_click)
        
        self.item_container.addWidget(name)
        self.item_container.addWidget(self.configure_button)
        self.item_container.addWidget(self.remove_button)
        
    def _on_configure_click(self):
        
        configure_window = _Sensor_Setting_Window(self)
        
        configure_window.exec()
        
        
class _Sensor_Setting_Window(QDialog):
    
    def __init__(self, sensor:_Sensor, parent = None):
        
        #Set up the basics of the dialog window
        super().__init__(parent)
        self.sensor = sensor
        self.setObjectName("ConfigWindow")
        self.setWindowTitle(f"{self.sensor.full_name} Configuration")
        
        #Put the setting files into a searchable dict
        self._assemble_setting_dict()
        
        #Initialize the settings dict
        self.settings = {}
        
        #Setup the layout
        outer = QVBoxLayout(self)
        
        outer.addWidget(self._build_parameter_section())
        
        outer.addStretch(1)
        
        save_button = QPushButton("Save Sensor Settings")
        save_button.clicked.connect(self._on_save)
        
        outer.addWidget(save_button)
        
    def _build_parameter_section(self) -> QWidget:
        
        #Make the QFormLayout
        container = QWidget()
        form = QFormLayout(container)
        
        self.param_fields = {}
        
        root = self._fetch_root(form)
        
        if root:
            for param in root.findall('parameter'):
                
                param_name = param.attrib.get('name')
                param_label = param.attrib.get('label')
                param_type = param.attrib.get('type')
                param_default = param.attrib.get('default')
                
                entry_box = QLineEdit()
                if self.sensor.configured:
                    entry_box.setText(f"{self.sensor.settings[param_name]}")
                else:
                    entry_box.setText(f"{param_default}")
                    
                form.addRow(param_label, entry_box)
                
                self.param_fields[param_name] = entry_box
            
        return container
    
    def _extract_settings(self):
        
        return {name: field.text() for name, field in self.param_fields.items()}      
    
    def _fetch_root(self, form = None):    
        
        #Try and extract parameters
        identifier = self.sensor.full_name.split('_')[0]
        
        root = None
        
        try:
            file = ET.parse(self.sensor_setting_dict[identifier])
            root = file.getroot()
        except FileNotFoundError as f:
            if form:
                form.addRow(QLabel(f"No recognized module settings found: {f}"))
        except ET.ParseError as e:
            if form:
                form.addRow(QLabel(f"Unable to parse settings file: {e}"))
            
        return root
    
    def _on_save(self):
        
        self.sensor.settings = self._extract_settings()
        self.sensor.configured = True
        self.accept()
        
        

    def _assemble_setting_dict(self) -> None:
        
        setting_folder_contents = sensor_config_path.iterdir()
        settings_files = [file for file in setting_folder_contents if file.is_file()]
        
        if len(settings_files) != len(sensor_names):
            raise(KeyError("Mismatch between number of sensor types and expected number of settings files"))

        self.sensor_setting_dict = {sensor:file for sensor, file in zip(sensor_names, settings_files)}
        
        
        

class SensorConfigWidget(QWidget):
    
    '''Sensor configuration UI, which allows users to select which sensors are active from a fixed list of devices, appending it to the active sensor list.
    The active sensor list allows the user to configure the settings of each sensor, and also allows the user to remove sensors from the active list.'''
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SensorConfigWidget")
        
        #initialize sensor dict
        self.sensor_dict = {sensor:-1 for sensor in sensor_names}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(14)

        #Selection list
        selection_list = self.build_selection_list()
        
        #Active sensor list
        active_list_section = self.build_active_list_widget()
        
        outer.addWidget(selection_list)
        outer.addWidget(active_list_section)
        outer.addStretch(1)
        
        
    def build_selection_list(self) -> QWidget:
        
        selections = QWidget()
        sl = QVBoxLayout(selections)
        
        selection_list_title = QLabel("Select Sensor: ")
        self.slist = QListWidget()
        self.slist.setObjectName("SelectionList")
        self.slist.setMinimumWidth(180)
        for sensor in sensor_names:
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
        sensor.setParent(None)
        sensor.deleteLater()
           
                
    def generate_unique_active(self, new_sensor: str):
        
        name = f"{new_sensor}_{self.sensor_dict[new_sensor]+1}"
        self.sensor_dict[new_sensor] += 1
                
        return name
    
    
                