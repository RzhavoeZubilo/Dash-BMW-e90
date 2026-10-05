#!/usr/bin/env python3
"""Чтение памяти приборки BMW (KOMBI / KOMB87) через EDIABAS api32.dll.

Читает произвольный диапазон через штатный джоб `SPEICHER_LESEN`
(KWP2000 `$23` ReadMemoryByAddress) и складывает результат в raw `.bin`.

Зачем именно так: телетрамму собирает сам SGBD `KOMB87.prg`, поэтому
реализовывать транспорт не нужно — EDIABAS делает всё сам. Скрипт только
крутит джоб по адресам и склеивает ответы.

Целевые сегменты (`SEG_BYTE` из таблицы `SPEICHERSEGMENT`):
    0x00 LAR, 0x01 ROMI, 0x02 ROMX, 0x03 NVRAM, 0x04 RAMIS,
    0x05 RAMXX, 0x06 FLASH, 0x07 UIFM, 0x08 VODM, 0x09 FLASHX, 0x0B RAMIL

Требования:
    * Windows с установленными BMW Standard Tools (EDIABAS);
    * **32-битный** Python (pydiabas грузит api32.dll);
    * `pip install pydiabas`.

Примеры:
    python kombi_read_flash.py --check
    python kombi_read_flash.py --ident
    python kombi_read_flash.py --segment FLASH --start 0xFFC000 --end 0x1000000 \\
        --out bootloader.bin
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path

# Кандидаты имени ЭБУ: EDIABAS резолвит имя в <имя>.prg в C:\EDIABAS\Ecu
CANDIDATE_ECUS = ["KOMB87", "KOMBI", "KOMB87.PRG", "KOMBI.PRG"]


def info(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str) -> None:
    print(f"ОШИБКА: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


class EcuError(RuntimeError):
    """EDIABAS вернул ошибку по джобу (или SGBD не найден)."""


# --------------------------------------------------------------------------
# Проверка окружения

def check_environment() -> int:
    bits = struct.calcsize("P") * 8
    info(f"Python: {sys.version.split()[0]}, разрядность {bits}")
    ok = True

    if sys.platform != "win32":
        info("  ! это не Windows — api32.dll доступен только там")
        ok = False

    if bits != 32:
        info("  ! нужен 32-битный Python: pydiabas грузит api32.dll.")
        info("    Установите 32-битный Python и запускайте через `py -3-32`.")
        ok = False
    else:
        info("  разрядность подходит для api32.dll")

    try:
        import pydiabas  # noqa: F401
        info(f"pydiabas: найден ({Path(pydiabas.__file__).parent})")
    except Exception as exc:  # noqa: BLE001
        info(f"  ! pydiabas не найден: {exc}")
        info("    установите: py -3-32 -m pip install pydiabas")
        ok = False

    if ok:
        try:
            from ctypes.util import find_library
            dll = find_library("api32")
            if dll is None:
                info("  ! api32.dll не найден в PATH. Обычно он лежит в")
                info("    C:\\EDIABAS\\BIN — добавьте этот каталог в PATH.")
                ok = False
            else:
                info(f"api32.dll: {dll}")
        except Exception as exc:  # noqa: BLE001
            info(f"  ! не удалось найти api32.dll: {exc}")
            ok = False

    return 0 if ok else 2


# --------------------------------------------------------------------------
# Работа с EDIABAS

class Kombi:
    """Тонкая обёртка над pydiabas: инициализация, джобы, ожидание."""

    def __init__(self, ecu: str, timeout_s: float = 30.0) -> None:
        from pydiabas import Pydiabas

        self.ecu = ecu
        self.timeout_s = timeout_s
        self.api = Pydiabas()
        self.api.init()

    def close(self) -> None:
        try:
            self.api.end()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> "Kombi":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _wait_ready(self) -> None:
        """apiJob асинхронный: ждём, пока EDIABAS освободится."""
        deadline = time.monotonic() + self.timeout_s
        while True:
            state = self.api.state()
            if int(getattr(state, "value", state)) == 1:  # READY
                return
            if time.monotonic() > deadline:
                raise EcuError(f"таймаут ожидания EDIABAS ({self.timeout_s} с)")
            time.sleep(0.01)

    def run_job(self, job: str, params: str = "") -> None:
        self.api.job(self.ecu, job, params, "")
        self._wait_ready()
        code = self.api.errorCode()
        if code:
            raise EcuError(f"джоб {job}({params}) — код {code}: {self.api.errorText()}")

    def result_text(self, name: str) -> str:
        try:
            return self.api.resultText(name).strip()
        except Exception:  # noqa: BLE001
            return ""

    def ident(self) -> dict[str, str]:
        self.run_job("IDENT")
        out: dict[str, str] = {}
        for name in (
            "ID_BMW_NR", "ID_HW_NR", "ID_DIAG_INDEX", "ID_COD_INDEX",
            "ID_VAR_INDEX", "ID_DATUM", "ID_LIEF_NR", "ID_LIEF_TEXT",
            "ID_SW_NR_MCV", "ID_SW_NR_FSV", "ID_SW_NR_OSV", "ID_SW_NR_RES",
        ):
            value = self.result_text(name)
            if value:
                out[name] = value
        return out

    def read_block(self, segment: str, address: int, count: int) -> bytes:
        """Один вызов SPEICHER_LESEN."""
        self.run_job("SPEICHER_LESEN", f"{segment};0x{address:06X};{count}")
        status = self.result_text("JOB_STATUS")
        if status and status.upper() != "OKAY":
            raise EcuError(f"JOB_STATUS={status}")
        return self.api.resultBinary("DATEN")


def connect(ecu: str, timeout_s: float) -> Kombi:
    """Подключается к ЭБУ; при ecu='auto' перебирает известные имена."""
    if ecu.lower() != "auto":
        kombi = Kombi(ecu, timeout_s)
        kombi.ident()  # сразу проверяем, что SGBD найден и ЭБУ отвечает
        return kombi

    last: str = "нет попыток"
    for candidate in CANDIDATE_ECUS:
        try:
            info(f"  пробую ЭБУ '{candidate}' …")
            kombi = Kombi(candidate, timeout_s)
            kombi.ident()
            info(f"  ЭБУ определён: {candidate}")
            return kombi
        except EcuError as exc:
            last = f"{candidate}: {exc}"
        except Exception as exc:  # noqa: BLE001
            last = f"{candidate}: {exc}"

    fail(
        "не удалось подключиться ни под одним именем ЭБУ.\n"
        f"  последняя ошибка — {last}\n"
        "  проверьте: C:\\EDIABAS\\Ecu\\KOMB87.prg существует, зажигание включено,\n"
        "  связь с приборкой работает (проверьте через INPA/Tool32)."
    )
    raise AssertionError  # недостижимо


# --------------------------------------------------------------------------
# Чтение диапазона

def read_range(
    kombi: Kombi,
    segment: str,
    start: int,
    end: int,
    chunk: int,
    out_path: Path,
    retries: int = 2,
) -> int:
    total = end - start
    data = bytearray(total)
    covered = bytearray(total)
    errors: list[dict] = []

    addr = start
    n = 0
    total_chunks = (total + chunk - 1) // chunk
    t0 = time.monotonic()

    while addr < end:
        want = min(chunk, end - addr)
        n += 1
        payload = b""
        last_exc: Exception | None = None

        for attempt in range(retries + 1):
            try:
                payload = kombi.read_block(segment, addr, want)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < retries:
                    time.sleep(0.3)

        if payload:
            got = len(payload)
            data[addr - start: addr - start + got] = payload
            for i in range(got):
                covered[addr - start + i] = 1
            note = "" if got == want else f"  (вернулось {got} из {want})"
            info(f"  [{n}/{total_chunks}] 0x{addr:06X} +{got}{note}")
            addr += got if got else want
        else:
            info(f"  [{n}/{total_chunks}] 0x{addr:06X}  ОШИБКА: {last_exc}")
            errors.append({"address": f"0x{addr:06X}", "count": want,
                           "error": str(last_exc)})
            addr += want

    out_path.write_bytes(bytes(data))
    manifest = out_path.with_suffix(".manifest.json")
    manifest.write_text(
        json.dumps({
            "ecu": kombi.ecu, "segment": segment,
            "start": f"0x{start:06X}", "end": f"0x{end:06X}", "chunk": chunk,
            "bytes_total": total, "bytes_covered": sum(covered),
            "errors": errors, "elapsed_s": round(time.monotonic() - t0, 1),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    info("")
    summarize(bytes(data), covered, start)
    info(f"\nзаписано: {out_path} ({total} байт)")
    info(f"покрыто:  {sum(covered)} из {total} "
         f"({100 * sum(covered) // max(total, 1)} %)")
    info(f"манифест: {manifest}")
    if errors:
        info(f"ошибок:   {len(errors)} (см. манифест)")
    return len(errors)


def summarize(data: bytes, covered: bytearray, start: int) -> None:
    """Быстрая проверка: похоже ли прочитанное на настоящий код."""
    info("--- проверка содержимого ---")
    blank = sum(1 for b in data if b == 0xFF)
    zero = sum(1 for b in data if b == 0x00)
    info(f"  байт 0xFF: {blank} ({100 * blank // max(len(data), 1)} %)")
    info(f"  байт 0x00: {zero} ({100 * zero // max(len(data), 1)} %)")

    if blank > len(data) * 0.9:
        info("  ВНИМАНИЕ: почти всё 0xFF — область пустая или сегмент не тот.")
        return

    info("  фрагмент в начале диапазона:")
    for off in range(0, min(32, len(data)), 16):
        chunk = data[off:off + 16]
        info(f"    {start + off:06X}  {chunk.hex(' ')}")

    info("  хвост (здесь ожидается таблица векторов, а не 0xFF):")
    tail_from = max(0, len(data) - 32)
    for off in range(tail_from, len(data), 16):
        chunk = data[off:off + 16]
        info(f"    {start + off:06X}  {chunk.hex(' ')}")


# --------------------------------------------------------------------------

def parse_int(text: str) -> int:
    return int(text, 0)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Чтение памяти приборки BMW через EDIABAS (SPEICHER_LESEN)")
    ap.add_argument("--ecu", default="auto",
                    help="имя SGBD/ЭБУ; 'auto' перебирает известные (по умолчанию)")
    ap.add_argument("--check", action="store_true",
                    help="только проверить окружение и выйти")
    ap.add_argument("--ident", action="store_true",
                    help="прочитать идентификацию ЭБУ и выйти")
    ap.add_argument("--segment", default="FLASH",
                    help="LAR/ROMI/ROMX/NVRAM/RAMIS/RAMXX/FLASH/UIFM/VODM/"
                         "FLASHX/RAMIL (по умолчанию FLASH)")
    ap.add_argument("--start", type=parse_int, default=0xFFC000,
                    help="начальный адрес (по умолчанию 0xFFC000)")
    ap.add_argument("--end", type=parse_int, default=0x1000000,
                    help="конечный адрес, не включая (по умолчанию 0x1000000)")
    ap.add_argument("--chunk", type=int, default=254,
                    help="байт за вызов, максимум 254")
    ap.add_argument("--out", type=Path, default=Path("kombi_dump.bin"),
                    help="куда писать raw-дамп")
    ap.add_argument("--retries", type=int, default=2,
                    help="повторов на неудачный вызов")
    ap.add_argument("--timeout", type=float, default=30.0,
                    help="таймаут ожидания EDIABAS, секунды")
    args = ap.parse_args()

    if args.check:
        return check_environment()

    if not (1 <= args.chunk <= 254):
        fail("--chunk должен быть 1..254 (ограничение джоба SPEICHER_LESEN)")
    if args.end <= args.start:
        fail("--end должен быть больше --start")

    info(f"сегмент:  {args.segment}")
    info(f"диапазон: 0x{args.start:06X} .. 0x{args.end - 1:06X} "
         f"({args.end - args.start} байт)")

    with connect(args.ecu, args.timeout) as kombi:
        info(f"ЭБУ:      {kombi.ecu}")
        if args.ident:
            info("\n--- IDENT ---")
            for key, value in kombi.ident().items():
                info(f"  {key:<16} {value}")
            return 0

        errors = read_range(kombi, args.segment, args.start, args.end,
                            args.chunk, args.out, args.retries)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
