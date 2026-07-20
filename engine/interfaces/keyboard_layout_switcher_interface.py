from abc import ABC, abstractmethod

from engine.dto.keyboard_layout_id import KeyboardLayoutId


class KeyboardLayoutSwitcherInterface(ABC):
    @abstractmethod
    def activate(self, keyboard_layout_id: KeyboardLayoutId):
        pass

    @abstractmethod
    def active_layout_langid(self) -> int | None:
        """Language id (low word of the active layout handle) of the
        foreground window's current layout, or None if unavailable — lets
        the carousel sync with what the user actually sees instead of
        trusting its own bookkeeping."""
        pass
