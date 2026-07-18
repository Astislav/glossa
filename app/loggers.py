from injector import singleton

from nexus_kit.logging import NamedLogger


@singleton
class SettingsStoreLogger(NamedLogger):
    name = "ls.settings"


@singleton
class SystemHotkeysGuardLogger(NamedLogger):
    name = "ls.hotkeys-guard"
