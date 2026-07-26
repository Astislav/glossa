import queue
import threading

from injector import inject, singleton

from nexus_kit.interfaces import ServiceInterface

from engine.dto.key_combination import KeyCombination
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

    Carousels: the primary carousel is the checked ``in_loop`` set, driven
    by ``next_layout_in_loop_hotkey``. Additional carousels form implicitly
    when several layouts share the same direct hotkey — that combo cycles
    those layouts instead of jumping to one of them. A hotkey bound to a
    single layout stays a direct jump.

    Each carousel syncs with reality: before advancing it asks the OS which
    layout is actually active (the user may have switched via the taskbar
    or another hotkey), advances from THAT position, and if the active
    layout is outside that carousel, returns to the last remembered layout
    of that carousel instead of moving on.
    """

    _NEXT_IN_LOOP = object()  # queue sentinel: resolve the target lazily, on the worker
    _MAIN_CAROUSEL = object()

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
        self._carousels: dict[object, list[KeyboardLayoutId]] = {}
        self._carousel_indices: dict[object, int] = {}
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
        self._carousels.clear()
        self._carousel_indices.clear()

        main = list(self._kl_manager_setup.in_loop_keyboard_layout_ids)
        self._carousels[self._MAIN_CAROUSEL] = main
        self._carousel_indices[self._MAIN_CAROUSEL] = 0
        self._keyboard_hook.register_hook(
            self._kl_manager_setup.next_layout_in_loop_hotkey,
            self._switch_next_in_loop,
            self._MAIN_CAROUSEL,
        )

        # Same direct hotkey on several layouts → one extra carousel.
        # The hook stores callbacks by combo frozenset, so a shared hotkey
        # must be registered once — not once per layout.
        for hotkey, klids in self._bindings_grouped_by_hotkey():
            if len(klids) == 1:
                self._keyboard_hook.register_hook(hotkey, self._switch_direct, klids[0])
                continue

            carousel_id = hotkey.as_frozenset()
            self._carousels[carousel_id] = klids
            self._carousel_indices[carousel_id] = 0
            self._keyboard_hook.register_hook(hotkey, self._switch_next_in_loop, carousel_id)

    def _bindings_grouped_by_hotkey(self) -> list[tuple[KeyCombination, list[KeyboardLayoutId]]]:
        groups: dict[frozenset, tuple[KeyCombination, list[KeyboardLayoutId]]] = {}
        order: list[frozenset] = []
        for klid, hotkey in self._kl_manager_setup.klid_to_hotkey_bindings.items():
            key = hotkey.as_frozenset()
            if key not in groups:
                groups[key] = (hotkey, [])
                order.append(key)
            groups[key][1].append(klid)
        return [groups[key] for key in order]

    # --- hook callbacks: enqueue only, no work on the hook thread ---

    def _switch_next_in_loop(self, carousel_id: object):
        if not self._carousels.get(carousel_id):
            self._log.warning("carousel hotkey pressed, but the carousel is empty")
            return

        self._switch_queue.put((self._NEXT_IN_LOOP, carousel_id))

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
                    if isinstance(item, tuple) and item and item[0] is self._NEXT_IN_LOOP:
                        klid = self._resolve_next_in_loop(item[1])
                    else:
                        klid = item
                    self._remember_carousel_position(klid)
                    self._log.info("switching to layout %s", klid)
                    self._kl_switcher.activate(klid)
                except Exception:
                    self._log.exception("failed to switch layout")
            finally:
                self._switch_queue.task_done()

    def _resolve_next_in_loop(self, carousel_id: object) -> KeyboardLayoutId:
        carousel = self._carousels[carousel_id]
        # Trust the OS, not our own bookkeeping: the user may have switched
        # layouts via the taskbar or a direct hotkey since the last press.
        active_index = self._carousel_index_of(carousel, self._kl_switcher.active_layout_langid())
        if active_index is not None:
            self._carousel_indices[carousel_id] = (active_index + 1) % len(carousel)
        # else: the active layout is outside this carousel — return to the
        # last remembered layout of this carousel without advancing.

        return carousel[self._carousel_indices[carousel_id]]

    def _remember_carousel_position(self, klid: KeyboardLayoutId):
        for carousel_id, carousel in self._carousels.items():
            if klid in carousel:
                self._carousel_indices[carousel_id] = carousel.index(klid)

    @staticmethod
    def _carousel_index_of(carousel: list[KeyboardLayoutId], langid: int | None) -> int | None:
        if langid is None:
            return None

        # A layout handle's language id matches the last 4 hex digits of the
        # KLID — also true for variant layouts (Dvorak 00010409 -> 0409).
        suffix = f"{langid:04X}"
        for index, klid in enumerate(carousel):
            if klid.to_string.upper().endswith(suffix):
                return index

        return None
