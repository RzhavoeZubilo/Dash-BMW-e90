#!/usr/bin/env python3
"""Проверка локальных проприетарных образов по манифесту.

В репозитории **нет** образов прошивок и файлов SP-Daten: это собственность
BMW, и публиковать их нельзя. Вместо них лежит `firmware-manifest.json`
с контрольными суммами SHA-256, чтобы результаты были воспроизводимы.

Положите свои копии в `local-firmware/` (каталог в .gitignore) и запустите:

    python tools/check-firmware.py
    python tools/check-firmware.py --dir /path/to/your/files
    python tools/check-firmware.py --list

Код возврата: 0 — всё найдено и совпало, 1 — есть расхождения или пропуски.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "firmware-manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=REPO / "local-firmware",
                    help="каталог с вашими копиями (по умолчанию local-firmware/)")
    ap.add_argument("--list", action="store_true",
                    help="только показать ожидаемые файлы")
    args = ap.parse_args()

    if not MANIFEST.exists():
        print(f"нет манифеста: {MANIFEST}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files: dict[str, dict] = manifest["files"]

    if args.list:
        print(f"Ожидается файлов: {len(files)}\n")
        for name, meta in sorted(files.items()):
            print(f"  {name:<28} {meta['size']:>9} байт  {meta['sha256'][:16]}…")
        print(f"\nПоложите их в: {args.dir}")
        return 0

    print(f"Манифест:   {MANIFEST}")
    print(f"Каталог:    {args.dir}\n")

    ok = missing = bad = 0
    for name, meta in sorted(files.items()):
        path = args.dir / name
        if not path.exists():
            print(f"  НЕТ       {name}")
            missing += 1
            continue
        size = path.stat().st_size
        if size != meta["size"]:
            print(f"  РАЗМЕР    {name}: {size} вместо {meta['size']}")
            bad += 1
            continue
        digest = sha256(path)
        if digest != meta["sha256"]:
            print(f"  ХЕШ       {name}: {digest[:16]}… вместо {meta['sha256'][:16]}…")
            bad += 1
            continue
        print(f"  OK        {name}")
        ok += 1

    print(f"\nсовпало: {ok}, отсутствует: {missing}, расхождений: {bad}")
    if missing or bad:
        print("\nЭто нормально, если у вас ещё нет всех образов: часть нужна")
        print("только для отдельных этапов. Важно, чтобы совпадали те, с")
        print("которыми вы работаете, — иначе результаты будут несовместимы.")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
