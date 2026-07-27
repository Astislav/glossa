"""Real-registry integration tests against a THROWAWAY HKCU key.

These exercise genuine winreg semantics (create/set/delete/query) for the
disable/restore/crash-recovery logic without touching the real system
`Keyboard Layout\\Toggle` — so they are safe to run anywhere, every time.
"""
import winreg

import pytest

from engine.windows.keyboard_layout_switching_settings import WindowsKeyboardLayoutSwitchingSettings

SANDBOX_BRANCH = r"Software\Glossa\TestToggle"
LANGUAGE = "Language Hotkey"
LAYOUT = "Layout Hotkey"


@pytest.fixture
def sandbox():
    """A fresh, empty HKCU key that stands in for the Toggle branch."""
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, SANDBOX_BRANCH)
    yield SANDBOX_BRANCH
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, SANDBOX_BRANCH)
    except FileNotFoundError:
        pass


def seed(values: dict):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SANDBOX_BRANCH, 0, winreg.KEY_SET_VALUE) as k:
        for name, value in values.items():
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


def toggle_values():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SANDBOX_BRANCH) as k:
        def value(name):
            try:
                return winreg.QueryValueEx(k, name)[0]
            except FileNotFoundError:
                return None
        return value(LANGUAGE), value(LAYOUT)


def settings(sandbox, tmp_path):
    return WindowsKeyboardLayoutSwitchingSettings(
        toggle_branch=sandbox, backup_path=tmp_path / "backup.json"
    )


def test_disable_restore_with_existing_values(sandbox, tmp_path):
    seed({LANGUAGE: "1", LAYOUT: "3"})
    s = settings(sandbox, tmp_path)

    s.disable_system_hotkeys()
    assert toggle_values() == ("3", "3")
    assert s._backup_path.exists()

    s.restore_system_hotkeys()
    assert toggle_values() == ("1", "3")
    assert not s._backup_path.exists()


def test_disable_restore_on_fresh_machine(sandbox, tmp_path):
    # Single-layout machine: the Toggle values don't exist. Restore must
    # DELETE what we wrote, not leave the hotkeys disabled.
    assert toggle_values() == (None, None)
    s = settings(sandbox, tmp_path)

    s.disable_system_hotkeys()
    assert toggle_values() == ("3", "3")

    s.restore_system_hotkeys()
    assert toggle_values() == (None, None)


def test_crash_recovery_with_existing_values(sandbox, tmp_path):
    seed({LANGUAGE: "1", LAYOUT: "3"})

    crashed = settings(sandbox, tmp_path)
    crashed.disable_system_hotkeys()  # then "crash": no restore, RAM gone
    del crashed

    next_run = settings(sandbox, tmp_path)
    next_run.disable_system_hotkeys()  # must adopt originals from the backup
    next_run.restore_system_hotkeys()

    assert toggle_values() == ("1", "3")
    assert not next_run._backup_path.exists()


def test_crash_recovery_on_fresh_machine(sandbox, tmp_path):
    assert toggle_values() == (None, None)

    crashed = settings(sandbox, tmp_path)
    crashed.disable_system_hotkeys()
    del crashed

    next_run = settings(sandbox, tmp_path)
    next_run.disable_system_hotkeys()
    next_run.restore_system_hotkeys()

    assert toggle_values() == (None, None)


def test_recover_if_needed_restores_leftover_disabled_state(sandbox, tmp_path):
    # A prior run "crashed" with the hotkeys disabled and a backup on disk.
    # A fresh process must restore them at startup (recover_if_needed), so
    # native switching works again while the app waits to take over.
    seed({LANGUAGE: "1", LAYOUT: "3"})
    crashed = settings(sandbox, tmp_path)
    crashed.disable_system_hotkeys()
    assert toggle_values() == ("3", "3")
    del crashed  # no restore — RAM gone, backup remains

    fresh = settings(sandbox, tmp_path)
    fresh.recover_if_needed()

    assert toggle_values() == ("1", "3")
    assert not fresh._backup_path.exists()


def test_recover_if_needed_is_a_noop_without_backup(sandbox, tmp_path):
    seed({LANGUAGE: "1", LAYOUT: "3"})
    fresh = settings(sandbox, tmp_path)

    fresh.recover_if_needed()  # no backup → nothing changes

    assert toggle_values() == ("1", "3")


def test_live_value_beats_stale_backup(sandbox, tmp_path):
    # The user reconfigured the system after a crash — the live value wins.
    seed({LANGUAGE: "1", LAYOUT: "3"})
    crashed = settings(sandbox, tmp_path)
    crashed.disable_system_hotkeys()
    del crashed

    seed({LANGUAGE: "2"})  # user set Ctrl+Shift while Glossa was dead
    next_run = settings(sandbox, tmp_path)
    next_run.disable_system_hotkeys()
    next_run.restore_system_hotkeys()

    assert toggle_values() == ("2", "3")
