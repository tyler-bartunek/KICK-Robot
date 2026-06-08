from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QPushButton, QLabel,
    QSpinBox, QSizePolicy
)
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, pyqtSignal


# Fixed hardware constants — not user-editable at runtime
RIDGE_COUNT    = 7
RIDGE_PITCH_MM = 12


class _DimBracket(QWidget):
    """
    Horizontal dimension line spanning between the two rails.
    Draws a horizontal line with vertical tick ends at left and right edges,
    with a labeled input sitting below the line centered horizontally.
    """
    value_changed = pyqtSignal(int)

    TICK_H = 8    # vertical extent of each end tick
    GAP    = 4    # px gap between line bottom and label top

    def __init__(self, value_mm: int = 65, parent=None):
        super().__init__(parent)
        self.setObjectName("DimBracket")
        self.setFixedHeight(52)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        # Reserve space for the painted line at top, then label + input below
        line_height = self.TICK_H + self.GAP
        outer.addSpacing(line_height)

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

        w = self.width()
        y = self.TICK_H // 2   # vertical center of the line

        # Left tick
        p.drawLine(0, 0,      0, self.TICK_H)
        # Horizontal line
        p.drawLine(0, y,      w, y)
        # Right tick
        p.drawLine(w, 0,      w, self.TICK_H)

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
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Rail body
        p.setPen(QPen(self.BORDER_COLOR, 1))
        p.setBrush(self.RAIL_COLOR)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        # Ridge ticks extending past rail width
        p.setClipping(False)
        p.setPen(QPen(self.RIDGE_COLOR, 1))
        cx = w // 2
        spacing = h / (RIDGE_COUNT + 1)
        for i in range(1, RIDGE_COUNT + 1):
            y = int(spacing * i)
            p.drawLine(cx - self.RIDGE_HALF, y, cx + self.RIDGE_HALF, y)

        p.end()


class RailCanvas(QWidget):
    """
    Two vertical rails with a single horizontal dimension bracket between
    them showing rail separation, plus a geometry sidebar.

    Vertical layout of the center column:
        [ dim bracket (horizontal line + input) ]
        [ left rail ] [ right rail ]   <- rails fill remaining height
    
    Full horizontal layout:
        rail_left | rail_right | sidebar
        (bracket spans above both rails)
    """

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RailCanvas")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(14)

        # Rails + bracket stacked horizontally
        rail_col = QWidget()
        rc = QHBoxLayout(rail_col)
        rc.setContentsMargins(0, 0, 0, 0)
        rc.setSpacing(0)

        self._bracket = _DimBracket(value_mm=65)
        self._bracket.setFixedWidth(350)

        self._rail_left  = _Rail()
        self._rail_right = _Rail()

        # Rails pushed to left and right edges of the rail row,
        # bracket line endpoints align with rail outer edges
        rc.addStretch(1)
        rc.addWidget(self._rail_left)
        rc.addWidget(self._bracket)
        rc.addWidget(self._rail_right)
        rc.addStretch(1)
        
        # rc.addWidget(rails, stretch=1)

        outer.addWidget(rail_col, stretch=1)
        outer.addWidget(self._build_sidebar())
        outer.addStretch(1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("RailSidebar")

        fl = QFormLayout(sidebar)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(6)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)


        #TODO: Make this dynamic depending on which modules are detected using _populate_sidebar
        self._wheel_r = QSpinBox()
        self._wheel_r.setRange(0, 200)
        self._wheel_r.setValue(65)
        self._wheel_r.setSuffix(" mm")

        fl.addRow("wheel r", self._wheel_r)

        push = QPushButton("push config")
        push.setObjectName("PushConfigButton")
        push.clicked.connect(self._on_push)
        fl.addRow("", push)

        return sidebar
    
    def _populate_sidebar(self) -> QWidget:
        
        pass

    def _on_push(self):
        self.config_changed.emit({
            "rail_sep_mm":    self._bracket.value(),
            "wheel_r_mm":     self._wheel_r.value(),
            "num_ridges":     RIDGE_COUNT,
            "ridge_pitch_mm": RIDGE_PITCH_MM,
        })