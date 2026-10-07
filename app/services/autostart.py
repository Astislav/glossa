import os
import subprocess
import sys
import tempfile
import winreg
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from xml.sax.saxutils import escape

from injector import inject, singleton

from nexus_kit import Root

from app.loggers import AutostartLogger

_TASK_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
_CREATE_NO_WINDOW = 0x08000000  # windowed app: never flash a console for schtasks


def build_task_xml(user_id: str, command: str, arguments: str, working_directory: str) -> str:
    """Task Scheduler definition for a per-user logon start.

    Why not HKCU\\...\\Run: Explorer holds back Run entries until the
    desktop "settles", which under an antivirus at boot measured almost six
    minutes. A logon trigger fires right at sign-in. The non-default settings
    matter: tasks run at below-normal priority unless told otherwise, are
    killed after 72 hours, and don't start (or get stopped) on battery.
    """
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="{_TASK_NS}">
  <RegistrationInfo>
    <Description>Starts Glossa when you sign in.</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{escape(user_id)}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{escape(user_id)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>4</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(command)}</Command>
      <Arguments>{escape(arguments)}</Arguments>
      <WorkingDirectory>{escape(working_directory)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def parse_task_command(task_xml: str) -> tuple[str, str] | None:
    """(command, arguments) of a registered task's first Exec action."""
    try:
        root = ElementTree.fromstring(task_xml)
    except ElementTree.ParseError:
        return None
    ns = {"t": _TASK_NS}
    exec_node = root.find("t:Actions/t:Exec", ns)
    if exec_node is None:
        return None
    return (exec_node.findtext("t:Command", "", ns), exec_node.findtext("t:Arguments", "", ns))


@singleton
class Autostart:
    """Per-user autostart at sign-in via a Task Scheduler logon task — no
    admin rights needed. Falls back to HKCU\\...\\Run if the task can't be
    registered (e.g. Task Scheduler disabled by policy)."""

    _RUN_BRANCH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _VALUE_NAME = "Glossa"

    @inject
    def __init__(self, log: AutostartLogger):
        self._log = log
        self._task_name = f"Glossa autostart ({os.environ.get('USERNAME', 'user')})"

    # --- public API (used by the settings window) ---

    def is_enabled(self) -> bool:
        return self._task_registered() or self._run_entry_present()

    def enable(self):
        if self._register_task():
            self._remove_run_entry()  # one launcher only
            return

        self._log.warning("could not register the logon task — falling back to the Run key")
        self._write_run_entry()

    def disable(self):
        self._delete_task()
        self._remove_run_entry()

    def migrate(self):
        """Called at startup of the shipped exe: move a legacy Run entry that
        launches *this* exe to the logon task, and re-register the task if the
        exe it points to no longer exists (moved or renamed).

        Deliberately conservative: running from source must never repoint the
        real autostart, and running a second copy of the exe (say, a fresh
        download) must not silently steal it from the installed one."""
        if not getattr(sys, "frozen", False):
            return

        command = self._command_parts()[0]
        run_value = self._run_entry_value()
        if run_value is not None and command.lower() in run_value.lower():
            self._log.info("moving autostart from the Run key to a logon task")
            self.enable()
            return

        registered = self._registered_command()
        if registered is not None and not Path(registered[0]).exists():
            self._log.info("autostart points to a missing exe — re-registering to this one")
            self.enable()

    # --- Task Scheduler ---

    def _register_task(self) -> bool:
        command, arguments, working_directory = self._command_parts()
        user_id = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"
        xml = build_task_xml(user_id, command, arguments, working_directory)

        fd, path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        try:
            Path(path).write_text(xml, encoding="utf-16")
            result = self._schtasks("/Create", "/TN", self._task_name, "/XML", path, "/F")
        finally:
            Path(path).unlink(missing_ok=True)

        if result.returncode != 0:
            self._log.warning("schtasks /Create failed: %s", result.stdout.strip() or result.stderr.strip())
            return False
        return True

    def _delete_task(self):
        self._schtasks("/Delete", "/TN", self._task_name, "/F")

    def _task_registered(self) -> bool:
        return self._schtasks("/Query", "/TN", self._task_name).returncode == 0

    def _registered_command(self) -> tuple[str, str] | None:
        result = self._schtasks("/Query", "/TN", self._task_name, "/XML")
        if result.returncode != 0:
            return None
        return parse_task_command(result.stdout)

    @staticmethod
    def _schtasks(*args: str) -> subprocess.CompletedProcess:
        # schtasks writes to a pipe in the OEM code page (cp866 on a Russian
        # system), not the ANSI one Python would assume — decode explicitly,
        # or a path with Cyrillic in it never matches and gets re-registered
        # on every start.
        return subprocess.run(
            ["schtasks", *args],
            capture_output=True, encoding="oem", errors="replace",
            creationflags=_CREATE_NO_WINDOW,
        )

    # --- legacy Run key (fallback) ---

    def _run_entry_present(self) -> bool:
        return self._run_entry_value() is not None

    def _run_entry_value(self) -> str | None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_BRANCH) as key:
            try:
                return winreg.QueryValueEx(key, self._VALUE_NAME)[0]
            except FileNotFoundError:
                return None

    def _write_run_entry(self):
        command, arguments, _ = self._command_parts()
        value = f'"{command}" {arguments}'.strip()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_BRANCH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self._VALUE_NAME, 0, winreg.REG_SZ, value)

    def _remove_run_entry(self):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_BRANCH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, self._VALUE_NAME)
            except FileNotFoundError:
                pass

    # --- what to launch ---

    @staticmethod
    def _command_parts() -> tuple[str, str, str]:
        """(command, arguments, working directory)."""
        if getattr(sys, "frozen", False):
            exe = Path(sys.executable)
            return str(exe), "", str(exe.parent)

        # Dev run: pythonw.exe (no console window) + main.py at the project root.
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        main = Path(Root.external("main.py"))
        return str(pythonw), f'"{main}"', str(main.parent)
