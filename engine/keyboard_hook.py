import keyboard
from injector import singleton

from engine.dto.key_combination import KeyCombination
from engine.interfaces.keyboard_hook_interface import KeyboardHookInterface


@singleton
class KeyboardHook(KeyboardHookInterface):
    def __init__(self):
        self._pressed = set()
        self._active = set()
        self._hotkeys = set()
        self._hotkeys_to_callback = {}
        self._hook_handle = None

    def register_hook(self, key_combination: KeyCombination, callback: callable, *args):
        self._hotkeys.update(key_combination.as_frozenset())
        self._hotkeys_to_callback[key_combination.as_frozenset()] = {'callback': callback, 'args': args}

    def start(self):
        if self._hook_handle is None:
            self._hook_handle = keyboard.hook(self._handler)

    def stop(self):
        if self._hook_handle is not None:
            keyboard.unhook(self._hook_handle)
            self._hook_handle = None

    @staticmethod
    def _normalize(name: str) -> str:
        return name.replace('left ', '').replace('right ', '')

    def _handler(self, event: keyboard.KeyboardEvent):
        key = self._normalize(event.name)

        if key not in self._hotkeys:
            return

        if event.event_type == keyboard.KEY_DOWN:
            self._pressed.add(key)
        else:
            self._pressed.discard(key)

        for combo, callback_setup in self._hotkeys_to_callback.items():
            if combo.issubset(self._pressed):
                if combo not in self._active:
                    callback = callback_setup['callback']
                    args = callback_setup['args']
                    callback(*args)

                    self._active.add(combo)
            else:
                self._active.discard(combo)
