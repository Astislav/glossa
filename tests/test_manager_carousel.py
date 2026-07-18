import pytest

from engine.dto.key_combination import KeyCombination
from engine.keyboard_layout_manager import KeyboardLayoutManager
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from tests.conftest import FakeHook, FakeRegistry, FakeSwitcher

EN, RU, GR = "00000409", "00000419", "00000408"


@pytest.fixture
def registry():
    return FakeRegistry([EN, RU, GR])


@pytest.fixture
def setup(registry):
    setup = KeyboardLayoutManagerSetup(registry)
    layouts = {layout.layout_id.to_string: layout.layout_id for layout in registry.layouts()}
    setup.in_loop_keyboard_layout_ids = [layouts[EN], layouts[RU]]
    setup.klid_to_hotkey_bindings = {layouts[GR]: KeyCombination.from_hotkey_string("alt+shift+g")}
    return setup


@pytest.fixture
def switcher():
    return FakeSwitcher()


@pytest.fixture
def hook():
    return FakeHook()


@pytest.fixture
def manager(setup, switcher, hook, test_logger):
    manager = KeyboardLayoutManager(setup, switcher, hook, test_logger)
    manager.start()
    yield manager
    manager.stop()


def fire(manager, hook, hotkey_string):
    """Fire a hotkey and wait for the async switch worker to process it."""
    hook.fire(hotkey_string)
    manager.flush()


def test_start_registers_hotkeys_and_starts_hook(manager, hook):
    assert hook.running
    assert frozenset({"alt", "shift"}) in hook.registrations
    assert frozenset({"alt", "shift", "g"}) in hook.registrations


def test_carousel_advances_in_circle(manager, hook, switcher):
    fire(manager, hook, "alt+shift")
    fire(manager, hook, "alt+shift")
    fire(manager, hook, "alt+shift")
    assert switcher.activated == [RU, EN, RU]


def test_direct_switch_activates_layout(manager, hook, switcher):
    fire(manager, hook, "alt+shift+g")
    assert switcher.activated == [GR]


def test_carousel_returns_to_last_carousel_layout_after_direct_switch(manager, hook, switcher):
    fire(manager, hook, "alt+shift")      # -> RU (last carousel layout)
    fire(manager, hook, "alt+shift+g")    # -> GR (away from carousel)
    fire(manager, hook, "alt+shift")      # back to RU, not EN
    assert switcher.activated == [RU, GR, RU]


def test_carousel_resumes_cycling_after_return(manager, hook, switcher):
    fire(manager, hook, "alt+shift")      # RU
    fire(manager, hook, "alt+shift+g")    # GR
    fire(manager, hook, "alt+shift")      # RU (return)
    fire(manager, hook, "alt+shift")      # EN (normal cycle again)
    assert switcher.activated == [RU, GR, RU, EN]


def test_direct_switch_to_carousel_member_syncs_position(manager, hook, switcher, setup, registry):
    layouts = {layout.layout_id.to_string: layout.layout_id for layout in registry.layouts()}
    setup.klid_to_hotkey_bindings = {
        layouts[GR]: KeyCombination.from_hotkey_string("alt+shift+g"),
        layouts[RU]: KeyCombination.from_hotkey_string("alt+shift+r"),
    }
    manager.reload()

    fire(manager, hook, "alt+shift+r")    # direct to RU, which IS in the carousel
    fire(manager, hook, "alt+shift")      # next after RU -> EN
    assert switcher.activated == [RU, EN]


def test_reload_reregisters_hotkeys(manager, hook, setup, switcher):
    setup.next_layout_in_loop_hotkey = KeyCombination.from_hotkey_string("ctrl+space")
    manager.reload()

    assert frozenset({"ctrl", "space"}) in hook.registrations
    assert frozenset({"alt", "shift"}) not in hook.registrations
    assert hook.running

    fire(manager, hook, "ctrl+space")
    assert switcher.activated == [RU]


def test_stop_stops_hook(manager, hook):
    manager.stop()
    assert not hook.running


def test_empty_carousel_does_not_crash(registry, switcher, hook, test_logger):
    setup = KeyboardLayoutManagerSetup(registry)
    setup.in_loop_keyboard_layout_ids = []
    manager = KeyboardLayoutManager(setup, switcher, hook, test_logger)
    manager.start()

    fire(manager, hook, "alt+shift")
    assert switcher.activated == []
    manager.stop()


def test_switcher_failure_does_not_kill_worker(manager, hook, switcher):
    original_activate = switcher.activate
    switcher.activate = lambda klid: (_ for _ in ()).throw(OSError("boom"))
    fire(manager, hook, "alt+shift")

    switcher.activate = original_activate
    fire(manager, hook, "alt+shift")
    assert switcher.activated == [EN]
