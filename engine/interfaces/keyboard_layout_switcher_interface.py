from abc import ABC, abstractmethod

from engine.dto.keyboard_layout_id import KeyboardLayoutId


class KeyboardLayoutSwitcherInterface(ABC):
    @abstractmethod
    def activate(self, keyboard_layout_id: KeyboardLayoutId):
        pass
