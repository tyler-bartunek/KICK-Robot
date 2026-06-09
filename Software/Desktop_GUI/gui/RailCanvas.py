from pathlib import Path
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QPushButton, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QSizePolicy, QScrollArea, QFrame
)
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, pyqtSignal


# Fixed hardware constants — not user-editable at runtime
RIDGE_COUNT    = 7
RIDGE_PITCH_MM = 12

MODULE_DEF_DIR = Path(__file__).parent.parent / "assets" / "_define" / "modules"


class _DimBracket(QWidget):
    """
    Horizontal dimension indicator sitting between the two rails.
    Draws: left-tick --- [label / input] --- right-tick
    Line runs through the vertical center of the widget.
    """
    value_changed = pyqtSignal(int)

    TICK_H = 8
    GAP    = 6

    def __init__(self, value_mm: int = 65, parent=None):
        super().__init__(parent)
        self.setObjectName("DimBracket")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(200)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        outer.addStretch(1)

        self._label = QLabel("rail sep")
        self._label.setObjectName("DimBracketLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._input = QSpinBox()
        self._input.setObjectName("DimBracketInput")
        self._input.setRange(0, 999)
        self._input.setValue(value_mm)
        self._input.setSuffix(" mm")
        self._input.setFixedWidth(80)
        self._input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._input.valueChanged.connect(self.value_changed)

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

    def value(self) -> int:
        return self._input.value()

    def set_value(self, v: int):
        self._input.setValue(v)


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

        p.setClipping(False)
        p.setPen(QPen(self.RIDGE_COLOR, 1))
        cx = w // 2
        spacing = h / (RIDGE_COUNT + 1)
        for i in range(1, RIDGE_COUNT + 1):
            y = int(spacing * i)
            p.drawLine(cx - self.RIDGE_HALF, y, cx + self.RIDGE_HALF, y)

        p.end()


class _ModuleSettingsPanel(QWidget):
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

        # param_name -> (widget, type_str, value_map)
        # value_map is only populated for dropdowns: {display: internal_value}
        self._fields: dict[str, tuple[QWidget, str, dict]] = {}
        self._module_type: str = ""

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
            root = ET.parse(xml_path).getroot()
        except ET.ParseError as e:
            self._form_layout.addRow(QLabel(f"XML parse error: {e}"))
            return

        for param in root.findall("config_settings/parameter"):
            name    = param.get("name",    "")
            label   = param.get("label",   name)
            ptype   = param.get("type",    "float")
            default = param.get("default", "0")
            unit    = param.get("unit",    "")
            options = param.get("options", "")
            p_min   = param.get("min",     None)
            p_max   = param.get("max",     None)

            result = self._make_widget(ptype, default, unit,
                                       options, p_min, p_max)
            if result is not None:
                widget, value_map = result
                self._fields[name] = (widget, ptype, value_map)
                self._form_layout.addRow(label, widget)

    def collect_config_settings(self) -> dict:
        """
        Return current values of all config_settings fields.
        Dropdowns return their internal value, not the display label.
        """
        out = {}
        for name, (widget, ptype, value_map) in self._fields.items():
            if ptype == "dropdown":
                display = widget.currentText()
                # Fall back to display text if no internal value mapping exists
                out[name] = value_map.get(display, display)
            elif ptype == "float":
                out[name] = widget.value()
            elif ptype == "double":
                try:
                    out[name] = float(widget.text())
                except ValueError:
                    out[name] = widget.text()
        return out

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _clear_form(self):
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)
        self._fields.clear()

    def _make_widget(
        self,
        ptype:   str,
        default: str,
        unit:    str,
        options: str,
        p_min:   str | None,
        p_max:   str | None,
    ) -> tuple[QWidget, dict] | None:
        """
        Build and return (widget, value_map) for the given parameter type.
        value_map is {display_label: internal_value} for dropdowns, {} otherwise.
        Returns None for unrecognised types so the row is silently skipped.

        Dropdown option format in XML:
            "Label:value,Label:value"   — separate display from internal value
            "Label,Label"               — display and internal value are the same
        """

        if ptype == "float":
            w = QDoubleSpinBox()
            w.setDecimals(2)
            w.setRange(
                float(p_min) if p_min is not None else -9999.0,
                float(p_max) if p_max is not None else  9999.0,
            )
            if unit:
                w.setSuffix(f" {unit}")
            try:
                w.setValue(float(default))
            except ValueError:
                w.setValue(0.0)
            w.valueChanged.connect(
                lambda _: self.settings_changed.emit(self.collect_config_settings())
            )
            return w, {}

        elif ptype == "double":
            w = QLineEdit()
            w.setText(default)
            if unit:
                w.setPlaceholderText(unit)
            w.textChanged.connect(
                lambda _: self.settings_changed.emit(self.collect_config_settings())
            )
            return w, {}

        elif ptype == "dropdown":
            w = QComboBox()
            value_map: dict[str, str] = {}

            for token in options.split(","):
                token = token.strip()
                if not token:
                    continue
                if ":" in token:
                    display, internal = token.split(":", 1)
                    display  = display.strip()
                    internal = internal.strip()
                else:
                    display = internal = token
                value_map[display] = internal
                w.addItem(display)

            # Select default by display label first, then by internal value
            idx = w.findText(default)
            if idx < 0:
                # Try matching against internal values
                for i, (disp, val) in enumerate(value_map.items()):
                    if val == default:
                        idx = i
                        break
            if idx >= 0:
                w.setCurrentIndex(idx)

            w.currentTextChanged.connect(
                lambda _: self.settings_changed.emit(self.collect_config_settings())
            )
            return w, value_map

        return None   # unknown type — skip row gracefully

    def _on_push(self):
        self.settings_changed.emit(self.collect_config_settings())


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
        self._bracket    = _DimBracket(value_mm=65)
        self._rail_right = _Rail()
        self._settings   = _ModuleSettingsPanel()
 
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

    def load_module_type(self, type_name: str):
        """Called by MainWindow when bus_state reports a module type."""
        self._settings.load_module_type(type_name)

    def load_config(self, cfg: dict):
        self._bracket.set_value(cfg.get("rail_sep_mm", 65))

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_settings_changed(self, settings: dict):
        self.config_changed.emit({
            "rail_sep_mm":    self._bracket.value(),
            "num_ridges":     RIDGE_COUNT,
            "ridge_pitch_mm": RIDGE_PITCH_MM,
            **settings,
        })