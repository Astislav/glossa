import keyboard

from engine.dto.key_combination import KeyCombination
from engine.interfaces.keyboard_hook_intreface import KeyboardHookInterface


class KeyboardHook(KeyboardHookInterface):
    def __init__(self):
        self._pressed = set()
        self._active = set()
        self._hotkeys = set()
        self._hotkeys_to_callback = {}
        self._keyboard = keyboard

        self._keyboard.hook(self._handler)

    def __del__(self):
        keyboard.unhook(self._handler)

    def register_hook(self, key_combination: KeyCombination, callback: callable, *args):
        self._hotkeys.update(key_combination.as_frozenset())
        self._hotkeys_to_callback[key_combination.as_frozenset()] = {'callback': callback, 'args': args}

    def process_events(self):
        pass

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
