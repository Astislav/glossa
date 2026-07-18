import json
from pathlib import Path

from injector import inject, singleton

from nexus_kit import Root
from nexus_kit.interfaces import ServiceInterface

from app.config.environment import Environment
from app.loggers import SettingsStoreLogger
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


@singleton
class SettingsStore(ServiceInterface):
    @inject
    def __init__(
            self,
            environment: Environment,
            keyboard_layout_manager_setup: KeyboardLayoutManagerSetup,
            log: SettingsStoreLogger,
    ):
        self._settings_path = Path(Root.external(environment.SETTINGS_FILE))
        self._kl_manager_setup = keyboard_layout_manager_setup
        self._log = log

    def start(self):
        if self._settings_path.exists():
            self._kl_manager_setup.from_string(json.loads(self._settings_path.read_text(encoding="utf-8")))
            self._log.info("settings loaded from %s", self._settings_path)
        else:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            self._settings_path.write_text(self._kl_manager_setup.to_string(), encoding="utf-8")
            self._log.info("default settings written to %s", self._settings_path)

    def stop(self):
        pass
