import json
import time
from pathlib import Path

from engine.keyboard_hook import KeyboardHook
from engine.keyboard_layout_manager import KeyboardLayoutManager
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from engine.windows.keyboard_layout_registry import WindowsKeyboardLayoutsRegistry
from engine.windows.keyboard_layout_switcher import WindowsKeyboardLayoutSwitcher
from engine.windows.keyboard_layout_switching_settings import WindowsKeyboardLayoutSwitchingSettings

SETTINGS_FILE = Path("settings\\settings.json")

if __name__ == "__main__":
    settings = WindowsKeyboardLayoutSwitchingSettings()
    registry = WindowsKeyboardLayoutsRegistry()
    layout_switcher = WindowsKeyboardLayoutSwitcher(registry)
    setup = KeyboardLayoutManagerSetup(registry)

    if SETTINGS_FILE.exists():
        setup.from_string(json.loads(SETTINGS_FILE.read_text()))
    else:
        SETTINGS_FILE.write_text(json.dumps(setup.to_string(), indent=2))

    hook = KeyboardHook()

    manager = KeyboardLayoutManager(setup, settings, layout_switcher, hook)
    manager.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    manager.stop()
    manager.join(timeout=2.0)
