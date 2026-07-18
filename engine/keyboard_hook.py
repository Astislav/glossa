import keyboard
from injector import inject, singleton

from engine.dto.key_combination import KeyCombination
from engine.interfaces.keyboard_hook_interface import KeyboardHookInterface
from engine.loggers import HookLogger


@singleton
class KeyboardHook(KeyboardHookInterface):
    """Global hotkey dispatcher with prefix-conflict resolution.

    A combo with no registered proper superset fires immediately on key-down
    (the familiar behavior). A combo that IS a proper subset of another
    registered combo (e.g. Alt+Shift when Alt+Shift+G is also registered)
    cannot fire on key-down — at that moment we don't yet know whether the
    extra key will follow. Such a combo is "armed" instead and fires on the
    first key-up of one of its keys, unless a superset combo fired during
    the hold (which suppresses it until all of its keys are released).
    """

    @inject
    def __init__(self, log: HookLogger):
        self._log = log
        self._pressed = set()
        self._active = set()      # immediate combos fired and still held
        self._armed = set()       # deferred combos fully pressed, awaiting release
        self._suppressed = set()  # deferred combos beaten by a superset this hold
        self._hotkeys = set()
        self._hotkeys_to_callback = {}
        self._hook_handle = None

    def register_hook(self, key_combination: KeyCombination, callback: callable, *args):
        combo = key_combination.as_frozenset()
        self._hotkeys.update(combo)
        self._hotkeys_to_callback[combo] = {'callback': callback, 'args': args}

    def unregister_all(self):
        self._hotkeys.clear()
        self._hotkeys_to_callback.clear()
        self._pressed.clear()
        self._active.clear()
        self._armed.clear()
        self._suppressed.clear()

    def start(self):
        if self._hook_handle is None:
            self._hook_handle = keyboard.hook(self._handler)

    def stop(self):
        if self._hook_handle is not None:
            keyboard.unhook(self._hook_handle)
            self._hook_handle = None

    def _handler(self, event: keyboard.KeyboardEvent):
        # This runs inside the low-level hook chain for EVERY keystroke in
        # the system — the common case (an unregistered key) must bail out
        # with a couple of set lookups and no string allocations.
        key = event.name
        if key not in self._hotkeys:
            if not (key.startswith('left ') or key.startswith('right ')):
                return
            key = key.split(' ', 1)[1]
            if key not in self._hotkeys:
                return

        if event.event_type == keyboard.KEY_DOWN:
            self._on_key_down(key)
        else:
            self._on_key_up(key)

    def _on_key_down(self, key: str):
        self._pressed.add(key)

        for combo in self._hotkeys_to_callback:
            if not combo.issubset(self._pressed):
                continue
            if combo in self._active or combo in self._armed or combo in self._suppressed:
                continue

            if self._has_registered_superset(combo):
                self._armed.add(combo)
            else:
                self._active.add(combo)
                self._fire(combo)

    def _on_key_up(self, key: str):
        # A deferred combo fires on the first release of one of its keys —
        # the hold ended without the conflicting superset being pressed.
        for combo in list(self._armed):
            if key in combo and combo.issubset(self._pressed):
                self._armed.discard(combo)
                self._fire(combo)

        self._pressed.discard(key)

        for combo in list(self._active):
            if not combo.issubset(self._pressed):
                self._active.discard(combo)
        for combo in list(self._armed):
            if not combo.issubset(self._pressed):
                self._armed.discard(combo)
        for combo in list(self._suppressed):
            if not (combo & self._pressed):
                self._suppressed.discard(combo)

    def _has_registered_superset(self, combo: frozenset) -> bool:
        return any(combo < other for other in self._hotkeys_to_callback)

    def _fire(self, combo: frozenset):
        # A fired combo beats its armed prefixes for the rest of the hold.
        for other in self._hotkeys_to_callback:
            if other < combo:
                self._armed.discard(other)
                self._suppressed.add(other)

        callback_setup = self._hotkeys_to_callback[combo]
        try:
            callback_setup['callback'](*callback_setup['args'])
        except Exception:
            # The handler runs on the keyboard library's listener thread —
            # an escaping exception would kill hotkey processing entirely.
            self._log.exception("hotkey callback failed for %s", '+'.join(sorted(combo)))
