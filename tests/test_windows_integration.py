"""Real-Windows integration tests: touch the actual HKCU registry.

Gated behind GLOSSA_WINDOWS_INTEGRATION=1 — meant for disposable CI runners
(ci.yml sets it). Safe by construction: original values are restored in
finally, but don't run casually on a workstation.
"""
import os
import winreg

import pytest

from engine.windows.keyboard_layout_switching_settings import WindowsKeyboardLayoutSwitchingSettings

pytestmark = pytest.mark.skipif(
    not os.environ.get("GLOSSA_WINDOWS_INTEGRATION"),
    reason="touches the real HKCU registry — set GLOSSA_WINDOWS_INTEGRATION=1 to enable",
)


def toggle_values():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\\Toggle") as k:
        def value(name):
            try:
                return winreg.QueryValueEx(k, name)[0]
            except FileNotFoundError:
                return None
        return value("Language Hotkey"), value("Layout Hotkey")


def restore_values(originals):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\\Toggle", 0, winreg.KEY_SET_VALUE) as k:
        for name, value in zip(("Language Hotkey", "Layout Hotkey"), originals):
            if value is not None:
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


def test_disable_restore_cycle(tmp_path):
    initial = toggle_values()
    try:
        settings = WindowsKeyboardLayoutSwitchingSettings()
        settings._backup_path = tmp_path / "backup.json"

        settings.disable_system_hotkeys()
        assert toggle_values() == ("3", "3")
        assert settings._backup_path.exists()

        settings.restore_system_hotkeys()
        assert toggle_values() == initial
        assert not settings._backup_path.exists()
    finally:
        restore_values(initial)


def test_crash_recovery_from_backup(tmp_path):
    initial = toggle_values()
    try:
        backup_path = tmp_path / "backup.json"

        crashed_run = WindowsKeyboardLayoutSwitchingSettings()
        crashed_run._backup_path = backup_path
        crashed_run.disable_system_hotkeys()
        del crashed_run  # hard kill: no restore, RAM state gone

        next_run = WindowsKeyboardLayoutSwitchingSettings()
        next_run._backup_path = backup_path
        next_run.disable_system_hotkeys()  # must adopt originals from the backup
        next_run.restore_system_hotkeys()

        assert toggle_values() == initial
        assert not backup_path.exists()
    finally:
        restore_values(initial)
