import json
from pathlib import Path

from injector import inject, singleton

from nexus_kit import Root
from nexus_kit.interfaces import ServiceInterface

from app.config.environment import Environment
from app.loggers import SettingsStoreLogger
from engine.interfaces.keyboard_layout_switching_system_settings_interface import \
    KeyboardLayoutSwitchingSystemSettingsInterface
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


@singleton
class SettingsStore(ServiceInterface):
    @inject
    def __init__(
            self,
            environment: Environment,
            keyboard_layout_manager_setup: KeyboardLayoutManagerSetup,
            system_settings: KeyboardLayoutSwitchingSystemSettingsInterface,
            log: SettingsStoreLogger,
    ):
        self._settings_path = Path(Root.external(environment.SETTINGS_FILE))
        self._kl_manager_setup = keyboard_layout_manager_setup
        self._system_settings = system_settings
        self._log = log

    def start(self):
        if self._settings_path.exists():
            self._kl_manager_setup.from_string(json.loads(self._settings_path.read_text(encoding="utf-8")))
            self._log.info("settings loaded from %s", self._settings_path)
        else:
            # First run: inherit the user's existing system hotkey (Alt+Shift,
            # Ctrl+Shift, …) so their habit keeps working out of the box.
            system_hotkey = self._system_settings.system_switch_hotkey()
            if system_hotkey is not None:
                self._kl_manager_setup.next_layout_in_loop_hotkey = system_hotkey
                self._log.info("carousel hotkey inherited from system: %s", system_hotkey.to_hotkey_string())
            self.save()
            self._log.info("default settings written to %s", self._settings_path)

    def stop(self):
        pass

    def save(self):
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(self._kl_manager_setup.to_string(), encoding="utf-8")
        self._log.info("settings saved to %s", self._settings_path)
