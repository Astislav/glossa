"""Session-end handlers on the Application: give the hotkeys back when the
session ends; take them back if the shutdown is cancelled — but only if the
app had taken over in the first place."""
from nexus_kit import Root
from nexus_kit.impl import ContainerInjector

from app.application import Application
from app.config.di import DI_CONFIG
from app.config.environment import Environment
from app.services.system_hotkeys_guard import SystemHotkeysGuard


class FakeGuard:
    def __init__(self):
        self.stop_calls = 0
        self.activate_calls = 0

    def stop(self):
        self.stop_calls += 1

    def activate(self):
        self.activate_calls += 1


def _application_with_fake_guard():
    env = Environment(Root.external(".env"))
    container = ContainerInjector(DI_CONFIG)
    container.set(Environment, env)
    fake_guard = FakeGuard()
    container.set(SystemHotkeysGuard, fake_guard)
    return Application(env, container), fake_guard


def test_session_end_restores_system_hotkeys():
    app, fake_guard = _application_with_fake_guard()
    app._on_session_end()
    assert fake_guard.stop_calls == 1


def test_cancelled_shutdown_retakes_hotkeys_after_activation():
    app, fake_guard = _application_with_fake_guard()
    app._activated = True
    app._on_session_resumed()
    assert fake_guard.activate_calls == 1


def test_cancelled_shutdown_before_activation_does_nothing():
    # Still waiting for the OS — nothing to take back.
    app, fake_guard = _application_with_fake_guard()
    app._on_session_resumed()
    assert fake_guard.activate_calls == 0
