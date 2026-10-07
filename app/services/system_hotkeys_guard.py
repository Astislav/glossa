from injector import inject, singleton

from nexus_kit.interfaces import ServiceInterface

from app.loggers import SystemHotkeysGuardLogger
from engine.interfaces.keyboard_layout_switching_system_settings_interface import \
    KeyboardLayoutSwitchingSystemSettingsInterface
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


@singleton
class SystemHotkeysGuard(ServiceInterface):
    """Owns the takeover of the Windows built-in layout-switch hotkeys.

    Lifecycle: start() only recovers a safe state (restores the OS hotkeys if
    a prior run left them disabled) — it does NOT take over yet, so native
    switching keeps working while the app waits for the keyboard subsystem.
    activate() is the actual takeover (disable), called once the system is
    ready. stop() restores on exit — via ServiceRunner teardown on a clean
    quit and via the session-end handler on Windows shutdown. A hard kill
    can't restore in the moment, but the originals are backed up to disk and
    the next start() recovers them."""

    @inject
    def __init__(
            self,
            system_settings: KeyboardLayoutSwitchingSystemSettingsInterface,
            setup: KeyboardLayoutManagerSetup,
            log: SystemHotkeysGuardLogger,
    ):
        self._system_settings = system_settings
        self._setup = setup
        self._log = log
        self._active = False

    def start(self):
        # Passive: don't take over yet — just make sure the OS is in its
        # normal state (recover from a prior unclean exit if needed).
        self._system_settings.recover_if_needed()

    def activate(self):
        if self._active:
            return  # already taken over

        # Take over — but only if we actually have a carousel to drive. An
        # empty carousel must never disable the system's own switching.
        if not self._setup.in_loop_keyboard_layout_ids:
            self._log.warning("carousel is empty — leaving the system layout hotkeys enabled")
            return

        self._system_settings.disable_system_hotkeys()
        self._active = True
        self._log.info("system layout hotkeys disabled")

    def stop(self):
        if not self._active:
            return

        self._system_settings.restore_system_hotkeys()
        self._active = False
        self._log.info("system layout hotkeys restored")
