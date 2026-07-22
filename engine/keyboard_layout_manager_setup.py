import json

from injector import inject, singleton

from engine.dto.key_combination import KeyCombination
from engine.dto.keyboard_layout_id import KeyboardLayoutId
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.windows.keyboard_layout_id import WindowsKeyboardLayoutId


@singleton
class KeyboardLayoutManagerSetup:
    @inject
    def __init__(self, keyboard_layout_registry: KeyboardLayoutRegistryInterface):
        self._keyboard_layout_registry = keyboard_layout_registry
        self._in_loop_keyboard_layout_ids: list[KeyboardLayoutId] = \
            [klid.layout_id for klid in self._keyboard_layout_registry.layouts()]
        self._next_layout_in_loop_hotkey: KeyCombination = KeyCombination.from_hotkey_string('Alt+Shift')
        self._klid_to_hotkey_bindings: dict[KeyboardLayoutId, KeyCombination] = {}

    def from_string(self, json: dict) -> list[str]:
        """Load persisted settings, tolerantly. Layouts the user has since
        removed from Windows (or a malformed/hand-edited entry) are skipped
        rather than raising — a stale settings file must never brick startup.
        Returns the klid strings that were dropped, so the caller can warn
        and rewrite the cleaned file.
        """
        dropped: list[str] = []

        self.next_layout_in_loop_hotkey = KeyCombination.from_hotkey_string(
            json.get("next_kl_hotkey", 'Alt+Shift')
        )

        klids: list[KeyboardLayoutId] = []
        for klid_string in json.get("in_loop_kl_ids", []):
            klid = self._installed_klid_or_none(klid_string)
            if klid is None:
                dropped.append(klid_string)
            else:
                klids.append(klid)
        # An empty carousel is useless — keep the default (all installed) if
        # every saved layout is gone.
        if klids:
            self.in_loop_keyboard_layout_ids = klids

        bindings: dict[KeyboardLayoutId, KeyCombination] = {}
        for klid_string, hotkey_string in json.get("kl_id_to_hotkey", {}).items():
            klid = self._installed_klid_or_none(klid_string)
            if klid is None:
                dropped.append(klid_string)
            else:
                bindings[klid] = KeyCombination.from_hotkey_string(hotkey_string)
        self.klid_to_hotkey_bindings = bindings

        return dropped

    def to_string(self) -> str:
        return json.dumps(
            {
                "in_loop_kl_ids": [klid.to_string for klid in self.in_loop_keyboard_layout_ids],
                "next_kl_hotkey": self.next_layout_in_loop_hotkey.to_hotkey_string(),
                "kl_id_to_hotkey": {
                    klid.to_string: hotkey.to_hotkey_string()
                    for klid, hotkey in self.klid_to_hotkey_bindings.items()
                }
            },
            indent=2
        )

    @property
    def klid_to_hotkey_bindings(self) -> dict[KeyboardLayoutId, KeyCombination]:
        return self._klid_to_hotkey_bindings

    @klid_to_hotkey_bindings.setter
    def klid_to_hotkey_bindings(self, klid_to_hotkey_bindings: dict[KeyboardLayoutId, KeyCombination]):
        for klid in klid_to_hotkey_bindings:
            if not self._keyboard_layout_registry.layout_exists(klid):
                raise ValueError(f"Invalid klid: {klid}")

        # Full replacement, not a merge — a binding removed in the UI must
        # actually disappear.
        self._klid_to_hotkey_bindings = dict(klid_to_hotkey_bindings)

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

    def _installed_klid_or_none(self, klid_string: str) -> KeyboardLayoutId | None:
        """Parse a saved klid string, returning None if it is malformed or
        no longer installed in the system."""
        try:
            klid = WindowsKeyboardLayoutId(klid_string)
        except ValueError:
            return None

        return klid if self._keyboard_layout_registry.layout_exists(klid) else None
