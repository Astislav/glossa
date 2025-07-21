from itertools import cycle
from threading import Thread

from engine.interfaces.keyboard_hook_intreface import KeyboardHookInterface
from engine.interfaces.keyboard_layout_switcher_interface import KeyboardLayoutSwitcherInterface
from engine.interfaces.keyboard_layout_switching_system_settings_interface import \
    KeyboardLayoutSwitchingSystemSettingsInterface
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


class KeyboardLayoutManager(Thread):
    def __init__(
            self,
            keyboard_layout_manager_setup: KeyboardLayoutManagerSetup,
            keyboard_layout_switching_system_settings: KeyboardLayoutSwitchingSystemSettingsInterface,
            keyboard_layout_switcher: KeyboardLayoutSwitcherInterface,
            keyboard_hook: KeyboardHookInterface,
    ):
        self._kl_manager_setup = keyboard_layout_manager_setup
        self._kl_loop = cycle(self._kl_manager_setup.in_loop_keyboard_layout_ids)
        self._kl_switching_system_settings = keyboard_layout_switching_system_settings
        self._kl_switcher = keyboard_layout_switcher
        self._keyboard_hook = keyboard_hook
        self._stopped = False
        self._setup_hotkeys()

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

    def _setup_hotkeys(self):
        self._keyboard_hook.register_hook(self._kl_manager_setup.next_layout_in_loop_hotkey, self._switch_next_in_loop)

    def _switch_next_in_loop(self):
        print('switching to next layout in loop...')
        klid = next(self._kl_loop)
        self._kl_switcher.activate(klid)
