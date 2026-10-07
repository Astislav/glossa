"""Autostart via a Task Scheduler logon task (Run key only as a fallback)."""
import os
import uuid
import winreg

import pytest

from app.services.autostart import Autostart, build_task_xml, parse_task_command


class SilentLogger:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass


def test_task_xml_has_the_settings_that_matter():
    xml = build_task_xml(r"PC\user", r"D:\Apps & Tools\Glossa.exe", "", r"D:\Apps & Tools")

    assert "<LogonTrigger>" in xml and r"<UserId>PC\user</UserId>" in xml
    assert "<Priority>4</Priority>" in xml                    # not the below-normal default 7
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in xml   # not killed after 72h
    assert "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>" in xml
    assert "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>" in xml
    assert r"D:\Apps &amp; Tools\Glossa.exe" in xml          # escaped


def test_task_xml_round_trips_the_command():
    xml = build_task_xml(r"PC\user", r"C:\py\pythonw.exe", r'"C:\proj\main.py"', r"C:\proj")
    assert parse_task_command(xml) == (r"C:\py\pythonw.exe", r'"C:\proj\main.py"')


# --- real Task Scheduler, under throwaway names (never the user's real entry) ---

pytestmark_real = pytest.mark.skipif(
    bool(os.environ.get("GITHUB_ACTIONS")),
    reason="registers a real scheduled task — run locally",
)


@pytest.fixture
def autostart():
    suffix = uuid.uuid4().hex[:8]
    a = Autostart(SilentLogger())
    a._task_name = f"Glossa autostart test {suffix}"
    a._VALUE_NAME = f"GlossaTest{suffix}"
    a._command_parts = lambda: (os.path.join(os.environ["SystemRoot"], "System32", "cmd.exe"), "/c exit", os.environ["SystemRoot"])
    yield a
    a.disable()  # cleanup: task and Run entry


@pytestmark_real
def test_enable_registers_logon_task_without_run_entry(autostart):
    autostart.enable()

    assert autostart._task_registered()
    assert not autostart._run_entry_present()
    assert autostart.is_enabled()
    assert autostart._registered_command() == autostart._command_parts()[:2]


@pytestmark_real
def test_disable_removes_everything(autostart):
    autostart.enable()
    autostart.disable()

    assert not autostart._task_registered()
    assert not autostart.is_enabled()


@pytest.fixture
def frozen(monkeypatch):
    """Pretend to be the shipped exe — migrate() only acts there."""
    monkeypatch.setattr("sys.frozen", True, raising=False)


@pytestmark_real
def test_migrate_moves_legacy_run_entry_to_task(autostart, frozen):
    autostart._write_run_entry()  # what older builds did, pointing at this exe
    assert autostart._run_entry_present() and not autostart._task_registered()

    autostart.migrate()

    assert autostart._task_registered()
    assert not autostart._run_entry_present()


@pytestmark_real
def test_migrate_leaves_another_copys_run_entry_alone(autostart, frozen):
    real_command = autostart._command_parts
    autostart._command_parts = lambda: (r"D:\Downloads\Glossa.exe", "", r"D:\Downloads")
    autostart._write_run_entry()          # the installed copy's entry
    autostart._command_parts = real_command  # now "running" a different copy

    autostart.migrate()

    assert autostart._run_entry_present()      # untouched
    assert not autostart._task_registered()


@pytestmark_real
def test_migrate_follows_an_exe_that_moved(autostart, frozen):
    real_command = autostart._command_parts
    autostart._command_parts = lambda: (r"C:\gone\Glossa.exe", "", r"C:\gone")
    autostart.enable()                      # registered for a path that no longer exists
    autostart._command_parts = real_command

    autostart.migrate()

    assert autostart._registered_command() == real_command()[:2]


@pytestmark_real
def test_migrate_never_repoints_an_existing_exe(autostart, frozen):
    autostart.enable()
    other = os.path.join(os.environ["SystemRoot"], "System32", "where.exe")  # exists
    autostart._command_parts = lambda: (other, "", os.environ["SystemRoot"])

    autostart.migrate()  # a second copy is running; the registered exe still exists

    assert autostart._registered_command()[0] != other


@pytestmark_real
def test_migrate_does_nothing_when_running_from_source(autostart):
    autostart._write_run_entry()

    autostart.migrate()  # not frozen

    assert autostart._run_entry_present()
    assert not autostart._task_registered()


@pytestmark_real
def test_registered_command_survives_a_cyrillic_path(autostart):
    # schtasks reports the task in the OEM code page — a non-ASCII path must
    # still compare equal, or migrate() would re-register on every start.
    cyrillic = r"C:\Программы\Глосса\Glossa.exe"
    autostart._command_parts = lambda: (cyrillic, "", r"C:\Программы")
    autostart.enable()

    assert autostart._registered_command() == (cyrillic, "")
