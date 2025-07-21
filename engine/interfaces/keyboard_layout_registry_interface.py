from abc import ABC, abstractmethod

from engine.dto.keyboard_layout import KeyboardLayout


class KeyboardLayoutRegistryInterface(ABC):
    @abstractmethod
    def layouts(self) -> list[KeyboardLayout]:
        pass

    @abstractmethod
    def layout_exists(self, keyboard_layout_id: str) -> bool:
        pass
