import json
from pathlib import Path

from injector import inject, singleton

from nexus_kit import Root
from nexus_kit.interfaces import ServiceInterface

from app.config.environment import Environment
from app.loggers import SettingsStoreLogger
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
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
            registry: KeyboardLayoutRegistryInterface,
            system_settings: KeyboardLayoutSwitchingSystemSettingsInterface,
            log: SettingsStoreLogger,
    ):
        self._settings_path = Path(Root.external(environment.SETTINGS_FILE))
        self._kl_manager_setup = keyboard_layout_manager_setup
        self._registry = registry
        self._system_settings = system_settings
        self._log = log

    def start(self):
        pass

    def load(self):
        """Load settings into the setup. Called once the keyboard subsystem is
        ready, so the registry is reliable here."""
        if self._settings_path.exists():
            self._load_or_reset()
        else:
            self._write_first_run_defaults()

    def _load_or_reset(self):
        if not self._registry.layouts():
            # The keyboard subsystem isn't ready (cold boot). Validating the
            # saved layouts against an empty registry would drop them all and
            # self-heal them away — destroying the file. Leave it untouched;
            # a restart (or the readiness gate) loads it correctly.
            self._log.warning("keyboard layouts unavailable — skipping settings load to avoid data loss")
            return

        try:
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            dropped = self._kl_manager_setup.from_string(data)
        except Exception:
            # Corrupt or unreadable settings must not brick startup — fall
            # back to defaults and overwrite the bad file.
            self._log.exception("could not load settings from %s — resetting to defaults", self._settings_path)
            self.save()
            return

        self._log.info("settings loaded from %s", self._settings_path)
        if dropped:
            # Layouts the user removed from Windows — self-heal the file so
            # the warning doesn't repeat on every launch.
            self._log.warning("dropped layouts no longer installed: %s", ", ".join(dict.fromkeys(dropped)))
            self.save()

    def _write_first_run_defaults(self):
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
