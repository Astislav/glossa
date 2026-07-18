import sys

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from nexus_kit import Root
from nexus_kit.impl import ServiceRunner
from nexus_kit.interfaces import ApplicationInterface, ContainerInterface

from app.config.environment import Environment
from app.services.autostart import Autostart
from app.services.settings_store import SettingsStore
from app.services.system_hotkeys_guard import SystemHotkeysGuard
from app.ui.settings_window import SettingsWindow
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.keyboard_layout_manager import KeyboardLayoutManager
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


class Application(ApplicationInterface):
    SERVICES = [SettingsStore, SystemHotkeysGuard, KeyboardLayoutManager]  # startup order; stopped in reverse

    def __init__(self, environment: Environment, container: ContainerInterface):
        self._env = environment
        self._container = container

    def run(self):
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # tray app: closing a window must not quit

        settings_window = SettingsWindow(
            registry=self._container.get(KeyboardLayoutRegistryInterface),
            setup=self._container.get(KeyboardLayoutManagerSetup),
            settings_store=self._container.get(SettingsStore),
            manager=self._container.get(KeyboardLayoutManager),
            autostart=self._container.get(Autostart),
        )

        def show_settings():
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()

        # internal: the icon ships inside the bundle — a bare downloaded exe
        # works without a resources/ folder next to it.
        icon = QIcon(Root.internal("resources", "icon.ico"))
        app.setWindowIcon(icon)

        tray_icon = QSystemTrayIcon(icon, parent=app)
        tray_icon.setToolTip(self._env.APP_NAME)
        tray_menu = QMenu()

        action_settings = QAction("Settings", triggered=show_settings)
        action_quit = QAction("Quit", triggered=app.quit)

        tray_menu.addAction(action_settings)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)

        tray_icon.setContextMenu(tray_menu)
        tray_icon.activated.connect(
            lambda reason: show_settings() if reason in (
                QSystemTrayIcon.ActivationReason.Trigger,        # left click
                QSystemTrayIcon.ActivationReason.DoubleClick,
            ) else None
        )
        settings_window.settings_applied.connect(
            lambda: tray_icon.showMessage(self._env.APP_NAME, "Settings applied")
        )
        tray_icon.show()

        with ServiceRunner(self._container, self.SERVICES):
            app.exec()
