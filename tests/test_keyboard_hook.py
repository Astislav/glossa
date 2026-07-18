from types import SimpleNamespace

import pytest

from engine.dto.key_combination import KeyCombination
from engine.keyboard_hook import KeyboardHook


@pytest.fixture
def hook(test_logger):
    return KeyboardHook(test_logger)


def down(hook, key):
    hook._handler(SimpleNamespace(name=key, event_type="down"))


def up(hook, key):
    hook._handler(SimpleNamespace(name=key, event_type="up"))


def tap(hook, *keys):
    for key in keys:
        down(hook, key)
    for key in reversed(keys):
        up(hook, key)


@pytest.fixture
def fired():
    return []


@pytest.fixture
def conflicting_hook(hook, fired):
    """Carousel Alt+Shift + direct Alt+Shift+G — the user's target setup."""
    hook.register_hook(KeyCombination.from_hotkey_string("alt+shift"), fired.append, "carousel")
    hook.register_hook(KeyCombination.from_hotkey_string("alt+shift+g"), fired.append, "greek")
    return hook


def test_prefix_combo_fires_once_on_release(conflicting_hook, fired):
    tap(conflicting_hook, "alt", "shift")
    assert fired == ["carousel"]


def test_prefix_combo_does_not_fire_before_release(conflicting_hook, fired):
    down(conflicting_hook, "alt")
    down(conflicting_hook, "shift")
    assert fired == []


def test_superset_fires_on_press_and_suppresses_prefix(conflicting_hook, fired):
    tap(conflicting_hook, "alt", "shift", "g")
    assert fired == ["greek"]


def test_superset_fires_immediately_on_last_key_down(conflicting_hook, fired):
    down(conflicting_hook, "alt")
    down(conflicting_hook, "shift")
    down(conflicting_hook, "g")
    assert fired == ["greek"]


def test_double_tap_of_extra_key_fires_superset_twice(conflicting_hook, fired):
    down(conflicting_hook, "alt")
    down(conflicting_hook, "shift")
    tap(conflicting_hook, "g")
    tap(conflicting_hook, "g")
    up(conflicting_hook, "shift")
    up(conflicting_hook, "alt")
    assert fired == ["greek", "greek"]


def test_combo_without_conflicts_fires_on_press(hook, fired):
    hook.register_hook(KeyCombination.from_hotkey_string("alt+shift"), fired.append, "carousel")
    down(hook, "alt")
    down(hook, "shift")
    assert fired == ["carousel"]


def test_independent_combo_fires_on_press(conflicting_hook, fired):
    conflicting_hook.register_hook(KeyCombination.from_hotkey_string("ctrl+alt+x"), fired.append, "other")
    down(conflicting_hook, "ctrl")
    down(conflicting_hook, "alt")
    down(conflicting_hook, "x")
    assert fired == ["other"]


def test_autorepeat_does_not_refire(hook, fired):
    hook.register_hook(KeyCombination.from_hotkey_string("ctrl+k"), fired.append, "combo")
    down(hook, "ctrl")
    down(hook, "k")
    down(hook, "k")  # OS autorepeat
    down(hook, "k")
    assert fired == ["combo"]


def test_autorepeat_does_not_refire_armed_combo(conflicting_hook, fired):
    down(conflicting_hook, "alt")
    down(conflicting_hook, "shift")
    down(conflicting_hook, "shift")  # OS autorepeat while armed
    up(conflicting_hook, "shift")
    up(conflicting_hook, "alt")
    assert fired == ["carousel"]


def test_repeated_taps_fire_each_time(conflicting_hook, fired):
    tap(conflicting_hook, "alt", "shift")
    tap(conflicting_hook, "alt", "shift")
    tap(conflicting_hook, "alt", "shift", "g")
    assert fired == ["carousel", "carousel", "greek"]


def test_left_right_modifier_names_are_normalized(conflicting_hook, fired):
    down(conflicting_hook, "left alt")
    down(conflicting_hook, "right shift")
    up(conflicting_hook, "right shift")
    up(conflicting_hook, "left alt")
    assert fired == ["carousel"]


def test_unregister_all_clears_hotkeys(conflicting_hook, fired):
    conflicting_hook.unregister_all()
    tap(conflicting_hook, "alt", "shift")
    assert fired == []


def test_callback_exception_does_not_break_hook(hook, fired):
    def broken():
        raise RuntimeError("boom")

    hook.register_hook(KeyCombination.from_hotkey_string("ctrl+b"), broken)
    hook.register_hook(KeyCombination.from_hotkey_string("ctrl+k"), fired.append, "combo")

    tap(hook, "ctrl", "b")
    tap(hook, "ctrl", "k")
    assert fired == ["combo"]
