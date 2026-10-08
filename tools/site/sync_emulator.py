#!/usr/bin/env python3
"""Синхронизирует site/emulator/simulator.html с tools/ui_simulator/index.html.

Источник истины — tools/ui_simulator/index.html (самостоятельный инструмент,
им же пользуются локально при разработке прошивки). Страница сайта
встраивает его через iframe, чтобы не дублировать Tailwind-разметку и JS
вручную и не разойтись с оригиналом по мере его доработки.

Usage:
    python3 tools/site/sync_emulator.py
    python3 tools/site/sync_emulator.py --check   # код 1, если копия устарела
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "tools" / "ui_simulator" / "index.html"
OUT = REPO / "site" / "emulator" / "simulator.html"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                     help="только проверить, что simulator.html совпадает с источником")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"нет источника: {SRC}", file=sys.stderr)
        return 1

    content = SRC.read_text(encoding="utf-8")

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != content:
            print(f"{OUT} устарел относительно {SRC} -- запустите без --check", file=sys.stderr)
            return 1
        print(f"OK: {OUT} в синхроне с {SRC}")
        return 0

    OUT.write_text(content, encoding="utf-8")
    print(f"записано {OUT} ({len(content)} байт из {SRC})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
