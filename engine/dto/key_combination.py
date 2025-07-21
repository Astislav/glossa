class KeyCombination:
    def __init__(self, keys: frozenset[str]):
        self._keys = keys

    @classmethod
    def from_hotkey_string(cls, string: str) -> "KeyCombination":
        keys = frozenset(k.strip().lower() for k in string.split("+"))

        return cls(keys)

    def to_hotkey_string(self) -> str:
        return "+".join(self._keys)

    def as_frozenset(self) -> frozenset[str]:
        return self._keys
