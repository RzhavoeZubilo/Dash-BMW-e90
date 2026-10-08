#!/usr/bin/env python3
"""Дизассемблер джобов BMW EDIABAS SGBD (.prg / .grp).

Обёртка над `BimmerDaten/decoderPrg.py`: тот умеет разбирать контейнер SGBD
(заголовок 0x9C, тело XOR 0xF7) и выдавать листинг BEST/1, но без адресов
инструкций и без разрешённых целей переходов — для анализа конкретного джоба
этого мало.

Здесь добавлено:
  * адрес у каждой инструкции;
  * разрешённые абсолютные цели `jump`/`jc`/`jz`/... (`__XXXXXXXX`);
  * дамп расшифрованных сырых байт по диапазону адресов (для встроенных таблиц).

Примеры:
    python3 sgbd_disasm.py KOMB87.prg --job SPEICHER_LESEN
    python3 sgbd_disasm.py KOMB87.prg --job AUTHENTISIERUNG_START
    python3 sgbd_disasm.py KOMB87.prg --addr 0x1B274
    python3 sgbd_disasm.py KOMB87.prg --job SPEICHER_LESEN --raw 0x1B274,0x1B3FF
    python3 sgbd_disasm.py KOMB87.prg --list
"""
import argparse
import os
import sys
from pathlib import Path

# Поиск decoderPrg.py: через BIMMERDATEN env var или относительные пути
_ENV_PATH = os.environ.get("BIMMERDATEN")
_CANDIDATES = [
    Path(_ENV_PATH) if _ENV_PATH else None,
    Path(__file__).resolve().parents[2] / "BimmerDaten",
    Path(__file__).resolve().parents[3] / "BimmerDaten",
]
for c in _CANDIDATES:
    if c and (c / "decoderPrg.py").exists():
        sys.path.insert(0, str(c))
        break

try:
    from decoderPrg import OC_MAP, PrgParser  # noqa: E402
except ImportError:
    print("Ошибка: модуль decoderPrg не найден. Задайте путь через BIMMERDATEN=<путь>", file=sys.stderr)
    sys.exit(1)


def disasm_job(p: PrgParser, addr: int, limit: int = 20000):
    """Линейный дизассемблер джоба. Возвращает (строки, цели_переходов)."""
    offset = addr
    out = []
    targets = set()
    eoj_seen = 0

    while len(out) < limit:
        start = offset
        try:
            header = p._read_decrypted(offset, 2)
        except Exception:
            out.append((start, "<конец данных>"))
            break
        offset += 2
        op_code, addr_byte = header[0], header[1]
        mode0 = (addr_byte & 0xF0) >> 4
        mode1 = addr_byte & 0x0F

        if op_code not in OC_MAP:
            out.append((start, f"<неизвестный опкод 0x{op_code:02X}>"))
            break

        mnemonic, arg0_is_near = OC_MAP[op_code]
        try:
            a0, offset = p._read_op_arg(offset, mode0)
            a1, offset = p._read_op_arg(offset, mode1)
        except Exception as exc:
            out.append((start, f"<ошибка операнда: {exc}>"))
            break

        # near-адрес (Imm32) -> абсолютная цель
        if arg0_is_near and mode0 == 7 and a0.startswith("#$"):
            raw = int(a0[2:-2], 16)
            target = offset + raw
            targets.add(target)
            a0 = f"__{target:08X}"

        if a0 and a1:
            text = f"{mnemonic:<10} {a0},{a1}"
        elif a0:
            text = f"{mnemonic:<10} {a0}"
        else:
            text = mnemonic
        out.append((start, text))

        if op_code == 0x1D:  # eoj: два подряд = конец джоба
            eoj_seen += 1
            if eoj_seen >= 2:
                break
        else:
            eoj_seen = 0

    return out, targets


def dump_raw(p: PrgParser, lo: int, hi: int, width: int = 16):
    lines = []
    for base in range(lo, hi, width):
        chunk = p._read_decrypted(base, min(width, hi - base))
        hexs = " ".join(f"{b:02X}" for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{base:08X}  {hexs:<{width * 3}}  {text}")
    return lines


def main():
    ap = argparse.ArgumentParser(description="Дизассемблер джобов BMW SGBD (.prg)")
    ap.add_argument("prg", help="путь к .prg")
    ap.add_argument("--job", help="имя джоба")
    ap.add_argument("--addr", help="адрес джоба (0x...)")
    ap.add_argument("--list", action="store_true", help="только список джобов")
    ap.add_argument("--raw", help="дамп сырых байт LO,HI (0x...), можно с --job")
    ap.add_argument("--limit", type=int, default=20000)
    args = ap.parse_args()

    parser = PrgParser(args.prg)
    prg = parser.parse()

    if args.list or (not args.job and not args.addr):
        print(f"=== {Path(args.prg).name} ===")
        print(f"BIP {prg.info.bip_version}, ревизия {prg.info.revision}, "
              f"таблиц {len(prg.tables)}, джобов {len(prg.jobs)}")
        for job in prg.jobs:
            print(f"  {job.name:<40} @ 0x{job.address:08X}")
        return 0

    if args.raw:
        lo_s, hi_s = args.raw.split(",")
        print(f"--- raw 0x{int(lo_s, 0):X}..0x{int(hi_s, 0):X} ---")
        for line in dump_raw(parser, int(lo_s, 0), int(hi_s, 0)):
            print(line)
        print()

    if args.job:
        match = [j for j in prg.jobs if j.name.upper() == args.job.upper()]
        if not match:
            print(f"Джоб '{args.job}' не найден. Используйте --list.", file=sys.stderr)
            return 1
        addr = match[0].address
        print(f"=== {match[0].name} @ 0x{addr:08X} ===")
        for c in match[0].comments:
            print(f"; {c}")
    else:
        addr = int(args.addr, 0)
        print(f"=== джоб @ 0x{addr:08X} ===")

    lines, targets = disasm_job(parser, addr, args.limit)
    for start, text in lines:
        mark = "*" if start in targets else " "
        print(f"{mark}{start:08X}: {text}")

    unresolved = sorted(t for t in targets if not any(s == t for s, _ in lines))
    if unresolved:
        print()
        print("Цели переходов вне линейного диапазона: "
              + ", ".join(f"0x{t:08X}" for t in unresolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
