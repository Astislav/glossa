import json

import pytest

from engine.dto.key_combination import KeyCombination
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from tests.conftest import FakeKeyboardLayoutId, FakeRegistry

EN, RU = "00000409", "00000419"


@pytest.fixture
def registry():
    return FakeRegistry([EN, RU])


@pytest.fixture
def setup(registry):
    return KeyboardLayoutManagerSetup(registry)


def test_defaults_include_all_layouts_in_loop(setup):
    assert [klid.to_string for klid in setup.in_loop_keyboard_layout_ids] == [EN, RU]
    assert setup.next_layout_in_loop_hotkey.as_frozenset() == frozenset({"alt", "shift"})


def test_serialization_round_trip(setup, registry):
    layouts = {layout.layout_id.to_string: layout.layout_id for layout in registry.layouts()}
    setup.klid_to_hotkey_bindings = {layouts[RU]: KeyCombination.from_hotkey_string("alt+shift+r")}

    serialized = setup.to_string()
    parsed = json.loads(serialized)
    assert parsed["in_loop_kl_ids"] == [EN, RU]
    assert parsed["kl_id_to_hotkey"] == {RU: "alt+shift+r"}

    restored = KeyboardLayoutManagerSetup(registry)
    restored.from_string(parsed)
    assert restored.to_string() == serialized


def test_bindings_are_replaced_not_merged(setup, registry):
    layouts = {layout.layout_id.to_string: layout.layout_id for layout in registry.layouts()}
    setup.klid_to_hotkey_bindings = {layouts[RU]: KeyCombination.from_hotkey_string("alt+shift+r")}
    setup.klid_to_hotkey_bindings = {layouts[EN]: KeyCombination.from_hotkey_string("alt+shift+e")}

    assert list(setup.klid_to_hotkey_bindings) == [layouts[EN]]


def test_unknown_layout_in_loop_is_rejected(setup):
    with pytest.raises(ValueError):
        setup.in_loop_keyboard_layout_ids = [FakeKeyboardLayoutId("DEADBEEF")]


def test_unknown_layout_in_bindings_is_rejected(setup):
    with pytest.raises(ValueError):
        setup.klid_to_hotkey_bindings = {
            FakeKeyboardLayoutId("DEADBEEF"): KeyCombination.from_hotkey_string("alt+x")
        }


STALE = "00000404"  # a valid KLID format, but not installed in the test registry


def test_stale_klid_in_carousel_is_dropped(setup):
    dropped = setup.from_string({"in_loop_kl_ids": [EN, STALE, RU]})

    assert dropped == [STALE]
    assert [klid.to_string for klid in setup.in_loop_keyboard_layout_ids] == [EN, RU]


def test_stale_klid_in_bindings_is_dropped(setup):
    dropped = setup.from_string({
        "in_loop_kl_ids": [EN, RU],
        "kl_id_to_hotkey": {EN: "alt+shift+e", STALE: "alt+shift+g"},
    })

    assert dropped == [STALE]
    assert [klid.to_string for klid in setup.klid_to_hotkey_bindings] == [EN]


def test_malformed_klid_is_dropped_not_fatal(setup):
    # A corrupt or hand-edited entry must not brick startup.
    dropped = setup.from_string({"in_loop_kl_ids": [EN, "not-a-klid"]})

    assert dropped == ["not-a-klid"]
    assert [klid.to_string for klid in setup.in_loop_keyboard_layout_ids] == [EN]


def test_carousel_falls_back_to_default_when_all_layouts_are_stale(setup):
    # Every saved layout is gone — keep the default (all installed) instead
    # of an empty, useless carousel.
    dropped = setup.from_string({"in_loop_kl_ids": [STALE]})

    assert dropped == [STALE]
    assert [klid.to_string for klid in setup.in_loop_keyboard_layout_ids] == [EN, RU]
