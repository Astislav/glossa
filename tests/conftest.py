import logging

import pytest

from engine.dto.keyboard_layout import KeyboardLayout
from engine.dto.keyboard_layout_id import KeyboardLayoutId
from engine.interfaces.keyboard_hook_interface import KeyboardHookInterface
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.interfaces.keyboard_layout_switcher_interface import KeyboardLayoutSwitcherInterface


class FakeKeyboardLayoutId(KeyboardLayoutId):
    def __init__(self, layout_id: str):
        self._layout_id = layout_id

    @property
    def to_string(self) -> str:
        return self._layout_id


class FakeRegistry(KeyboardLayoutRegistryInterface):
    def __init__(self, klid_strings: list[str]):
        self._layouts = [KeyboardLayout(s, FakeKeyboardLayoutId(s)) for s in klid_strings]

    def layouts(self) -> list[KeyboardLayout]:
        return list(self._layouts)

    def layout_exists(self, keyboard_layout_id: KeyboardLayoutId) -> bool:
        return any(layout.layout_id == keyboard_layout_id for layout in self._layouts)


class FakeSwitcher(KeyboardLayoutSwitcherInterface):
    def __init__(self, initial_langid: int | None = None):
        self.activated: list[str] = []
        self.current_langid = initial_langid

    def activate(self, keyboard_layout_id: KeyboardLayoutId):
        self.activated.append(keyboard_layout_id.to_string)
        self.current_langid = int(keyboard_layout_id.to_string[-4:], 16)

    def active_layout_langid(self) -> int | None:
        return self.current_langid


class FakeHook(KeyboardHookInterface):
    def __init__(self):
        self.registrations: dict[frozenset, tuple] = {}
        self.running = False

    def register_hook(self, key_combination, callback, *args):
        self.registrations[key_combination.as_frozenset()] = (callback, args)

    def unregister_all(self):
        self.registrations.clear()

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def fire(self, hotkey_string: str):
        """Test helper: trigger the callback registered for a hotkey."""
        combo = frozenset(k.strip().lower() for k in hotkey_string.split("+"))
        callback, args = self.registrations[combo]
        callback(*args)


@pytest.fixture
def test_logger():
    return logging.getLogger("test")
