from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import pyqtSignal


class LaunchPanel(QWidget):
    """
    Launch profile selector + uptime / CPU / temp readout.
    Emits launch_requested(profile_name) when user clicks Launch.
    """

    launch_requested = pyqtSignal(str)

    PROFILES = [
        "mecanum_4wd.launch",
        "test_spi.launch",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LaunchPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QLabel("LAUNCH PROFILE")
        header.setObjectName("PanelSectionHeader")
        layout.addWidget(header)

        self._combo = QComboBox()
        self._combo.setObjectName("LaunchCombo")
        for p in self.PROFILES:
            self._combo.addItem(p)
        layout.addWidget(self._combo)

        self._launch_btn = QPushButton("▶  launch")
        self._launch_btn.setObjectName("LaunchButton")
        self._launch_btn.clicked.connect(self._on_launch)
        layout.addWidget(self._launch_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("PanelDivider")
        layout.addWidget(sep)

        # System stats
        self._uptime_lbl = self._stat_row("uptime",  "---")
        self._cpu_lbl    = self._stat_row("Pi CPU",  "---")
        self._temp_lbl   = self._stat_row("Pi temp", "---")

        for entry in (self._uptime_lbl, self._cpu_lbl, self._temp_lbl):
            layout.addLayout(entry["layout"])

        layout.addStretch()

    def _stat_row(self, key: str, default: str) -> dict:
        layout = QHBoxLayout()
        layout.setSpacing(0)
        k = QLabel(key)
        k.setObjectName("LaunchStatKey")
        v = QLabel(default)
        v.setObjectName("LaunchStatValue")
        layout.addWidget(k)
        layout.addStretch()
        layout.addWidget(v)
        return {"layout": layout, "value": v}

    def _on_launch(self):
        self.launch_requested.emit(self._combo.currentText())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_stats(self, uptime: str, cpu_pct: float, temp_c: float):
        self._uptime_lbl["value"].setText(uptime)
        self._cpu_lbl["value"].setText(f"{cpu_pct:.0f}%")

        temp_str = f"{temp_c:.0f} °C"
        self._temp_lbl["value"].setText(temp_str)
        state = "warn" if temp_c > 70 else "normal"
        self._temp_lbl["value"].setObjectName(f"LaunchStatValue_{state}")
        self._temp_lbl["value"].style().unpolish(self._temp_lbl["value"])
        self._temp_lbl["value"].style().polish(self._temp_lbl["value"])
