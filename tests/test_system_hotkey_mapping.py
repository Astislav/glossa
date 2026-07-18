from engine.windows.keyboard_layout_switching_settings import WindowsKeyboardLayoutSwitchingSettings

map_value = WindowsKeyboardLayoutSwitchingSettings._hotkey_from_toggle_value


def test_alt_shift():
    assert map_value("1").as_frozenset() == frozenset({"alt", "shift"})


def test_ctrl_shift():
    assert map_value("2").as_frozenset() == frozenset({"ctrl", "shift"})


def test_disabled_and_unknown_values_give_none():
    assert map_value("3") is None
    assert map_value("4") is None
    assert map_value(None) is None
