from threading import Thread

from engine.interfaces.keyboard_hook_intreface import KeyboardHookInterface
from engine.interfaces.keyboard_layout_switching_system_settings_interface import \
    KeyboardLayoutSwitchingSystemSettingsInterface
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


class KeyboardLayoutManager(Thread):
    def __init__(
            self,
            keyboard_layout_manager_setup: KeyboardLayoutManagerSetup,
            keyboard_layout_switching_system_settings: KeyboardLayoutSwitchingSystemSettingsInterface,
            keyboard_hook: KeyboardHookInterface
    ):
        self._kl_manager_setup = keyboard_layout_manager_setup
        self._kl_switching_system_settings = keyboard_layout_switching_system_settings
        self._keyboard_hook = keyboard_hook
        self._stopped = False

        super().__init__()

    def run(self):
        print('starting keyboard layout manager thread...')

        self._kl_switching_system_settings.disable_system_hotkeys()
        while not self._stopped:
            self._keyboard_hook.process_events()

        self._kl_switching_system_settings.restore_system_hotkeys()
        print('stopped keyboard layout manager thread...')

    def stop(self):
        self._stopped = True
