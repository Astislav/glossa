from engine.dto.keyboard_layout_id import KeyboardLayoutId


class KeyboardLayout:
    def __init__(self, keyboard_layout_name: str, keyboard_layout_id: KeyboardLayoutId):
        self._layout_name = keyboard_layout_name
        self._layout_id = keyboard_layout_id

    @classmethod
    def from_klid(cls, klid: KeyboardLayoutId):
        return cls(klid.to_string, klid)

    @property
    def layout_name(self) -> str:
        return self._layout_name

    @property
    def layout_id(self) -> KeyboardLayoutId:
        return self._layout_id

    def __repr__(self):
        return f"{self._layout_name} ({self._layout_id})"

    def __eq__(self, other: "KeyboardLayout"):
        return self._layout_id == other._layout_id
