#!/usr/bin/env python3
r"""Генератор site/reference/jobs-data.js из docs/research/KOMB87_JOBS.md.

Источник истины — markdown-файл (читается людьми и правится при новых
находках реверса); этот скрипт просто конвертирует его построчный формат
`- \`NAME\` @ 0xADDR -- comment` в JSON-массив для таблицы на сайте, чтобы
данные не приходилось дублировать руками и держать в синхроне вручную.

Usage:
    python3 tools/site/build_jobs_data.py
    python3 tools/site/build_jobs_data.py --check   # код 1, если файл устарел
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "docs" / "research" / "KOMB87_JOBS.md"
OUT = REPO / "site" / "reference" / "jobs-data.js"

LINE_RE = re.compile(
    r"^- `(?P<name>[A-Z0-9_]+)` @ (?P<addr>0x[0-9A-Fa-f]+)(?:\s*--\s*|\s+)?(?P<comment>.*)$"
)
TAG_RE = re.compile(r"\*\*\[(?P<tag>[A-Z]+)(?: -- .*?)?\]\*\*")


def parse_jobs(text: str) -> list[dict]:
    jobs = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("- `"):
            continue
        m = LINE_RE.match(s)
        if not m:
            print(f"предупреждение: строка не распозналась и пропущена: {s!r}", file=sys.stderr)
            continue
        comment = m.group("comment").strip()
        tags = TAG_RE.findall(comment)
        clean_comment = TAG_RE.sub("", comment).strip(" -")
        jobs.append(
            {
                "name": m.group("name"),
                "addr": m.group("addr").upper().replace("0X", "0x"),
                "comment": clean_comment,
                "tags": tags,
            }
        )
    jobs.sort(key=lambda j: int(j["addr"], 16))
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                     help="только проверить, что jobs-data.js соответствует источнику")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"нет источника: {SRC}", file=sys.stderr)
        return 1

    jobs = parse_jobs(SRC.read_text(encoding="utf-8"))
    if not jobs:
        print("не нашлось ни одного джоба — формат источника изменился?", file=sys.stderr)
        return 1

    rendered = (
        "// Сгенерировано: python3 tools/site/build_jobs_data.py\n"
        "// Источник: docs/research/KOMB87_JOBS.md -- не редактировать руками.\n"
        f"window.KOMBI_JOBS = {json.dumps(jobs, ensure_ascii=False, indent=2)};\n"
    )

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(f"{OUT} устарел относительно {SRC} -- запустите без --check", file=sys.stderr)
            return 1
        print(f"OK: {OUT} в синхроне с источником ({len(jobs)} джобов)")
        return 0

    OUT.write_text(rendered, encoding="utf-8")
    print(f"записано {OUT}: {len(jobs)} джобов")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
