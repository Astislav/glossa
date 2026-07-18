import sys
import winreg
from pathlib import Path

from injector import singleton

from nexus_kit import Root


@singleton
class Autostart:
    """Per-user autostart via HKCU\\...\\Run — no admin rights needed."""

    _RUN_BRANCH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _VALUE_NAME = "Glossa"

    def is_enabled(self) -> bool:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_BRANCH) as key:
            try:
                winreg.QueryValueEx(key, self._VALUE_NAME)
                return True
            except FileNotFoundError:
                return False

    def enable(self):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_BRANCH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self._VALUE_NAME, 0, winreg.REG_SZ, self._command())

    def disable(self):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_BRANCH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, self._VALUE_NAME)
            except FileNotFoundError:
                pass

    @staticmethod
    def _command() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'

        # Dev run: pythonw.exe (no console window) + main.py next to the project root.
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        return f'"{pythonw}" "{Root.external("main.py")}"'
