"""Shutdown/logoff must give the system hotkeys back. A tray-only Qt app never
hears about it unless it owns a real top-level window — SessionEndWatcher."""
import ctypes
import winreg

import pytest
from PySide6.QtWidgets import QApplication

from app.services.system_hotkeys_guard import SystemHotkeysGuard
from app.session_end_watcher import (
    WM_ENDSESSION, WM_QUERYENDSESSION, SessionEndWatcher, send_session_message,
)
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from engine.windows.keyboard_layout_switching_settings import WindowsKeyboardLayoutSwitchingSettings
from tests.conftest import FakeRegistry

SANDBOX = r"Software\Glossa\TestToggleSessionEnd"


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_watcher_is_a_hidden_top_level_window(qapp):
    watcher = SessionEndWatcher(lambda: None, lambda: None)
    hwnd = int(watcher.winId())
    user32 = ctypes.windll.user32

    assert not user32.IsWindowVisible(hwnd)
    assert user32.GetParent(hwnd) == 0  # top-level: Windows broadcasts shutdown to it


def test_watcher_reports_end_cancel_and_end(qapp):
    calls = []
    watcher = SessionEndWatcher(lambda: calls.append("end"), lambda: calls.append("resumed"))
    hwnd = int(watcher.winId())

    reply = send_session_message(hwnd, WM_QUERYENDSESSION)
    send_session_message(hwnd, WM_ENDSESSION, 0)   # shutdown cancelled
    send_session_message(hwnd, WM_ENDSESSION, 1)   # session really ends

    assert calls == ["end", "resumed", "end"]
    assert reply == 1  # we never block the shutdown


class SilentLogger:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass


@pytest.fixture
def sandbox_guard(tmp_path):
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, SANDBOX)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SANDBOX, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "Language Hotkey", 0, winreg.REG_SZ, "1")
        winreg.SetValueEx(k, "Layout Hotkey", 0, winreg.REG_SZ, "3")
    settings = WindowsKeyboardLayoutSwitchingSettings(toggle_branch=SANDBOX, backup_path=tmp_path / "backup.json")
    guard = SystemHotkeysGuard(settings, KeyboardLayoutManagerSetup(FakeRegistry(["00000409", "00000419"])), SilentLogger())
    yield guard
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, SANDBOX)


def language_hotkey():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SANDBOX) as k:
        return winreg.QueryValueEx(k, "Language Hotkey")[0]


def test_shutdown_message_restores_the_registry(qapp, sandbox_guard):
    sandbox_guard.start()
    sandbox_guard.activate()
    assert language_hotkey() == "3"  # taken over

    watcher = SessionEndWatcher(sandbox_guard.stop, sandbox_guard.activate)
    send_session_message(int(watcher.winId()), WM_QUERYENDSESSION)

    assert language_hotkey() == "1"  # given back before the process is killed


def test_cancelled_shutdown_takes_over_again(qapp, sandbox_guard):
    sandbox_guard.start()
    sandbox_guard.activate()
    watcher = SessionEndWatcher(sandbox_guard.stop, sandbox_guard.activate)
    hwnd = int(watcher.winId())

    send_session_message(hwnd, WM_QUERYENDSESSION)
    assert language_hotkey() == "1"
    send_session_message(hwnd, WM_ENDSESSION, 0)  # user cancelled the shutdown

    assert language_hotkey() == "3"  # Glossa is in charge again — no double switching
    sandbox_guard.stop()
