import ctypes
import json
import os
import winreg
from ctypes import wintypes
from pathlib import Path

from injector import singleton

from nexus_kit import Root

from engine.dto.key_combination import KeyCombination
from engine.interfaces.keyboard_layout_switching_system_settings_interface import KeyboardLayoutSwitchingSystemSettingsInterface


@singleton
class WindowsKeyboardLayoutSwitchingSettings(KeyboardLayoutSwitchingSystemSettingsInterface):
    _layout_toggle_branch = r"Keyboard Layout\\Toggle"
    _layout_hotkey_reg_name = "Layout Hotkey"
    _language_hotkey_reg_name = "Language Hotkey"

    _DISABLED = "3"
    _WM_SETTINGCHANGE = 0x001A
    _HWND_BROADCAST = 0xFFFF
    _SMTO_ABORTIFHUNG = 0x0002

    def __init__(self):
        self._language_hot_key_id = None
        self._layout_hot_key_id = None
        self._user32 = ctypes.windll.user32
        self._user32.SendMessageTimeoutW.argtypes = (
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
            wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
        )
        # Survives a hard kill: the original values are persisted before we
        # overwrite them, and a later run treats a leftover backup as the
        # true originals (RAM alone would lose them on crash/power loss).
        self._backup_path = Path(Root.external("settings", "system_hotkeys_backup.json"))

    def disable_system_hotkeys(self):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._layout_toggle_branch, 0, winreg.KEY_ALL_ACCESS) as k:
            current = (
                self._get_registry_value(k, self._language_hotkey_reg_name),
                self._get_registry_value(k, self._layout_hotkey_reg_name),
            )
            self._language_hot_key_id, self._layout_hot_key_id = \
                self._resolve_originals(current, self._load_backup())
            self._save_backup((self._language_hot_key_id, self._layout_hot_key_id))

            winreg.SetValueEx(k, self._language_hotkey_reg_name, 0, winreg.REG_SZ, self._DISABLED)
            winreg.SetValueEx(k, self._layout_hotkey_reg_name, 0, winreg.REG_SZ, self._DISABLED)

        self._notify()

    def restore_system_hotkeys(self):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._layout_toggle_branch, 0, winreg.KEY_ALL_ACCESS) as k:
            if self._language_hot_key_id is not None:
                winreg.SetValueEx(k, self._language_hotkey_reg_name, 0, winreg.REG_SZ, self._language_hot_key_id)

            if self._layout_hot_key_id is not None:
                winreg.SetValueEx(k, self._layout_hotkey_reg_name, 0, winreg.REG_SZ, self._layout_hot_key_id)

        self._notify()
        self._backup_path.unlink(missing_ok=True)

    def system_switch_hotkey(self) -> KeyCombination | None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._layout_toggle_branch) as k:
            value = self._get_registry_value(k, self._language_hotkey_reg_name)

        return self._hotkey_from_toggle_value(value)

    @staticmethod
    def _hotkey_from_toggle_value(value: str | None) -> KeyCombination | None:
        # HKCU\Keyboard Layout\Toggle, "Language Hotkey": 1 = Alt+Shift,
        # 2 = Ctrl+Shift, 3 = disabled, 4 = grave accent (not a combo we host).
        if value == "1":
            return KeyCombination.from_hotkey_string("alt+shift")
        if value == "2":
            return KeyCombination.from_hotkey_string("ctrl+shift")
        return None

    @classmethod
    def _resolve_originals(cls, current: tuple, backup: tuple | None) -> tuple:
        """Decide what the user's true original values are.

        A "disabled" current value with a backup present means a previous
        run died before restoring — take the backed-up original. A live
        (non-disabled) current value always wins: the user may have
        reconfigured the system since the crash.
        """
        if backup is None:
            return current

        current_language, current_layout = current
        backup_language, backup_layout = backup
        return (
            backup_language if current_language == cls._DISABLED else current_language,
            backup_layout if current_layout == cls._DISABLED else current_layout,
        )

    def _load_backup(self) -> tuple | None:
        try:
            data = json.loads(self._backup_path.read_text(encoding="utf-8"))
            return data["language_hotkey"], data["layout_hotkey"]
        except (OSError, ValueError, KeyError):
            return None

    def _save_backup(self, originals: tuple):
        self._backup_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write (temp file + rename): a power cut mid-write must not
        # leave a truncated backup — it is our only copy of the originals.
        temp_path = self._backup_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps({"language_hotkey": originals[0], "layout_hotkey": originals[1]}),
            encoding="utf-8",
        )
        os.replace(temp_path, self._backup_path)

    def _notify(self):
        # WM_SETTINGCHANGE carries a string POINTER — it cannot be posted:
        # the address is meaningless in receiving processes and the buffer
        # dies before delivery. Microsoft prescribes SendMessageTimeout.
        buffer = ctypes.create_unicode_buffer("Keyboard Layout")
        self._user32.SendMessageTimeoutW(
            self._HWND_BROADCAST,
            self._WM_SETTINGCHANGE,
            0,
            ctypes.cast(buffer, ctypes.c_void_p).value,
            self._SMTO_ABORTIFHUNG,
            100,
            None,
        )

    @staticmethod
    def _get_registry_value(key, name, default=None):
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return value
        except FileNotFoundError:
            return default
