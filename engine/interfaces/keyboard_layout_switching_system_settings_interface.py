from abc import ABC, abstractmethod


class KeyboardLayoutSwitchingSystemSettingsInterface(ABC):
    @abstractmethod
    def disable_system_hotkeys(self):
        pass

    @abstractmethod
    def restore_system_hotkeys(self):
        pass
