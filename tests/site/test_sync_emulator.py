import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "site" / "sync_emulator.py"

spec = importlib.util.spec_from_file_location("sync_emulator", SCRIPT)
sync_emulator = importlib.util.module_from_spec(spec)
sys.modules["sync_emulator"] = sync_emulator
spec.loader.exec_module(sync_emulator)


def test_writes_exact_copy_of_source(tmp_path, monkeypatch):
    src = tmp_path / "index.html"
    src.write_text("<html>simulator</html>", encoding="utf-8")
    out = tmp_path / "simulator.html"
    monkeypatch.setattr(sync_emulator, "SRC", src)
    monkeypatch.setattr(sync_emulator, "OUT", out)
    monkeypatch.setattr(sys, "argv", ["sync_emulator.py"])

    rc = sync_emulator.main()

    assert rc == 0
    assert out.read_text(encoding="utf-8") == "<html>simulator</html>"


def test_check_mode_fails_when_copy_is_stale(tmp_path, monkeypatch):
    src = tmp_path / "index.html"
    src.write_text("new content", encoding="utf-8")
    out = tmp_path / "simulator.html"
    out.write_text("old content", encoding="utf-8")
    monkeypatch.setattr(sync_emulator, "SRC", src)
    monkeypatch.setattr(sync_emulator, "OUT", out)
    monkeypatch.setattr(sys, "argv", ["sync_emulator.py", "--check"])

    rc = sync_emulator.main()

    assert rc == 1
    assert out.read_text(encoding="utf-8") == "old content"  # не перезаписан


def test_check_mode_passes_when_in_sync(tmp_path, monkeypatch):
    src = tmp_path / "index.html"
    src.write_text("same", encoding="utf-8")
    out = tmp_path / "simulator.html"
    out.write_text("same", encoding="utf-8")
    monkeypatch.setattr(sync_emulator, "SRC", src)
    monkeypatch.setattr(sync_emulator, "OUT", out)
    monkeypatch.setattr(sys, "argv", ["sync_emulator.py", "--check"])

    assert sync_emulator.main() == 0


def test_real_repo_files_are_in_sync():
    # Регрессия: напоминает запустить `python3 tools/site/sync_emulator.py`
    # после правок в tools/ui_simulator/index.html.
    assert sync_emulator.SRC.exists()
    assert sync_emulator.OUT.exists(), "site/emulator/simulator.html отсутствует"
    assert sync_emulator.SRC.read_text(encoding="utf-8") == sync_emulator.OUT.read_text(encoding="utf-8")
