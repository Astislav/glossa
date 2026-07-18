class KeyCombination:
    _MODIFIER_ORDER = ("ctrl", "alt", "shift", "windows")

    def __init__(self, keys: frozenset[str]):
        self._keys = keys

    @classmethod
    def from_hotkey_string(cls, string: str) -> "KeyCombination":
        keys = frozenset(k.strip().lower() for k in string.split("+"))

        return cls(keys)

    def to_hotkey_string(self) -> str:
        # Canonical order: modifiers first, then the remaining keys sorted —
        # stable output for the settings file and the UI.
        modifiers = [k for k in self._MODIFIER_ORDER if k in self._keys]
        others = sorted(self._keys - set(self._MODIFIER_ORDER))

        return "+".join(modifiers + others)

    def as_frozenset(self) -> frozenset[str]:
        return self._keys
