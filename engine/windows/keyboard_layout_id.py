import re

from engine.dto.keyboard_layout_id import KeyboardLayoutId

_KLID_RE = re.compile(r'^[0-9A-F]{8}$', re.IGNORECASE)


class WindowsKeyboardLayoutId(KeyboardLayoutId):
    def __init__(self, layout_id: str):
        if not _KLID_RE.match(layout_id):
            raise ValueError(f"Invalid klid: {layout_id}")

        self._layout_id = layout_id

    @property
    def to_string(self) -> str:
        return self._layout_id[-8:].upper().rjust(8, "0")
