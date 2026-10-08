import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "site" / "build_jobs_data.py"

spec = importlib.util.spec_from_file_location("build_jobs_data", SCRIPT)
build_jobs_data = importlib.util.module_from_spec(spec)
sys.modules["build_jobs_data"] = build_jobs_data
spec.loader.exec_module(build_jobs_data)


def test_parses_standard_line():
    jobs = build_jobs_data.parse_jobs(
        "- `SPEICHER_LESEN` @ 0x0001B274 -- Auslesen des Steuergeraete-Speichers\n"
    )
    assert jobs == [
        {
            "name": "SPEICHER_LESEN",
            "addr": "0x0001B274",
            "comment": "Auslesen des Steuergeraete-Speichers",
            "tags": [],
        }
    ]


def test_extracts_tag_and_strips_it_from_comment():
    jobs = build_jobs_data.parse_jobs(
        "- `FLASH_LOESCHEN` @ 0x000493D0 -- Flash loeschen  **[FIRMWARE]**\n"
    )
    assert jobs[0]["tags"] == ["FIRMWARE"]
    assert "FIRMWARE" not in jobs[0]["comment"]
    assert jobs[0]["comment"] == "Flash loeschen"


def test_handles_tag_before_comment_without_double_dash():
    jobs = build_jobs_data.parse_jobs(
        "- `CODIERDATEN_LESEN` @ 0x00055FFA  **[CODING]** (блок 0x3000-0x3FFF)\n"
    )
    assert jobs[0]["tags"] == ["CODING"]
    assert jobs[0]["comment"] == "(блок 0x3000-0x3FFF)"


def test_handles_line_with_no_comment_at_all():
    jobs = build_jobs_data.parse_jobs("- `STATUS_CBS_ANZEIGE` @ 0x00086600\n")
    assert jobs[0]["comment"] == ""
    assert jobs[0]["tags"] == []


def test_sorted_by_address():
    jobs = build_jobs_data.parse_jobs(
        "- `B` @ 0x00000200 -- second\n"
        "- `A` @ 0x00000100 -- first\n"
    )
    assert [j["name"] for j in jobs] == ["A", "B"]


def test_non_job_lines_are_ignored():
    jobs = build_jobs_data.parse_jobs(
        "# заголовок\n"
        "просто текст, не джоб\n"
        "- `REAL_JOB` @ 0x00000001 -- ok\n"
    )
    assert len(jobs) == 1
    assert jobs[0]["name"] == "REAL_JOB"


def test_real_source_file_is_well_formed():
    # Регрессия: все 133 строки из реального источника должны парситься
    # без предупреждений (см. tools/site/build_jobs_data.py --check в CI).
    src = build_jobs_data.SRC
    assert src.exists(), "docs/research/KOMB87_JOBS.md отсутствует"
    jobs = build_jobs_data.parse_jobs(src.read_text(encoding="utf-8"))
    assert len(jobs) == 133
    names = [j["name"] for j in jobs]
    assert len(names) == len(set(names)), "дублирующиеся имена джобов"


def test_real_repo_jobs_data_js_is_in_sync():
    # Регрессия: напоминает запустить `python3 tools/site/build_jobs_data.py`
    # после правок в docs/research/KOMB87_JOBS.md.
    jobs = build_jobs_data.parse_jobs(build_jobs_data.SRC.read_text(encoding="utf-8"))
    expected = (
        "// Сгенерировано: python3 tools/site/build_jobs_data.py\n"
        "// Источник: docs/research/KOMB87_JOBS.md -- не редактировать руками.\n"
        f"window.KOMBI_JOBS = {json.dumps(jobs, ensure_ascii=False, indent=2)};\n"
    )
    assert build_jobs_data.OUT.exists(), "site/reference/jobs-data.js отсутствует"
    assert build_jobs_data.OUT.read_text(encoding="utf-8") == expected


def test_output_is_valid_json_embedded_in_js(tmp_path, monkeypatch):
    src = tmp_path / "jobs.md"
    src.write_text("- `X` @ 0x00000010 -- test job\n", encoding="utf-8")
    out = tmp_path / "jobs-data.js"
    monkeypatch.setattr(build_jobs_data, "SRC", src)
    monkeypatch.setattr(build_jobs_data, "OUT", out)
    monkeypatch.setattr(sys, "argv", ["build_jobs_data.py"])

    rc = build_jobs_data.main()

    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("// Сгенерировано")
    array_text = text[text.index("[") : text.rindex("]") + 1]
    assert json.loads(array_text) == [
        {"name": "X", "addr": "0x00000010", "comment": "test job", "tags": []}
    ]
