
"""
AddRobotWizard — three-page QWizard for adding a new robot connection.

Page 1: Alias, IP address, username
Page 2: Password + remember-me checkbox, live connection attempt
Page 3: Workspace — auto-detect or manual entry

On successful completion, caller receives a populated RobotProfile
and (optionally) a stored password via RobotProfileManager.
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QProgressBar, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from connection.RobotProfileManager import RobotProfile, RobotProfileManager
from connection.SSHWorker import SSHWorker


# ------------------------------------------------------------------
# Page 1 — Robot identity
# ------------------------------------------------------------------

class _IdentityPage(QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("New Robot Connection")
        self.setSubTitle("Enter a name and the IP address of your KICK Robot.")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._alias    = self._field("Alias",      "e.g. Lab Bot")
        self._ip       = self._field("IP Address", "e.g. 192.168.1.42")
        self._username = self._field("Username",   "kickbot")
        self._username.setText("kickbot")

        for label_text, widget in [
            ("Alias",      self._alias),
            ("IP Address", self._ip),
            ("Username",   self._username),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(80)
            row.addWidget(lbl)
            row.addWidget(widget)
            layout.addLayout(row)

        # Register fields so QWizard can access them from other pages
        self.registerField("alias*",    self._alias)
        self.registerField("hostname*", self._ip)
        self.registerField("username",  self._username)

    def _field(self, name: str, placeholder: str) -> QLineEdit:
        w = QLineEdit()
        w.setPlaceholderText(placeholder)
        w.setObjectName(f"WizardField_{name}")
        return w

    def isComplete(self) -> bool:
        return bool(self._alias.text().strip()
                    and self._ip.text().strip()
                    and self._username.text().strip())


# ------------------------------------------------------------------
# Page 2 — Credentials + connection attempt
# ------------------------------------------------------------------

class _CredentialsPage(QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Credentials")
        self.setSubTitle(
            "Enter your SSH password. Click Connect to verify."
        )
        self._connected = False

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Password row
        pw_row = QHBoxLayout()
        pw_lbl = QLabel("Password")
        pw_lbl.setFixedWidth(80)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("SSH password")
        self._password.returnPressed.connect(self._attempt_connect)
        pw_row.addWidget(pw_lbl)
        pw_row.addWidget(self._password)
        layout.addLayout(pw_row)

        # Remember me
        self._remember = QCheckBox("Remember me (store in Windows Credential Manager)")
        layout.addWidget(self._remember)

        # Connect button + status
        btn_row = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setObjectName("LaunchButton")
        self._connect_btn.clicked.connect(self._attempt_connect)
        btn_row.addWidget(self._connect_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setObjectName("WizardStatus")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        layout.addStretch()

        self.registerField("password", self._password)
        self.registerField("remember", self._remember)

        # SSH worker + thread (created once, reused on retry)
        self._thread = QThread(self)
        self._worker = SSHWorker()
        self._worker.moveToThread(self._thread)
        self._worker.connected.connect(self._on_connected)
        self._worker.connection_failed.connect(self._on_failed)
        self._thread.start()

    def _attempt_connect(self):
        hostname = self.field("hostname")
        username = self.field("username") or "kickbot"
        password = self._password.text()

        if not password:
            self._status.setText("Please enter a password.")
            return

        self._connect_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._status.setText("Connecting…")
        self._connected = False
        self.completeChanged.emit()

        # Invoke on the worker thread
        QThread.msleep(0)   # allow UI to update
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._worker, "connect",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, hostname),
            Q_ARG(str, username),
            Q_ARG(str, password),
        )

    def _on_connected(self):
        self._connected = True
        self._progress.setVisible(False)
        self._status.setText("✓ Connected successfully.")
        self._status.setObjectName("WizardStatusOk")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._connect_btn.setEnabled(True)
        self.completeChanged.emit()

    def _on_failed(self, error: str):
        self._connected = False
        self._progress.setVisible(False)
        self._status.setText(f"✗ Connection failed: {error}")
        self._status.setObjectName("WizardStatusErr")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._connect_btn.setEnabled(True)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._connected

    def ssh_worker(self) -> SSHWorker:
        """Expose worker so Page 3 and MainWindow can reuse the session."""
        return self._worker

    def ssh_thread(self) -> QThread:
        return self._thread


# ------------------------------------------------------------------
# Page 3 — Workspace detection
# ------------------------------------------------------------------

class _WorkspacePage(QWizardPage):

    def __init__(self, ssh_worker: SSHWorker, parent=None):
        super().__init__(parent)
        self.setTitle("ROS Workspace")
        self.setSubTitle(
            "Let the wizard find your sros_ws directory, "
            "or enter the path manually."
        )
        self._worker = ssh_worker
        self._workspace = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._detect_btn = QPushButton("Auto-detect sros_ws")
        self._detect_btn.setObjectName("LaunchButton")
        self._detect_btn.clicked.connect(self._run_detect)
        layout.addWidget(self._detect_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._detect_status = QLabel("")
        self._detect_status.setObjectName("WizardStatus")
        layout.addWidget(self._detect_status)

        # Manual entry fallback
        manual_row = QHBoxLayout()
        manual_lbl = QLabel("Or enter path:")
        manual_lbl.setFixedWidth(90)
        self._manual = QLineEdit()
        self._manual.setPlaceholderText("/home/kickbot/sros_ws")
        self._manual.textChanged.connect(self._on_manual_changed)
        manual_row.addWidget(manual_lbl)
        manual_row.addWidget(self._manual)
        layout.addLayout(manual_row)

        layout.addStretch()

        self.registerField("workspace", self._manual)

        self._worker.workspace_found.connect(self._on_found)
        self._worker.workspace_not_found.connect(self._on_not_found)

    def _run_detect(self):
        self._detect_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._detect_status.setText("Searching…")
        self._workspace = ""
        self.completeChanged.emit()

        from PyQt6.QtCore import QMetaObject
        QMetaObject.invokeMethod(
            self._worker, "detect_workspace",
            Qt.ConnectionType.QueuedConnection,
        )

    def _on_found(self, path: str):
        self._workspace = path
        self._manual.setText(path)
        self._progress.setVisible(False)
        self._detect_status.setText(f"✓ Found: {path}")
        self._detect_btn.setEnabled(True)
        self.completeChanged.emit()

    def _on_not_found(self):
        self._progress.setVisible(False)
        self._detect_status.setText(
            "Not found automatically. Enter path manually."
        )
        self._detect_btn.setEnabled(True)

    def _on_manual_changed(self, text: str):
        self._workspace = text.strip()
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return bool(self._workspace)


# ------------------------------------------------------------------
# Wizard
# ------------------------------------------------------------------

class AddRobotWizard(QWizard):
    """
    Emits robot_added(profile, ssh_worker, ssh_thread) on success so
    MainWindow can store the profile and keep the SSH session alive.
    """

    robot_added = pyqtSignal(object, object, object)
    # args: RobotProfile, SSHWorker, QThread

    def __init__(self, profile_manager: RobotProfileManager, parent=None):
        super().__init__(parent)
        self._manager = profile_manager

        self.setWindowTitle("Add Robot Connection")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(480, 360)

        self._page1 = _IdentityPage(self)
        self._page2 = _CredentialsPage(self)
        self._page3 = _WorkspacePage(self._page2.ssh_worker(), self)

        self.addPage(self._page1)
        self.addPage(self._page2)
        self.addPage(self._page3)

        self.button(QWizard.WizardButton.FinishButton).clicked.connect(
            self._on_finish
        )

    def _on_finish(self):
        alias     = self.field("alias").strip()
        hostname  = self.field("hostname").strip()
        username  = self.field("username").strip() or "kickbot"
        workspace = self.field("workspace").strip()
        password  = self.field("password")
        remember  = bool(self.field("remember"))

        profile = RobotProfile(
            alias=alias,
            hostname=hostname,
            username=username,
            workspace=workspace,
        )
        self._manager.add_or_update(
            profile,
            password=password,
            remember=remember,
        )

        self.robot_added.emit(
            profile,
            self._page2.ssh_worker(),
            self._page2.ssh_thread(),
        )

