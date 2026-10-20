"""
Implementation of a simple XML settings parser for the KICK-Robot GUI application.

Should work with either the sensor or module settings XML files. 

The module settings generally have a structure like this:
<module>
    <ind_settings>
      //Settings for indivdual modules. 
      //Example of a float parameter
      <parameter name="parameter_name" label="Parameter Label" type="float"
      default="20.0" unit="parameter_unit" min="min_value" max="max_value"/>
      //Example of a parameter with a dropdown menu of options
        <parameter name="parameter_name" label="Parameter Label" type="dropdown" default="option1">
                <option value="option1">Option 1</option>
                <option value="option2">Option 2</option>
            </parameter>
    </ind_settings>
    <config_settings>
        //Similar to the ind_settings, but this is for kinematic configuration-level parameters
        //E.g. for a mecanum module, the matrix-type parameter for the P controller gains
        <parameter name="P" label="Proportional Gain" type="matrix" rows="3" cols="3" default="0.1,0,0;0,0.1,0;0,0,0.1"/>
    </config_settings>
</module>

The sensor settings generally have a structure like this:
<sensor name="sensor_name">
    <parameter name="I2C_address" label="I2C Address" type="hex" default="0x68"/>
    <parameter name="accel_range" label="Accelerometer Range" type="enum" default="2g">
        <option value="2g">±2g</option>
        <option value="4g">±4g</option>
        <option value="8g">±8g</option>
        <option value="16g">±16g</option>
    </parameter>
</sensor>

The important difference between the module and sensor settings is that the module settings make 
that distinction between individual module settings and configuration-level settings, while the 
sensor settings do not.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QLineEdit, QComboBox, QSpinBox, QWidget
from PyQt6.QtWidgets import QVBoxLayout, QGridLayout, QLabel

from pathlib import Path
import xml.etree.ElementTree as ET


class MatrixWidget(QWidget):
    """
    A custom QWidget for displaying and editing matrix parameters.
    """
    value_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
    
    def _build_matrix_layout(self):
        layout = QGridLayout()
        default_values = [list(map(float, row.split(','))) for row in self.default.split(';')]
        
        for i in range(self.rows):
            for j in range(self.cols):
                line_edit = QLineEdit()
                line_edit.setText(str(default_values[i][j]))
                line_edit.textChanged.connect(self.value_changed)
                layout.addWidget(line_edit, i, j)
        
        self.setLayout(layout)
        
    def define_matrix(self, rows: int, cols: int, default: str):
        """
        Defines the matrix dimensions and default values.

        Args:
            rows (int): Number of rows in the matrix.
            cols (int): Number of columns in the matrix.
            default (str): Default values for the matrix, formatted as "val1,val2;val3,val4".
        """
        self.rows = rows
        self.cols = cols
        self.default = default
        self._build_matrix_layout()

    def set_value(self, value: str) -> None:
        values = [row.split(',') for row in value.split(';')]
        if len(values) != self.rows or any(len(row) != self.cols for row in values):
            raise ValueError(
                f"Matrix value must have {self.rows} rows and {self.cols} columns"
            )

        layout = self.layout()
        for row in range(self.rows):
            for col in range(self.cols):
                line_edit = layout.itemAtPosition(row, col).widget()
                line_edit.setText(values[row][col])

    def value(self) -> str:
        layout = self.layout()
        return ';'.join(
            ','.join(
                layout.itemAtPosition(row, col).widget().text()
                for col in range(self.cols)
            )
            for row in range(self.rows)
        )
        
        


class XMLSettingsParser(QObject):
    
    settings_map = {
        "float": QLineEdit,
        "dropdown": QComboBox,
        "hex": QSpinBox,
        "matrix": MatrixWidget}
    
    setting_update = pyqtSignal(str, object)  # Signal emitted when a setting is updated. Arguments: setting name, new value.
    
    signal_map = {
        QLineEdit: 'textChanged',
        QComboBox: 'currentIndexChanged',
        QSpinBox: 'valueChanged',
        MatrixWidget: 'value_changed'
    }
    
    def __init__(self, xml_file_path: str, is_module_settings: bool = True):
        """
        Initializes the XMLSettingsParser with the provided XML file path.

        Args:
            xml_file_path (str): The path to the XML file to be parsed.
        """
        super().__init__()
        self.xml_file_path = Path(xml_file_path)
        self.tree = ET.parse(self.xml_file_path)
        self.root = self.tree.getroot()
        self.is_module_settings = is_module_settings
        self.param_dict: dict[str, QWidget] = {}
        self.param_types: dict[str, str] = {}
        
        
    def build_widget(self, **kwargs) -> QWidget:
        """
        Parses the XML file and returns a widget containing the settings.
        
        Returns:
            QWidget: A Widget containing QWidgets for each parameter, keyed by simple enumeration.
            
            Future work: XML templating for more customization of the GUI layout.
        """
        
        self.param_dict.clear()
        self.param_types.clear()
        
        if self.is_module_settings:
            return self.build_module_settings_widgets(**kwargs)
        else:
            return self.build_sensor_settings_widgets()
        
    def build_module_settings_widgets(self, **kwargs) -> QWidget:
        """
        Parses the module settings XML and returns a widget containing the settings, depending on if individual
        or configuration-level settings are requested.
        
        Args:
            setting_type (str, optional): Type of settings to retrieve. Can be "individual" or "config". Defaults to "config".
        
        Returns:
            QWidget: A dict containing QWidgets for each parameter, keyed by simple enumeration.
        """
        widget = QWidget()
        layout = QVBoxLayout()
        
        #Parse kwargs to determine if we are retrieving the individual module settings or the configuration
        #level settings. If neither is specified, default to individual module settings.
        ind_indicators = ["ind", "individual", "i", "module", "m"]
        if kwargs.get('setting_type', "config") in ind_indicators:
            # Parse individual module settings
            settings = self.root.find('ind_settings')
        else: #Assume we want the configuration-level settings if individual is not specified
            settings = self.root.find('config_settings')
            
            
        if settings is not None:
            inner_layout = QGridLayout()
            for i, parameter in enumerate(settings.findall('parameter')):
                label = QLabel(parameter.get('label'))
                input_widget = self._create_input_widget(parameter)
                inner_layout.addWidget(label, i, 0)
                inner_layout.addWidget(input_widget, i, 1)
                self._wire_input_signal(input_widget, parameter.get('name'))
                
            layout.addLayout(inner_layout)
        
        widget.setLayout(layout)
        return widget

    def set_settings(self, settings: dict[str, object]) -> None:
        """Apply saved values to the widgets created by build_widget()."""
        for name, value in settings.items():
            input_widget = self.param_dict.get(name)
            if input_widget is None:
                continue

            if isinstance(input_widget, QLineEdit):
                input_widget.setText(str(value))
            elif isinstance(input_widget, QComboBox):
                index = input_widget.findData(str(value))
                if index < 0:
                    raise ValueError(
                        f"Unknown option {value!r} for setting {name!r}"
                    )
                input_widget.setCurrentIndex(index)
            elif isinstance(input_widget, QSpinBox):
                input_widget.setValue(
                    int(value, 0) if isinstance(value, str) else int(value)
                )
            elif isinstance(input_widget, MatrixWidget):
                input_widget.set_value(str(value))
            else:
                raise TypeError(f"Unsupported input widget for setting {name!r}")

    def get_settings(self) -> dict[str, str]:
        """Read the current input values using the parser's setting names."""
        settings = {}
        for name, input_widget in self.param_dict.items():
            if isinstance(input_widget, QLineEdit):
                value = input_widget.text()
            elif isinstance(input_widget, QComboBox):
                value = input_widget.currentData()
                if value is None:
                    raise ValueError(f"No option selected for setting {name!r}")
            elif isinstance(input_widget, QSpinBox):
                value = hex(input_widget.value())
            elif isinstance(input_widget, MatrixWidget):
                value = input_widget.value()
            else:
                raise TypeError(f"Unsupported input widget for setting {name!r}")

            settings[name] = str(value)
        return settings
    
    
    def build_sensor_settings_widgets(self) -> QWidget:
        """
        Parses the sensor settings XML and returns a widget containing the settings.
        
        Returns:
            QWidget: A dict containing QWidgets for each parameter, keyed by simple enumeration.
        """
        widget = QWidget()
        layout = QGridLayout()
        
        for i, parameter in enumerate(self.root.findall('parameter')):
            label = QLabel(parameter.get('label'))
            input_widget = self._create_input_widget(parameter)
            layout.addWidget(label, i, 0)
            layout.addWidget(input_widget, i, 1)
            
            #Wire the signal for the input widget to the setting update signal,
            #so that any changes made by the user are captured and processed accordingly.
            self._wire_input_signal(input_widget, parameter.get('name'))
        
        widget.setLayout(layout)
        return widget
    
    def _create_input_widget(self, parameter: ET.Element) -> QWidget:
        """
        Creates an input widget based on the parameter type.

        Args:
            parameter (ET.Element): The XML element representing the parameter.

        Returns:
            QWidget: The created input widget.
        """
        param_type = parameter.get('type')
        widget = None
        if param_type in self.settings_map:
            widget_class = self.settings_map[param_type]
            widget = widget_class()
            if param_type == "dropdown":
                for option in parameter.findall('option'):
                    widget.addItem(option.text, option.get('value'))
                if widget.count() == 0:
                    for token in parameter.get('options', '').split(','):
                        token = token.strip()
                        if not token:
                            continue
                        if ':' in token:
                            label, value = (part.strip() for part in token.split(':', 1))
                        else:
                            label = value = token
                        widget.addItem(label, value)
                default_index = widget.findData(parameter.get('default'))
                if default_index < 0:
                    default_index = widget.findText(parameter.get('default', ''))
                if default_index >= 0:
                    widget.setCurrentIndex(default_index)

            elif param_type == "hex":
                widget.setPrefix("0x")
                widget.setDisplayIntegerBase(16)
                widget.setMinimum(0)
                widget.setMaximum(255)
                widget.setValue(int(parameter.get('default', '0x00'), 0))

            elif param_type == "matrix":
                rows = int(parameter.get('rows', 1))
                cols = int(parameter.get('cols', 1))
                default = parameter.get('default', '0' * (rows * cols))
                widget.define_matrix(rows, cols, default)

            elif param_type == "float":
                widget.setText(parameter.get('default', ''))
            
            name = parameter.get('name')
            if name is None:
                raise ValueError("Every parameter must have a name")
            self.param_dict[name] = widget
            self.param_types[name] = param_type
            return widget
        else:
            raise ValueError(f"Unsupported parameter type: {param_type}")
        
    def _wire_input_signal(self, input_widget: QWidget, parameter_name: str):
        """
        Wires the input signals for the created widgets to handle user interactions.
        This method should be called after the widgets are created to ensure that
        any changes made by the user are captured and processed accordingly.
        """
        # Implementation for wiring signals goes here
        signal_name = self.signal_map.get(type(input_widget))
        if signal_name:
            signal = getattr(input_widget, signal_name)
            if isinstance(input_widget, QComboBox):
                signal.connect(
                    lambda index, name=parameter_name, widget=input_widget:
                    self.setting_update.emit(name, widget.itemData(index))
                )
            elif isinstance(input_widget, MatrixWidget):
                signal.connect(
                    lambda name=parameter_name, widget=input_widget:
                    self.setting_update.emit(name, widget.value())
                )
            else:
                signal.connect(
                    lambda value, name=parameter_name:
                    self.setting_update.emit(name, value)
                )
       

        
        
        
