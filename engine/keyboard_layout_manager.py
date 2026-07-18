import queue
import threading

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
    layouts.

    Responsiveness contract: hotkey callbacks run INSIDE the low-level
    keyboard hook chain — while a callback runs, Windows delays delivering
    that key event to every application. So the callbacks here only resolve
    the target layout and enqueue it; the actual switch (LoadKeyboardLayout,
    broadcasts, possible retries) happens on a dedicated worker thread.

    The carousel remembers its position: a direct hotkey that leaves the
    carousel (e.g. Greek) does not advance it, and the next carousel press
    returns to the last carousel layout instead of moving on.
    """

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
        self._carousel: list[KeyboardLayoutId] = []
        self._carousel_index = 0
        self._away_from_carousel = False
        self._switch_queue: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None

    def start(self):
        # The setup is populated by SettingsStore at startup — register
        # hotkeys here, not in the constructor.
        self._register_hotkeys()
        self._worker = threading.Thread(target=self._process_switches, daemon=True, name="layout-switch-worker")
        self._worker.start()
        self._keyboard_hook.start()
        self._log.info("keyboard layout manager started")

    def stop(self):
        self._keyboard_hook.stop()
        if self._worker is not None:
            self._switch_queue.put(None)
            self._worker.join(timeout=2.0)
            self._worker = None
        self._log.info("keyboard layout manager stopped")

    def pause_hotkeys(self):
        """Temporarily detach the hook — e.g. while the UI captures a new
        hotkey and the combination must not trigger a switch."""
        self._keyboard_hook.stop()

    def resume_hotkeys(self):
        self._keyboard_hook.start()

    def reload(self):
        """Re-read the setup and re-register hotkeys — called after the
        settings change at runtime."""
        self._keyboard_hook.stop()
        self._keyboard_hook.unregister_all()
        self._register_hotkeys()
        self._keyboard_hook.start()
        self._log.info("hotkeys reloaded from settings")

    def flush(self):
        """Block until every queued switch has been executed — for
        deterministic tests."""
        self._switch_queue.join()

    def _register_hotkeys(self):
        self._carousel = list(self._kl_manager_setup.in_loop_keyboard_layout_ids)
        self._carousel_index = 0
        self._away_from_carousel = False

        self._keyboard_hook.register_hook(self._kl_manager_setup.next_layout_in_loop_hotkey, self._switch_next_in_loop)
        for klid, hotkey in self._kl_manager_setup.klid_to_hotkey_bindings.items():
            self._keyboard_hook.register_hook(hotkey, self._switch_direct, klid)

    # --- hook callbacks: cheap resolution + enqueue only ---

    def _switch_next_in_loop(self):
        if not self._carousel:
            self._log.warning("carousel hotkey pressed, but the carousel is empty")
            return

        if self._away_from_carousel:
            # Coming back from a direct-switched layout: return to the last
            # active carousel layout instead of advancing past it.
            self._away_from_carousel = False
        else:
            self._carousel_index = (self._carousel_index + 1) % len(self._carousel)

        self._switch_queue.put(self._carousel[self._carousel_index])

    def _switch_direct(self, klid: KeyboardLayoutId):
        if klid in self._carousel:
            self._carousel_index = self._carousel.index(klid)
            self._away_from_carousel = False
        else:
            self._away_from_carousel = True

        self._switch_queue.put(klid)

    # --- worker thread ---

    def _process_switches(self):
        while True:
            klid = self._switch_queue.get()
            try:
                if klid is None:
                    return
                self._log.info("switching to layout %s", klid)
                try:
                    self._kl_switcher.activate(klid)
                except Exception:
                    self._log.exception("failed to activate layout %s", klid)
            finally:
                self._switch_queue.task_done()
