
"""
SSHWorker — persistent SSH session on a QThread.
Handles: connect, workspace detection, docker+configure launch,
         launch file listing, and arbitrary command execution.
"""

from PyQt6.QtCore import QObject, pyqtSignal

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SSHWorker(QObject):
    """
    All public methods are intended to be called as slots from the main
    thread — they run on the worker's QThread via Qt's queued connection.

    Signals carry results back to the main thread safely.
    """

    # Connection
    connected           = pyqtSignal()
    connection_failed   = pyqtSignal(str)       # error message

    # Workspace detection
    workspace_found     = pyqtSignal(str)        # absolute path on Pi
    workspace_not_found = pyqtSignal()

    # Docker / configure
    docker_output       = pyqtSignal(str)        # stdout lines streamed
    docker_ready        = pyqtSignal()           # rosbridge is up
    docker_failed       = pyqtSignal(str)        # error message

    # Launch files
    launches_listed     = pyqtSignal(list)       # list[str] of .sh filenames

    # Generic exec
    exec_output         = pyqtSignal(str)
    exec_error          = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ssh:      "paramiko.SSHClient | None" = None
        self._hostname: str = ""

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, hostname: str, username: str, password: str):
        
        if not PARAMIKO_AVAILABLE:
            self.connection_failed.emit("paramiko not installed")
            return

        self._hostname = hostname
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(
                hostname=hostname,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            self._ssh = client
            self.connected.emit()
        except Exception as e:
            self.connection_failed.emit(str(e))

    def disconnect(self):
        if self._ssh:
            self._ssh.close()
            self._ssh = None

    # ------------------------------------------------------------------
    # Workspace detection
    # ------------------------------------------------------------------

    def detect_workspace(self):
        """
        Search for sros_ws on the Pi (up to depth 4 under /home).
        Emits workspace_found(path) or workspace_not_found().
        """
        result = self._exec("find /home -maxdepth 4 -name 'sros_ws'"
                            " -type d 2>/dev/null | head -1")
        if result:
            self.workspace_found.emit(result.strip())
        else:
            self.workspace_not_found.emit()

    # ------------------------------------------------------------------
    # Docker + configure
    # ------------------------------------------------------------------

    def start_docker(self, workspace: str):
        """
        Run the configure script inside the workspace directory.
        Streams stdout lines via docker_output.
        Polls port 9090 after completion to confirm rosbridge is up.
        """
        # Find the configure script — assumed to be configure*.sh in workspace
        find_cmd = f"find {workspace} -maxdepth 1 -name 'configure*.sh'"
        script = self._exec(find_cmd)
        if not script:
            self.docker_failed.emit("No configure*.sh found in workspace")
            return

        script = script.strip()
        cmd = f"cd {workspace} && bash {script}"

        try:
            _, stdout, stderr = self._ssh.exec_command(cmd, timeout=120)
            for line in iter(stdout.readline, ""):
                self.docker_output.emit(line.rstrip())
            err = stderr.read().decode()
            if err:
                self.docker_output.emit(f"[stderr] {err}")
        except Exception as e:
            self.docker_failed.emit(str(e))
            return

        # Poll port 9090 until rosbridge responds (up to 30 s)
        import time
        for _ in range(30):
            check = self._exec(
                "nc -z localhost 9090 && echo ok || echo wait"
            )
            if check and "ok" in check:
                self.docker_ready.emit()
                return
            time.sleep(1)

        self.docker_failed.emit("Timed out waiting for rosbridge on :9090")

    # ------------------------------------------------------------------
    # Launch file listing
    # ------------------------------------------------------------------

    def list_launches(self, workspace: str):
        """
        Find all *.sh files in workspace/launch/ and emit their names.
        """
        result = self._exec(
            f"find {workspace}/launch -maxdepth 1 -name '*.sh'"
            f" 2>/dev/null"
        )
        if result:
            names = [
                line.strip().split("/")[-1]
                for line in result.strip().splitlines()
                if line.strip()
            ]
            self.launches_listed.emit(names)
        else:
            self.launches_listed.emit([])

    # ------------------------------------------------------------------
    # Execute a launch script
    # ------------------------------------------------------------------

    def run_launch(self, workspace: str, script_name: str):
        """
        Execute a launch script inside the workspace/launch directory.
        Streams output via exec_output / exec_error.
        """
        cmd = f"cd {workspace}/launch && bash {script_name}"
        try:
            _, stdout, stderr = self._ssh.exec_command(cmd, timeout=60)
            for line in iter(stdout.readline, ""):
                self.exec_output.emit(line.rstrip())
            err = stderr.read().decode()
            if err:
                self.exec_error.emit(err)
        except Exception as e:
            self.exec_error.emit(str(e))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _exec(self, cmd: str) -> str | None:
        """Run a command and return stdout as a string, or None on error."""
        if not self._ssh:
            return None
        try:
            _, stdout, _ = self._ssh.exec_command(cmd, timeout=15)
            return stdout.read().decode()
        except Exception:
            return None

