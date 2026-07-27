"""Cold-boot flow: start passive (native switching intact), wait for the OS
to be ready, then take over. Nothing blocks and nothing gives up."""
import pytest

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.readiness_controller import ReadinessController
from app.services.system_hotkeys_guard import SystemHotkeysGuard
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from tests.conftest import FakeRegistry

EN, RU = "00000409", "00000419"


class SilentLogger:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass
    def error(self, *a, **k): pass


# --- SystemHotkeysGuard: passive start, deferred takeover ---

class RecordingSystemSettings:
    def __init__(self):
        self.recovered = False
        self.disabled = False
        self.restored = False

    def recover_if_needed(self):
        self.recovered = True

    def disable_system_hotkeys(self):
        self.disabled = True

    def restore_system_hotkeys(self):
        self.restored = True


def make_guard(setup, system):
    guard = SystemHotkeysGuard.__new__(SystemHotkeysGuard)
    guard._system_settings = system
    guard._setup = setup
    guard._log = SilentLogger()
    guard._active = False
    return guard


def test_start_recovers_but_does_not_take_over():
    system = RecordingSystemSettings()
    guard = make_guard(KeyboardLayoutManagerSetup(FakeRegistry([EN, RU])), system)

    guard.start()
    assert system.recovered      # safe state recovered
    assert not system.disabled   # but native switching left intact


def test_activate_takes_over_when_carousel_has_layouts():
    system = RecordingSystemSettings()
    guard = make_guard(KeyboardLayoutManagerSetup(FakeRegistry([EN, RU])), system)

    guard.start()
    guard.activate()
    assert system.disabled

    guard.stop()
    assert system.restored


def test_activate_leaves_system_alone_when_carousel_empty():
    system = RecordingSystemSettings()
    guard = make_guard(KeyboardLayoutManagerSetup(FakeRegistry([])), system)

    guard.start()
    guard.activate()
    assert not system.disabled

    guard.stop()
    assert not system.restored


# --- ReadinessController: non-blocking poll, no timeout ---

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class DelayedRegistry(FakeRegistry):
    def __init__(self, klid_strings, empty_calls):
        super().__init__(klid_strings)
        self._empty_calls = empty_calls
        self._calls = 0

    def layouts(self):
        self._calls += 1
        return [] if self._calls <= self._empty_calls else super().layouts()


def test_activates_immediately_when_registry_ready(qapp):
    calls = []
    controller = ReadinessController(FakeRegistry([EN, RU]), lambda waited: calls.append(waited))

    controller.start()
    assert calls == [False]  # ready at once — no wait, no toast


def test_waits_then_activates_exactly_once(qapp):
    calls = []
    controller = ReadinessController(DelayedRegistry([EN, RU], empty_calls=2), lambda waited: calls.append(waited))
    controller._timer.setInterval(5)

    controller.start()
    assert calls == []  # not ready yet — stays passive

    QTest.qWait(60)
    assert calls == [True]  # activated once, having waited (cold boot)
