from abc import ABC, abstractmethod

from engine.dto.keyboard_layout import KeyboardLayout
from engine.dto.keyboard_layout_id import KeyboardLayoutId


class KeyboardLayoutRegistryInterface(ABC):
    @abstractmethod
    def layouts(self) -> list[KeyboardLayout]:
        pass

    @abstractmethod
    def layout_exists(self, keyboard_layout_id: KeyboardLayoutId) -> bool:
        pass
