"""SettingsStore must survive a settings.json that references layouts the
user has since removed (the reported ValueError: Invalid klid crash) and a
corrupt file — never bricking startup."""
import json

import pytest

from app.services.settings_store import SettingsStore
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup
from tests.conftest import FakeRegistry

EN, RU = "00000409", "00000419"
STALE = "00000404"


class FakeSystemSettings:
    def system_switch_hotkey(self):
        return None


class SilentLogger:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass
    def exception(self, *a, **k): pass


def make_store(tmp_path, settings_text=None):
    registry = FakeRegistry([EN, RU])
    setup = KeyboardLayoutManagerSetup(registry)
    settings_path = tmp_path / "settings.json"
    if settings_text is not None:
        settings_path.write_text(settings_text, encoding="utf-8")

    store = SettingsStore.__new__(SettingsStore)
    store._settings_path = settings_path
    store._kl_manager_setup = setup
    store._system_settings = FakeSystemSettings()
    store._log = SilentLogger()
    return store, setup, settings_path


def test_start_drops_stale_layout_and_rewrites_file(tmp_path):
    saved = json.dumps({
        "in_loop_kl_ids": [EN, STALE, RU],
        "next_kl_hotkey": "alt+shift",
        "kl_id_to_hotkey": {STALE: "alt+shift+g"},
    })
    store, setup, settings_path = make_store(tmp_path, saved)

    store.start()  # must not raise

    assert [klid.to_string for klid in setup.in_loop_keyboard_layout_ids] == [EN, RU]
    # File self-healed: the stale klid is gone from disk.
    on_disk = json.loads(settings_path.read_text(encoding="utf-8"))
    assert STALE not in on_disk["in_loop_kl_ids"]
    assert STALE not in on_disk["kl_id_to_hotkey"]


def test_start_survives_corrupt_file(tmp_path):
    store, setup, settings_path = make_store(tmp_path, "{ this is not valid json")

    store.start()  # must not raise

    # Fell back to defaults and rewrote a valid file.
    on_disk = json.loads(settings_path.read_text(encoding="utf-8"))
    assert on_disk["in_loop_kl_ids"] == [EN, RU]


def test_start_leaves_a_clean_file_untouched_in_content(tmp_path):
    store, setup, settings_path = make_store(tmp_path, None)
    store.start()  # first run writes defaults
    first = settings_path.read_text(encoding="utf-8")

    store2, _, path2 = make_store(tmp_path, first)
    store2.start()  # loading a clean file: no drops
    assert path2.read_text(encoding="utf-8") == first
