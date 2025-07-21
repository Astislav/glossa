from abc import ABC, abstractmethod


class KeyboardLayoutSwitcherInterface(ABC):
    @abstractmethod
    def activate(self, keyboard_layout_id: str):
        pass
