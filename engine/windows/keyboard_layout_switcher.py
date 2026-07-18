import ctypes
from ctypes import wintypes
from time import sleep

from injector import inject, singleton

from engine.dto.keyboard_layout_id import KeyboardLayoutId
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.interfaces.keyboard_layout_switcher_interface import KeyboardLayoutSwitcherInterface
from engine.loggers import SwitcherLogger


@singleton
class WindowsKeyboardLayoutSwitcher(KeyboardLayoutSwitcherInterface):
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    _KLF_ACTIVATE = 0x00000001
    _WM_INPUT_LANG_CHANGE_REQUEST = 0x0050
    _HWND_BROADCAST = 0xFFFF
    _ERR_SLEEP_TIME_SECONDS = 0.05

    _user32.ActivateKeyboardLayout.argtypes = (wintypes.HKL, wintypes.UINT)
    _user32.PostMessageW.argtypes = (
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM
    )
    _user32.PostMessageW.restype = wintypes.BOOL

    @inject
    def __init__(self, layouts_registry: KeyboardLayoutRegistryInterface, log: SwitcherLogger):
        self._layouts_registry = layouts_registry
        self._log = log

    def activate(self, keyboard_layout_id: KeyboardLayoutId):
        if not self._layouts_registry.layout_exists(keyboard_layout_id):
            raise ValueError(
                f"Keyboard layout with ID '{keyboard_layout_id}' is not registered in the system."
            )

        self._log.info("loading keyboard layout: %s", keyboard_layout_id)
        hkl = self._user32.LoadKeyboardLayoutW(keyboard_layout_id.to_string, self._KLF_ACTIVATE)
        if not hkl:
            err = ctypes.get_last_error()
            raise OSError(f"Failed to load keyboard layout: {err}")

        self._user32.ActivateKeyboardLayout(hkl, 0)

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            self._log.info(
                "broadcasting keyboard layout change: %s (attempt %d/%d)",
                keyboard_layout_id, attempt, max_attempts
            )
            if self._user32.PostMessageW(self._HWND_BROADCAST, self._WM_INPUT_LANG_CHANGE_REQUEST, 0, hkl):
                break

            if self._user32.SendMessageTimeoutW(
                    self._HWND_BROADCAST,
                    self._WM_INPUT_LANG_CHANGE_REQUEST,
                    0,
                    ctypes.wintypes.LPARAM(hkl),
                    0x0002 | 0x0001,
                    150,
                    None):
                break

            if attempt <= max_attempts:
                err = ctypes.get_last_error()
                self._log.warning("PostMessageW failed with error: %s", err)
                sleep(self._ERR_SLEEP_TIME_SECONDS)
