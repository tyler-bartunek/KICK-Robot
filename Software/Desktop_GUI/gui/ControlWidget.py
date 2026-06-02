from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal


class ControlWidget(QWidget):
    """
    Keyboard / gamepad selector + D-pad jog buttons + live vel readout.
    Keyboard arrow keys are captured at window level and forwarded here.
    """

    # Emitted on every state change: (vx, vy, omega)
    velocity_command = pyqtSignal(float, float, float)

    # Jog speed (m/s and rad/s) — tune per platform
    JOG_LINEAR  = 0.3
    JOG_ANGULAR = 0.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ControlWidget")

        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        header = QLabel("CONTROL")
        header.setObjectName("PanelSectionHeader")
        outer.addWidget(header)

        # Scheme toggle
        scheme_row = QHBoxLayout()
        scheme_row.setSpacing(6)
        self._scheme_group = QButtonGroup(self)
        for label in ("keyboard", "gamepad"):
            btn = QPushButton(label)
            btn.setObjectName("SchemeButton")
            btn.setCheckable(True)
            self._scheme_group.addButton(btn)
            scheme_row.addWidget(btn)
        self._scheme_group.buttons()[0].setChecked(True)
        outer.addLayout(scheme_row)

        # D-pad + velocity readout
        lower = QHBoxLayout()
        lower.setSpacing(10)
        lower.addLayout(self._build_dpad())
        lower.addLayout(self._build_vel_readout())
        outer.addLayout(lower)
        outer.addStretch()

    def _build_dpad(self) -> QVBoxLayout:
        grid_layout = QVBoxLayout()
        grid_layout.setSpacing(3)

        rows = [
            [None,    "↑",    None ],
            ["←",     "·",    "→"  ],
            [None,    "↓",    None ],
        ]
        actions = {
            "↑": ( self.JOG_LINEAR,  0,  0),
            "↓": (-self.JOG_LINEAR,  0,  0),
            "←": ( 0, -self.JOG_LINEAR,  0),
            "→": ( 0,  self.JOG_LINEAR,  0),
            "·": ( 0,  0,               0),
        }

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(3)
            for cell in row:
                if cell is None:
                    spacer = QWidget()
                    spacer.setFixedSize(28, 28)
                    row_layout.addWidget(spacer)
                else:
                    btn = QPushButton(cell)
                    btn.setObjectName(
                        "DPadStop" if cell == "·" else "DPadButton"
                    )
                    btn.setFixedSize(28, 28)
                    vx, vy, om = actions[cell]
                    btn.pressed.connect(
                        lambda v=(vx, vy, om): self._send(v[0], v[1], v[2])
                    )
                    btn.released.connect(lambda: self._send(0, 0, 0))
                    row_layout.addWidget(btn)
            grid_layout.addLayout(row_layout)

        return grid_layout

    def _build_vel_readout(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)

        self._vx_lbl    = self._vel_row("vx")
        self._vy_lbl    = self._vel_row("vy")
        self._omega_lbl = self._vel_row("omega")

        for entry in (self._vx_lbl, self._vy_lbl, self._omega_lbl):
            layout.addLayout(entry["layout"])
        layout.addStretch()
        return layout

    def _vel_row(self, key: str) -> dict:
        layout = QHBoxLayout()
        layout.setSpacing(6)
        k = QLabel(key)
        k.setObjectName("OrientStatKey")
        v = QLabel("0.00")
        v.setObjectName("OrientStatValue")
        layout.addWidget(k)
        layout.addWidget(v)
        return {"layout": layout, "value": v}

    def _send(self, vx: float, vy: float, omega: float):
        self._vx, self._vy, self._omega = vx, vy, omega
        self._vx_lbl["value"].setText(f"{vx:.2f}")
        self._vy_lbl["value"].setText(f"{vy:.2f}")
        self._omega_lbl["value"].setText(f"{omega:.2f}")
        self.velocity_command.emit(vx, vy, omega)

    # ------------------------------------------------------------------
    # Call from MainWindow.keyPressEvent / keyReleaseEvent
    # ------------------------------------------------------------------

    def handle_key_press(self, key):
        from PyQt6.QtCore import Qt as _Qt
        mapping = {
            _Qt.Key.Key_Up:    ( self.JOG_LINEAR, 0, 0),
            _Qt.Key.Key_Down:  (-self.JOG_LINEAR, 0, 0),
            _Qt.Key.Key_Left:  (0, -self.JOG_LINEAR, 0),
            _Qt.Key.Key_Right: (0,  self.JOG_LINEAR, 0),
        }
        if key in mapping:
            self._send(*mapping[key])

    def handle_key_release(self, key):
        from PyQt6.QtCore import Qt as _Qt
        if key in (_Qt.Key.Key_Up, _Qt.Key.Key_Down,
                   _Qt.Key.Key_Left, _Qt.Key.Key_Right):
            self._send(0, 0, 0)
