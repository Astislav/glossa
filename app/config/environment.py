from pathlib import Path

from injector import singleton

from nexus_kit.interfaces import EnvironmentInterface


@singleton
class Environment(EnvironmentInterface):
    APP_NAME: str = "Glossa"
    SETTINGS_FILE: str = "settings/settings.json"

    def __init__(self, env_path: Path | str) -> None:
        super().__init__(_env_file=env_path)
