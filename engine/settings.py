from typing import Optional

from engine.dto.key_combination import KeyCombination
from engine.dto.keyboard_layout import KeyboardLayout
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface


class KeyboardLayoutManagerSetup:
    _in_loop_keyboard_layout_ids: list[str] = []
    _next_layout_in_loop_hotkey: Optional[KeyCombination] = None
    _klid_to_hotkey_bindings: dict[str, KeyCombination] = {}
    _keyboard_layout_registry: KeyboardLayoutRegistryInterface

    def __init__(self, keyboard_layout_registry: KeyboardLayoutRegistryInterface):
        self._keyboard_layout_registry = keyboard_layout_registry

    def load(self, json: dict):
        self.in_loop_keyboard_layout_ids = json.get("in_loop_kl_ids", [])
        self.next_layout_in_loop_hotkey = KeyCombination.from_hotkey_string(
            json.get("next_kl_hotkey", 'Alt+Shift')
        )
        self.klid_to_hotkey_bindings = json.get("klid_to_hotkey", {})

    @property
    def klid_to_hotkey_bindings(self) -> dict[str, KeyCombination]:
        return self._klid_to_hotkey_bindings

    @klid_to_hotkey_bindings.setter
    def klid_to_hotkey_bindings(self, klid_to_hotkey_bindings: dict[str, KeyCombination]):
        for klid, key in klid_to_hotkey_bindings.items():
            if not self._validate_klid_string(klid):
                raise ValueError(f"Invalid klid: {klid}")

            self._klid_to_hotkey_bindings[klid] = key

    @property
    def in_loop_keyboard_layout_ids(self) -> list[str]:
        return self._in_loop_keyboard_layout_ids

    @in_loop_keyboard_layout_ids.setter
    def in_loop_keyboard_layout_ids(self, in_loop_keyboard_layout_ids: list[str]):
        for klid in in_loop_keyboard_layout_ids:
            if not self._validate_klid_string(klid):
                raise ValueError(f"Invalid klid: {klid}")

        self._in_loop_keyboard_layout_ids = in_loop_keyboard_layout_ids

    @property
    def next_layout_in_loop_hotkey(self) -> KeyCombination:
        return self._next_layout_in_loop_hotkey

    @next_layout_in_loop_hotkey.setter
    def next_layout_in_loop_hotkey(self, next_layout_in_loop_hotkey: KeyCombination):
        self._next_layout_in_loop_hotkey = next_layout_in_loop_hotkey

    def _validate_klid_string(self, klid: str) -> bool:
        for registered_layout in self._keyboard_layout_registry.layouts():
            if registered_layout == KeyboardLayout.from_klid(klid):
                return True

        return False
