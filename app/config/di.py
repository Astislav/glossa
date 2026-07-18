# Composition root: only swappable seams — {Interface: Implementation}.
from engine.interfaces.keyboard_hook_interface import KeyboardHookInterface
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.interfaces.keyboard_layout_switcher_interface import KeyboardLayoutSwitcherInterface
from engine.interfaces.keyboard_layout_switching_system_settings_interface import \
    KeyboardLayoutSwitchingSystemSettingsInterface
from engine.keyboard_hook import KeyboardHook
from engine.windows.keyboard_layout_registry import WindowsKeyboardLayoutsRegistry
from engine.windows.keyboard_layout_switcher import WindowsKeyboardLayoutSwitcher
from engine.windows.keyboard_layout_switching_settings import WindowsKeyboardLayoutSwitchingSettings

DI_CONFIG = {
    KeyboardLayoutRegistryInterface: WindowsKeyboardLayoutsRegistry,
    KeyboardLayoutSwitcherInterface: WindowsKeyboardLayoutSwitcher,
    KeyboardLayoutSwitchingSystemSettingsInterface: WindowsKeyboardLayoutSwitchingSettings,
    KeyboardHookInterface: KeyboardHook,
}
