from abc import ABC, abstractmethod

from engine.dto.key_combination import KeyCombination


class KeyboardHookInterface(ABC):
    @abstractmethod
    def register_hook(self, key_combination: KeyCombination, callback: callable, *args):
        pass

    @abstractmethod
    def unregister_all(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
