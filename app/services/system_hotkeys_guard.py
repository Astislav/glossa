from injector import inject, singleton

from nexus_kit.interfaces import ServiceInterface

from app.loggers import SystemHotkeysGuardLogger
from engine.interfaces.keyboard_layout_switching_system_settings_interface import \
    KeyboardLayoutSwitchingSystemSettingsInterface


@singleton
class SystemHotkeysGuard(ServiceInterface):
    """Disables the Windows built-in layout-switch hotkeys for the app's
    lifetime. ServiceRunner guarantees stop() on any exit, so the system
    hotkeys are restored even when the app crashes."""

    @inject
    def __init__(
            self,
            system_settings: KeyboardLayoutSwitchingSystemSettingsInterface,
            log: SystemHotkeysGuardLogger,
    ):
        self._system_settings = system_settings
        self._log = log
        self._disabled = False

    def start(self):
        self._system_settings.disable_system_hotkeys()
        self._disabled = True
        self._log.info("system layout hotkeys disabled")

    def stop(self):
        if not self._disabled:
            return

        self._system_settings.restore_system_hotkeys()
        self._disabled = False
        self._log.info("system layout hotkeys restored")
