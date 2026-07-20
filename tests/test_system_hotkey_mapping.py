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


resolve = WindowsKeyboardLayoutSwitchingSettings._resolve_originals


def test_no_backup_takes_current_values():
    assert resolve(("1", "3"), None) == ("1", "3")


def test_disabled_current_with_backup_means_previous_crash():
    # A previous run died before restoring — the backup holds the originals.
    assert resolve(("3", "3"), ("1", "2")) == ("1", "2")


def test_live_current_value_beats_stale_backup():
    # The user reconfigured the system after a crash — current wins.
    assert resolve(("2", "3"), ("1", "1")) == ("2", "1")
