from engine.dto.key_combination import KeyCombination
from engine.dto.keyboard_layout_id import KeyboardLayoutId
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.windows.keyboard_layout_id import WindowsKeyboardLayoutId


class KeyboardLayoutManagerSetup:
    _in_loop_keyboard_layout_ids: list[KeyboardLayoutId] = []
    _next_layout_in_loop_hotkey: KeyCombination = KeyCombination.from_hotkey_string('Alt+Shift')
    _klid_to_hotkey_bindings: dict[KeyboardLayoutId, KeyCombination] = {}
    _keyboard_layout_registry: KeyboardLayoutRegistryInterface

    def __init__(self, keyboard_layout_registry: KeyboardLayoutRegistryInterface):
        self._keyboard_layout_registry = keyboard_layout_registry
        self._in_loop_keyboard_layout_ids = [klid.layout_id for klid in self._keyboard_layout_registry.layouts()]

    def from_string(self, json: dict):
        self.next_layout_in_loop_hotkey = KeyCombination.from_hotkey_string(
            json.get("next_kl_hotkey", 'Alt+Shift')
        )

        for klid_string in json.get("in_loop_kl_ids", []):
            klid = self._klid_from_string(klid_string)
            self.in_loop_keyboard_layout_ids.append(klid)

        for klid_string, hotkey_string in json.get("klid_to_hotkey", {}).items():
            klid = self._klid_from_string(klid_string)
            hotkey = KeyCombination.from_hotkey_string(hotkey_string)
            self.klid_to_hotkey_bindings[klid] = hotkey

    def to_string(self) -> dict:
        return {
            "in_loop_kl_ids": self.in_loop_keyboard_layout_ids,
            "next_kl_hotkey": self.next_layout_in_loop_hotkey.to_hotkey_string(),
            "klid_to_hotkey": self.klid_to_hotkey_bindings
        }

    @property
    def klid_to_hotkey_bindings(self) -> dict[KeyboardLayoutId, KeyCombination]:
        return self._klid_to_hotkey_bindings

    @klid_to_hotkey_bindings.setter
    def klid_to_hotkey_bindings(self, klid_to_hotkey_bindings: dict[KeyboardLayoutId, KeyCombination]):
        for klid, key in klid_to_hotkey_bindings.items():
            if not self._keyboard_layout_registry.layout_exists(klid):
                raise ValueError(f"Invalid klid: {klid}")

            self._klid_to_hotkey_bindings[klid] = key

    @property
    def in_loop_keyboard_layout_ids(self) -> list[KeyboardLayoutId]:
        return self._in_loop_keyboard_layout_ids

    @in_loop_keyboard_layout_ids.setter
    def in_loop_keyboard_layout_ids(self, in_loop_keyboard_layout_ids: list[KeyboardLayoutId]):
        for klid in in_loop_keyboard_layout_ids:
            if not self._keyboard_layout_registry.layout_exists(klid):
                raise ValueError(f"Invalid klid: {klid}")

        self._in_loop_keyboard_layout_ids = in_loop_keyboard_layout_ids

    @property
    def next_layout_in_loop_hotkey(self) -> KeyCombination:
        return self._next_layout_in_loop_hotkey

    @next_layout_in_loop_hotkey.setter
    def next_layout_in_loop_hotkey(self, next_layout_in_loop_hotkey: KeyCombination):
        self._next_layout_in_loop_hotkey = next_layout_in_loop_hotkey

    # noinspection PyMethodMayBeStatic
    def _klid_from_string(self, klid_string: str) -> KeyboardLayoutId:
        try:
            klid = WindowsKeyboardLayoutId(klid_string)

            return klid
        except ValueError:
            raise ValueError(f"Invalid klid: {klid_string}")
