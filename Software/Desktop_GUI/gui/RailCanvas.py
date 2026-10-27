from pathlib import Path
import xml.etree.ElementTree as ET

from xml_settings_parser import XMLSettingsParser

from kick_core import MODULE_COLOR_MAP, MODULE_DEF_DIR, MODULE_TYPE_MAP

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QPushButton, QLabel, QLineEdit,
    QSizePolicy, QScrollArea, QFrame, QDialog
)
from PyQt6.QtGui import QPainter, QPen, QColor, QDoubleValidator
from PyQt6.QtCore import Qt, pyqtSignal


# Fixed hardware constants — not user-editable at runtime
SEGMENT_COUNT    = 6
RIDGE_COUNT     = 7
RIDGE_PITCH_MM = 12


class _DimBracket(QWidget):
    """
    Horizontal dimension indicator sitting between the two rails.
    Draws: left-tick --- [label / input] --- right-tick
    Line runs through the vertical center of the widget.
    """
    value_changed = pyqtSignal(str)

    TICK_H = 8
    GAP    = 6

    def __init__(self, value_mm: float = 100., parent=None):
        super().__init__(parent)
        self.setObjectName("DimBracket")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(200)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        outer.addStretch(1)

        self._label = QLabel("rail sep (mm)")
        self._label.setObjectName("DimBracketLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Input field for the dimension value
        self._input = QLineEdit()
        self._input.setObjectName("DimBracketInput")
        #Make sure the input text is always a number (float)
        self._input.setValidator(QDoubleValidator(0, 9999, 2, self))
        self._input.setPlaceholderText(str(value_mm))
        self._input.setFixedWidth(80)
        self._input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._input.textChanged.connect(self.value_changed)

        outer.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(self._input, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#666666"), 1))

        w  = self.width()
        cy = self.height() // 2
        half_tick = self.TICK_H // 2

        input_left  = self._input.mapTo(self, self._input.rect().topLeft()).x()
        input_right = self._input.mapTo(self, self._input.rect().topRight()).x()
        gap_l = input_left  - self.GAP
        gap_r = input_right + self.GAP

        p.drawLine(0, cy - half_tick, 0, cy + half_tick)
        p.drawLine(0, cy, gap_l, cy)
        p.drawLine(gap_r, cy, w, cy)
        p.drawLine(w, cy - half_tick, w, cy + half_tick)

        p.end()

    def value(self) -> float:
        return float(self._input.text() or 0)

    def set_value(self, v: float):
        self._input.setText(str(v))


class _Rail(QWidget):
    """A single vertical rail track with evenly-spaced ridge tick marks."""

    RIDGE_COLOR  = QColor("#3a3a3a")
    RAIL_COLOR   = QColor("#1c1c1c")
    BORDER_COLOR = QColor("#555555")
    RIDGE_HALF   = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Rail")
        self.setFixedWidth(14)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        p.setPen(QPen(self.BORDER_COLOR, 1))
        p.setBrush(self.RAIL_COLOR)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        #Create the segments with visible demarcation lines,
        # with the ridge count representing the number of invisible position options
        # along each segment for the module to be placed. 
        
        #Ridge count is unrelated to number of segments, but is instead a fixed
        # number of ridges on a physical rail. 
        
        #The product of the number of segments and the ridge count is the total number
        # of positions available for the module to be placed along the rail.
        p.setClipping(False)
        p.setPen(QPen(self.RIDGE_COLOR, 1))
        cx = w // 2
        spacing = h / (SEGMENT_COUNT)
        for i in range(1, SEGMENT_COUNT):
            y = int(spacing * i)
            p.drawLine(cx - self.RIDGE_HALF, y, cx + self.RIDGE_HALF, y)

        p.end()


class _ConfigSettingsPanel(QWidget):
    """
    Scrollable settings panel populated from a module XML definition.
    Renders config_settings fields only — ind_settings are handled by
    the per-module context menu.

    Emits settings_changed(dict) on any field change or push button click.
    The dict values use internal values (not display labels) for dropdowns.
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModuleSettingsPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._type_label = QLabel("no module detected")
        self._type_label.setObjectName("ModuleTypeLabel")
        outer.addWidget(self._type_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("PanelDivider")
        outer.addWidget(sep)

        self._form_widget = QWidget()
        self._form_widget.setObjectName("ModuleSettingsForm")
        self._form_layout = QFormLayout(self._form_widget)
        self._form_layout.setContentsMargins(4, 6, 4, 6)
        self._form_layout.setSpacing(6)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._form_widget)
        outer.addWidget(scroll, stretch=1)

        self._push_btn = QPushButton("push config")
        self._push_btn.setObjectName("PushConfigButton")
        self._push_btn.clicked.connect(self._on_push)
        outer.addWidget(self._push_btn)

        self._module_type: str = ""
        self._parser: XMLSettingsParser | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_module_type(self, type_name: str):
        """
        Parse <type_name>.xml and rebuild the config_settings form.
        Called by RailCanvas.load_module_type().
        """
        self._module_type = type_name
        self._type_label.setText(type_name.replace("_", " "))
        self._clear_form()

        xml_path = MODULE_DEF_DIR / f"{type_name}.xml"
        if not xml_path.exists():
            self._form_layout.addRow(QLabel(f"No definition found: {xml_path.name}"))
            return

        try:
            parser = XMLSettingsParser(xml_path, is_module_settings=True)
            settings_widget = parser.build_widget(setting_type="config")
        except ET.ParseError as e:
            self._form_layout.addRow(QLabel(f"XML parse error: {e}"))
            return
        except ValueError as e:
            self._form_layout.addRow(QLabel(f"Unable to build settings: {e}"))
            return

        self._parser = parser
        self._parser.setting_update.connect(self._on_parameter_changed)
        self._form_layout.addRow(settings_widget)

    def collect_config_settings(self) -> dict:
        """
        Return current values of all config_settings fields.
        Dropdowns return their internal value, not the display label.
        """
        if self._parser is None:
            return {}

        out: dict[str, object] = self._parser.get_settings()
        for name, ptype in self._parser.param_types.items():
            if ptype == "dropdown":
                continue
            elif ptype == "float":
                out[name] = float(out[name])
            elif ptype == "double":
                try:
                    out[name] = float(out[name])
                except ValueError:
                    pass
        return out

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _clear_form(self):
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)
        self._parser = None

    def _on_parameter_changed(self):
        self.settings_changed.emit(self.collect_config_settings())

    def _on_push(self):
        self.settings_changed.emit(self.collect_config_settings())
        
        
        
class ModuleBox(QWidget):
    """
    A simple box with a label, draggable to the discrete positions along the rails. 
    
    The box is both a visual representation of the module for setting the position settings
    along the rails for the user to reference, and can also be moved along the rail using 
    a scroll wheel indicating how many ridges to move the module relative to the default position. 
    
    Positive values move the module up the rail, negative values move the module down the rail. 
    
    The box also has a label indicating the module type, and can be clicked to open a context menu
    for changing the module-level settings (ind_settings) for the module. The context menu is populated from the module's XML definition. 
    """
    
    def __init__(self, module_type: str, parent=None):
        
        super().__init__(parent)
        self.setObjectName("ModuleBox")
        self.setFixedSize(100, 50)
        
        self.module_type = module_type
        self.label = QLabel(module_type, self)
        
        self.configured = False
        self.settings: dict[str, str] = {}
        
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setGeometry(0, 0, 100, 50)
        
    
class _Module_Settings_Window(QDialog):
    
    def __init__(self, module:ModuleBox, parent = None):
        
        #Set up the basics of the dialog window
        super().__init__(parent)
        self.module = module
        self.setObjectName("ConfigWindow")
        self.setWindowTitle(f"{self.module.module_type} Configuration")
        
        #Put the setting files into a searchable dict
        self._assemble_setting_dict()
        
        #Setup the layout
        outer = QVBoxLayout(self)
        
        #Create the parameter section and add it to the layout
        outer.addWidget(self._build_parameter_section())
        
        outer.addStretch(1)
        
        save_button = QPushButton("Save Module Settings")
        save_button.clicked.connect(self._on_save)
        
        outer.addWidget(save_button)
        
    def _build_parameter_section(self) -> QWidget:
        # sensor_identifier = self.sensor.full_name.split('_')[0]
        settings_path = MODULE_DEF_DIR / f"{MODULE_TYPE_MAP[self.module.module_type]}.xml"
        
        try:
            self.param_parser = XMLSettingsParser(settings_path, is_module_settings=True)
            parameter_widget = self.param_parser.build_widget(setting_type="ind")
        except ET.ParseError:
            pass #TODO: Determine what to do here

        if self.module.configured:
            self.param_parser.set_settings(self.module.settings)

        return parameter_widget

    def _extract_settings(self) -> dict[str, str]:
        return self.param_parser.get_settings()

    def _on_save(self):
        
        self.module.settings = self._extract_settings()
        self.module.configured = True
        self.accept()
    


class RailCanvas(QWidget):
    """
    Two vertical rails with a horizontal dimension bracket centered
    between them, and a module settings sidebar on the right.

    Row layout:  rail_left | bracket | rail_right | module_settings_panel
    """

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        
        super().__init__(parent)
        self.setObjectName("RailCanvas")
 
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(4)
 
        self._rail_left  = _Rail()
        self._bracket    = _DimBracket(value_mm=100.)
        self._rail_right = _Rail()
        self._settings   = _ConfigSettingsPanel()
        
        self.devices = {i:{} for i in range(SEGMENT_COUNT)}  # Store device info for each segment
 
        self._settings.settings_changed.connect(self._on_settings_changed)
 
        # Rail section stretches to fill available space
        rail_section = QWidget()
        rl = QHBoxLayout(rail_section)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        rl.addStretch(1)
        rl.addWidget(self._rail_left)
        rl.addWidget(self._bracket)
        rl.addWidget(self._rail_right)
        rl.addStretch(1)
 
        # Settings panel fixed width so it doesn't crowd the rails
        self._settings.setFixedWidth(200)
 
        rail_section.setMinimumWidth(400)
        outer.addWidget(rail_section, stretch=1)
        outer.addSpacing(12)
        outer.addWidget(self._settings)
        outer.addStretch(1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_module_type(self, device:dict):
        """Called by MainWindow when bus_state reports a module type."""
        type_name = device["type"]
        position = device["position"]
        #If the module type has changed, update the module box and reload the settings panel
        #Also draw the box on the rail if it doesn't exist yet.
        if (not self.devices[position]) or (self.devices[position].get("type") != type_name):
            self.devices[position] = device
            self.devices[position]["box"] = ModuleBox(type_name)
        self._settings.load_module_type(type_name)
        

    def load_config(self, cfg: dict):
        self._bracket.set_value(cfg.get("rail_sep_mm", 100))

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_settings_changed(self, settings: dict):
        self.config_changed.emit({
            "rail_sep_mm":    self._bracket.value(),
            **settings,
        })
        
        
        