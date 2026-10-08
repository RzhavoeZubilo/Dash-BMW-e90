import hashlib
import json
import sys

import check_firmware


def test_sha256_matches_hashlib(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello bmw kombi")

    assert check_firmware.sha256(f) == hashlib.sha256(b"hello bmw kombi").hexdigest()


def test_main_reports_ok_for_matching_file(tmp_path, monkeypatch, capsys):
    data = b"\x01\x02\x03"
    firmware_dir = tmp_path / "local-firmware"
    firmware_dir.mkdir()
    (firmware_dir / "TEST.0pa").write_bytes(data)

    manifest = tmp_path / "firmware-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": {
                    "TEST.0pa": {
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_firmware, "MANIFEST", manifest)
    monkeypatch.setattr(sys, "argv", ["check_firmware.py", "--dir", str(firmware_dir)])

    rc = check_firmware.main()

    out = capsys.readouterr().out
    assert rc == 0
    assert "OK        TEST.0pa" in out


def test_main_reports_missing_file(tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "firmware-manifest.json"
    manifest.write_text(
        json.dumps({"files": {"GHOST.0pa": {"sha256": "0" * 64, "size": 1}}}),
        encoding="utf-8",
    )
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    monkeypatch.setattr(check_firmware, "MANIFEST", manifest)
    monkeypatch.setattr(sys, "argv", ["check_firmware.py", "--dir", str(empty_dir)])

    rc = check_firmware.main()

    out = capsys.readouterr().out
    assert rc == 0  # missing != bad: код возврата у check_firmware.py 0 даже при missing
    assert "НЕТ       GHOST.0pa" in out


def test_main_reports_hash_mismatch(tmp_path, monkeypatch, capsys):
    firmware_dir = tmp_path / "local-firmware"
    firmware_dir.mkdir()
    (firmware_dir / "BAD.0pa").write_bytes(b"wrong content")

    manifest = tmp_path / "firmware-manifest.json"
    manifest.write_text(
        json.dumps(
            {"files": {"BAD.0pa": {"sha256": "0" * 64, "size": len(b"wrong content")}}}
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_firmware, "MANIFEST", manifest)
    monkeypatch.setattr(sys, "argv", ["check_firmware.py", "--dir", str(firmware_dir)])

    rc = check_firmware.main()

    out = capsys.readouterr().out
    assert rc == 1
    assert "ХЕШ       BAD.0pa" in out
