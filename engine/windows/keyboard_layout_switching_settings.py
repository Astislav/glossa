import ctypes
import winreg
from ctypes import wintypes

from engine.interfaces.keyboard_layout_switching_system_settings_interface import KeyboardLayoutSwitchingSystemSettingsInterface


class WindowsKeyboardLayoutSwitchingSettings(KeyboardLayoutSwitchingSystemSettingsInterface):
    _layout_toggle_branch = r"Keyboard Layout\\Toggle"
    _layout_hotkey_reg_name = "Layout Hotkey"
    _language_hotkey_reg_name = "Language Hotkey"

    def __init__(self):
        self._language_hot_key_id = None
        self._layout_hot_key_id = None
        self._user32 = ctypes.windll.user32
        self._user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self._user32.PostMessageW.restype = wintypes.BOOL

    def disable_system_hotkeys(self):
        disabled_value = "3"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._layout_toggle_branch, 0, winreg.KEY_ALL_ACCESS) as k:
            self._language_hot_key_id = self._get_registry_value(k, self._language_hotkey_reg_name)
            self._layout_hot_key_id = self._get_registry_value(k, self._layout_hotkey_reg_name)

            winreg.SetValueEx(k, self._language_hotkey_reg_name, 0, winreg.REG_SZ, disabled_value)
            winreg.SetValueEx(k, self._layout_hotkey_reg_name, 0, winreg.REG_SZ, disabled_value)

        self._notify()

    def restore_system_hotkeys(self):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._layout_toggle_branch, 0, winreg.KEY_ALL_ACCESS) as k:
            if self._language_hot_key_id is not None:
                winreg.SetValueEx(k, self._language_hotkey_reg_name, 0, winreg.REG_SZ, self._language_hot_key_id)

            if self._layout_hot_key_id is not None:
                winreg.SetValueEx(k, self._layout_hotkey_reg_name, 0, winreg.REG_SZ, self._layout_hot_key_id)

        self._notify()

    def _notify(self):
        buffer = ctypes.create_unicode_buffer("Keyboard Layout")
        self._user32.PostMessageW(0xFFFF, 0x001A, 0, ctypes.cast(buffer, ctypes.c_void_p).value)

    @staticmethod
    def _get_registry_value(key, name, default=None):
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return value
        except FileNotFoundError:
            return default
