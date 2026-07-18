from itertools import cycle

from injector import inject, singleton

from nexus_kit.interfaces import ServiceInterface

from engine.dto.keyboard_layout_id import KeyboardLayoutId
from engine.interfaces.keyboard_hook_interface import KeyboardHookInterface
from engine.interfaces.keyboard_layout_switcher_interface import KeyboardLayoutSwitcherInterface
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from engine.loggers import ManagerLogger


@singleton
class KeyboardLayoutManager(ServiceInterface):
    """Registers the configured hotkeys and reacts to them by switching
    layouts. The `keyboard` library delivers events on its own listener
    thread, so no thread of our own is needed — start() arms the hook,
    stop() removes it."""

    @inject
    def __init__(
            self,
            keyboard_layout_manager_setup: KeyboardLayoutManagerSetup,
            keyboard_layout_switcher: KeyboardLayoutSwitcherInterface,
            keyboard_hook: KeyboardHookInterface,
            log: ManagerLogger,
    ):
        self._kl_manager_setup = keyboard_layout_manager_setup
        self._kl_switcher = keyboard_layout_switcher
        self._keyboard_hook = keyboard_hook
        self._log = log
        self._kl_loop = None

    def start(self):
        # The setup is populated by SettingsStore at startup — build the
        # cycle and register hotkeys here, not in the constructor.
        self._kl_loop = cycle(self._kl_manager_setup.in_loop_keyboard_layout_ids)
        self._keyboard_hook.register_hook(self._kl_manager_setup.next_layout_in_loop_hotkey, self._switch_next_in_loop)
        for klid, hotkey in self._kl_manager_setup.klid_to_hotkey_bindings.items():
            self._keyboard_hook.register_hook(hotkey, self._switch_direct, klid)

        self._keyboard_hook.start()
        self._log.info("keyboard layout manager started")

    def stop(self):
        self._keyboard_hook.stop()
        self._log.info("keyboard layout manager stopped")

    def _switch_next_in_loop(self):
        klid = next(self._kl_loop)
        self._log.info("switching to next layout in loop: %s", klid)
        self._kl_switcher.activate(klid)

    def _switch_direct(self, klid: KeyboardLayoutId):
        self._log.info("switching to layout %s directly", klid)
        self._kl_switcher.activate(klid)
