from abc import ABC, abstractmethod

from engine.dto.key_combination import KeyCombination


class KeyboardLayoutSwitchingSystemSettingsInterface(ABC):
    @abstractmethod
    def disable_system_hotkeys(self):
        pass

    @abstractmethod
    def restore_system_hotkeys(self):
        pass

    @abstractmethod
    def recover_if_needed(self):
        """Restore the OS hotkeys at startup if a prior run left them disabled."""
        pass

    @abstractmethod
    def system_switch_hotkey(self) -> KeyCombination | None:
        """The layout-switch hotkey currently configured in the OS, if any —
        lets the app inherit the user's existing habit on first run."""
        pass
