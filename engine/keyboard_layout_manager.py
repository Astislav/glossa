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

    The carousel syncs with reality: before advancing it asks the OS which
    layout is actually active (the user may have switched via the taskbar
    or a direct hotkey), advances from THAT position, and if the active
    layout is outside the carousel (e.g. Greek), returns to the last
    remembered carousel layout instead of moving on.
    """

    _NEXT_IN_LOOP = object()  # queue sentinel: resolve the target lazily, on the worker

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

        self._keyboard_hook.register_hook(self._kl_manager_setup.next_layout_in_loop_hotkey, self._switch_next_in_loop)
        for klid, hotkey in self._kl_manager_setup.klid_to_hotkey_bindings.items():
            self._keyboard_hook.register_hook(hotkey, self._switch_direct, klid)

    # --- hook callbacks: enqueue only, no work on the hook thread ---

    def _switch_next_in_loop(self):
        if not self._carousel:
            self._log.warning("carousel hotkey pressed, but the carousel is empty")
            return

        self._switch_queue.put(self._NEXT_IN_LOOP)

    def _switch_direct(self, klid: KeyboardLayoutId):
        self._switch_queue.put(klid)

    # --- worker thread ---

    def _process_switches(self):
        while True:
            item = self._switch_queue.get()
            try:
                if item is None:
                    return
                try:
                    klid = self._resolve_next_in_loop() if item is self._NEXT_IN_LOOP else item
                    self._remember_carousel_position(klid)
                    self._log.info("switching to layout %s", klid)
                    self._kl_switcher.activate(klid)
                except Exception:
                    self._log.exception("failed to switch layout")
            finally:
                self._switch_queue.task_done()

    def _resolve_next_in_loop(self) -> KeyboardLayoutId:
        # Trust the OS, not our own bookkeeping: the user may have switched
        # layouts via the taskbar or a direct hotkey since the last press.
        active_index = self._carousel_index_of(self._kl_switcher.active_layout_langid())
        if active_index is not None:
            self._carousel_index = (active_index + 1) % len(self._carousel)
        # else: the active layout is outside the carousel — return to the
        # last remembered carousel layout without advancing.

        return self._carousel[self._carousel_index]

    def _remember_carousel_position(self, klid: KeyboardLayoutId):
        if klid in self._carousel:
            self._carousel_index = self._carousel.index(klid)

    def _carousel_index_of(self, langid: int | None) -> int | None:
        if langid is None:
            return None

        # A layout handle's language id matches the last 4 hex digits of the
        # KLID — also true for variant layouts (Dvorak 00010409 -> 0409).
        suffix = f"{langid:04X}"
        for index, klid in enumerate(self._carousel):
            if klid.to_string.upper().endswith(suffix):
                return index

        return None
