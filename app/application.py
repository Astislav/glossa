import sys

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from nexus_kit import Root
from nexus_kit.impl import ServiceRunner
from nexus_kit.interfaces import ApplicationInterface, ContainerInterface

from app.config.environment import Environment
from app.services.settings_store import SettingsStore
from app.services.system_hotkeys_guard import SystemHotkeysGuard
from app.ui.settings_window import SettingsWindow
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.keyboard_layout_manager import KeyboardLayoutManager


class Application(ApplicationInterface):
    SERVICES = [SettingsStore, SystemHotkeysGuard, KeyboardLayoutManager]  # startup order; stopped in reverse

    def __init__(self, environment: Environment, container: ContainerInterface):
        self._env = environment
        self._container = container

    def run(self):
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # tray app: closing a window must not quit

        settings_window = SettingsWindow(self._container.get(KeyboardLayoutRegistryInterface))

        tray_icon = QSystemTrayIcon(QIcon(Root.external("resources", "icon.ico")), parent=app)
        tray_menu = QMenu()

        action_settings = QAction("Настройки", triggered=settings_window.show)
        action_quit = QAction("Выход", triggered=app.quit)

        tray_menu.addAction(action_settings)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)

        tray_icon.setContextMenu(tray_menu)
        tray_icon.show()

        with ServiceRunner(self._container, self.SERVICES):
            app.exec()
