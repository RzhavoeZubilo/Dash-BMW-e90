#!/usr/bin/env python3
"""Проверка окружения для работы с приборкой BMW через EDIABAS.

Чем это отличается от `kombi_read_flash.py --check`: тот проверяет только
Python и `pydiabas`. Здесь проверяется **вся цепочка до машины**:

    32-битный Python -> pydiabas -> api32.dll -> установка EDIABAS ->
    EDIABAS.INI -> OBD.INI (COM-порт) -> драйвер кабеля и LatencyTimer ->
    SGBD приборки в EcuPath -> сопоставление с firmware-manifest.json

Всё, что можно, читается из реестра и конфигов — машина и кабель не нужны.
Приборку скрипт не опрашивает (для этого `--ident` в kombi_read_flash.py).

Запуск (именно 32-битным Python):
    py -3-32 flasher/check_bmw_env.py
    py -3-32 flasher/check_bmw_env.py --ediabas "D:\\EDIABAS"
    py -3-32 flasher/check_bmw_env.py --firmware-scan "C:\\NCSEXPER,C:\\EDIABAS"

Код возврата: 0 — всё на месте; 1 — предупреждения (чаще всего нет кабеля);
2 — не выполнены критичные условия, работать не получится.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OK = "OK  "
WARN = "!   "
BAD = "X   "

problems: list[tuple[str, str]] = []   # (severity, текст): severity в {bad, warn}


def say(mark: str, text: str) -> None:
    print(f"  {mark}{text}")


def bad(text: str) -> None:
    problems.append(("bad", text))
    say(BAD, text)


def warn(text: str) -> None:
    problems.append(("warn", text))
    say(WARN, text)


def head(text: str) -> None:
    print(f"\n=== {text} ===")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Кандидаты путей установки

DEFAULT_EDIABAS = [
    Path(r"C:\EDIABAS"),
    Path(r"C:\EC-APPS\EDIABAS"),
]

# Где искать другие копии EDIABAS. Полный обход диска слишком долог, поэтому
# это список типовых мест, включая репаки на внешних дисках.
DISCOVERY_ROOTS = [
    r"C:\EDIABAS",
    r"C:\EC-APPS",
    r"F:\BMW",
    r"G:\BMW Standard Tools",
    r"G:\BimmerGeeks Standard Tools",
    r"G:\BMW",
    r"G:\SoftPack",
]


def read_ini(path: Path) -> dict[str, dict[str, str]]:
    """Простейший разбор .INI: секции -> ключи. Регистр ключей сохраняется.

    EDIABAS.INI из BMW Standard Tools бывает в UTF-16LE (его пишет установщик),
    поэтому кодировка определяется по содержимому, а не задаётся жёстко:
    иначе файл выглядит как одна строка с нулевыми байтами и не разбирается.
    """
    out: dict[str, dict[str, str]] = {}
    section = ""
    try:
        raw = path.read_bytes()
    except OSError:
        return out
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16", errors="replace")
    else:
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("latin-1", errors="replace")
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            out.setdefault(section, {})
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            out.setdefault(section, {})[key.strip()] = value.strip()
    return out


def ini_get(table: dict[str, dict[str, str]], key: str, *sections: str) -> str:
    """Значение ключа. Секции — только предпочтение: EDIABAS.INI держит
    настройки в [Configuration], OBD.INI — в [OBD], а сборки бывают разные,
    поэтому при промахе ключ ищется по всему файлу."""
    wanted = [s.lower() for s in sections]
    for name, values in table.items():
        if wanted and name.lower() not in wanted:
            continue
        for k, v in values.items():
            if k.lower() == key.lower():
                return v
    if wanted:
        return ini_get(table, key)
    return ""


# ---------------------------------------------------------------------------
# Реестр: COM-порты, драйверы, LatencyTimer

def system_ports() -> dict[str, str]:
    """COMn -> путь устройства, из DEVICEMAP\\SERIALCOMM."""
    ports: dict[str, str] = {}
    try:
        import winreg
    except ImportError:
        return ports
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DEVICEMAP\SERIALCOMM") as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                except OSError:
                    break
                ports[str(value).upper()] = name
                i += 1
    except OSError:
        pass
    return ports


def _walk_enum(root: str):
    """Перебирает записи HKLM\\SYSTEM\\CurrentControlSet\\Enum\\<root>."""
    try:
        import winreg
    except ImportError:
        return
    try:
        top = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             rf"SYSTEM\CurrentControlSet\Enum\{root}")
    except OSError:
        return
    i = 0
    while True:
        try:
            vendor = winreg.EnumKey(top, i)
        except OSError:
            break
        i += 1
        try:
            vkey = winreg.OpenKey(top, vendor)
        except OSError:
            continue
        j = 0
        while True:
            try:
                instance = winreg.EnumKey(vkey, j)
            except OSError:
                break
            j += 1
            params = rf"SYSTEM\CurrentControlSet\Enum\{root}\{vendor}\{instance}\Device Parameters"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, params) as pkey:
                    entry: dict[str, object] = {}
                    for field in ("PortName", "LatencyTimer"):
                        try:
                            entry[field] = winreg.QueryValueEx(pkey, field)[0]
                        except OSError:
                            pass
                    yield f"{root}\\{vendor}\\{instance}", entry
            except OSError:
                continue


def adapter_info() -> list[tuple[str, dict[str, object]]]:
    """Кабели семейств FTDI / CH340 / CP210x и их LatencyTimer."""
    found: list[tuple[str, dict[str, object]]] = []
    for root in ("FTDIBUS", r"USB\VID_1A86", r"USB\VID_10C4"):
        for name, entry in _walk_enum(root) or ():
            if entry:
                found.append((name, entry))
    return found


# ---------------------------------------------------------------------------
# Проверки

def check_python() -> None:
    head("Python и pydiabas")
    bits = struct.calcsize("P") * 8
    version = sys.version.split()[0]
    if bits == 32:
        say(OK, f"Python {version}, разрядность {bits}")
    else:
        bad(f"Python {version}, разрядность {bits} — нужен 32-битный "
            f"(api32.dll 32-битная). Запускайте через `py -3-32`.")

    if sys.platform != "win32":
        bad(f"платформа {sys.platform} — api32.dll существует только под Windows")
        return

    try:
        import pydiabas  # noqa: F401
        where = Path(pydiabas.__file__).parent
        say(OK, f"pydiabas найден: {where}")
    except Exception as exc:  # noqa: BLE001
        bad(f"pydiabas не импортируется: {exc} — "
            f"поставьте `py -3-32 -m pip install pydiabas`")
        return

    if bits != 32:
        return

    # api32.dll: find_library ищет по PATH — ровно так же, как pydiabas.
    located = ctypes.util.find_library("api32")
    if not located:
        bad("api32.dll не найден в PATH — добавьте C:\\EDIABAS\\BIN "
            "и перезапустите консоль (PATH перечитывается только при старте)")
        return
    say(OK, f"api32.dll найден: {located}")

    # Наличие в PATH — ещё не загрузка: у библиотеки есть зависимости.
    try:
        ctypes.WinDLL(located)
        say(OK, "api32.dll загружается (зависимости разрешаются)")
    except OSError as exc:
        bad(f"api32.dll найден, но не загружается: {exc}")
        return

    # Помощник find_library находит по имени, но WinDLL("api32.dll") без
    # каталога в списке поиска падает — проверим, что pydiabas сработает.
    dll_dir = str(Path(located).parent)
    added = False
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(dll_dir)
            added = True
        except OSError:
            pass
    try:
        ctypes.WinDLL("api32.dll")
        say(OK, "загрузка по имени тоже работает — pydiabas стартует без правок")
    except OSError:
        if added:
            warn("загрузка по имени без add_dll_directory не работает, "
                 "но pydiabas подставляет полный путь из find_library — это норма")
        else:
            warn("загрузка по имени не работает; если pydiabas упадёт — "
                 "запускайте из каталога EDIABAS\\BIN")


def find_ediabas(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    if os.environ.get("EDIABAS_BIN"):
        return Path(os.environ["EDIABAS_BIN"]).parent
    for candidate in DEFAULT_EDIABAS:
        if (candidate / "BIN" / "api32.dll").exists():
            return candidate
    return None


def check_ediabas(root: Path | None) -> tuple[dict, dict]:
    head("Установка EDIABAS")
    if root is None or not root.exists():
        bad("каталог EDIABAS не найден — укажите `--ediabas <путь>`")
        return {}, {}
    say(OK, f"каталог установки: {root}")

    ini_path = root / "BIN" / "EDIABAS.INI"
    if not ini_path.exists():
        bad(f"нет {ini_path} — установка неполная")
        return {}, {}
    ini = read_ini(ini_path)
    interface = ini_get(ini, "Interface", "Configuration", "EDIABAS")
    ecupath = ini_get(ini, "EcuPath", "Configuration", "EDIABAS")
    simulation = ini_get(ini, "Simulation", "Configuration", "EDIABAS")
    say(OK, f"EDIABAS.INI: Interface={interface or '?'}, "
            f"EcuPath={ecupath or '?'}, Simulation={simulation or '?'}")
    if simulation not in ("", "0"):
        warn(f"Simulation={simulation} — EDIABAS работает в режиме имитации, "
             f"к реальной машине не подключится")
    if interface.upper() != "STD:OBD":
        warn(f"Interface={interface}: для кабеля K+DCAN ожидается STD:OBD")

    obd_path = root / "BIN" / "OBD.INI"
    obd = read_ini(obd_path) if obd_path.exists() else {}
    if not obd:
        bad(f"нет {obd_path} — COM-порт OBD-интерфейса задать негде")
        return ini, {}
    port = ini_get(obd, "Port", "OBD")
    hardware = ini_get(obd, "Hardware", "OBD")
    say(OK, f"OBD.INI: [OBD] Port={port or '?'}, Hardware={hardware or '?'}")
    return ini, obd


def check_cable(obd: dict, ini: dict, ediabas_root: Path | None) -> None:
    head("Кабель и COM-порт")
    ports = system_ports()
    if ports:
        for com, device in sorted(ports.items()):
            say(OK, f"{com} <- {device}")
    else:
        warn("в системе ни одного COM-порта: кабель не подключён или нет драйвера")

    configured = ini_get(obd, "Port", "OBD") if obd else ""
    if configured:
        if not ports:
            warn(f"в OBD.INI прописан {configured}, но портов в системе нет — "
                 f"подключите кабель и проверьте, что порт совпадает")
        elif configured.upper() not in ports:
            bad(f"OBD.INI указывает {configured}, а в системе есть только "
                f"{', '.join(sorted(ports))} — EDIABAS не найдёт адаптер. "
                f"Поправьте {ediabas_root / 'BIN' / 'OBD.INI' if ediabas_root else 'OBD.INI'}")
        else:
            say(OK, f"порт {configured} из OBD.INI присутствует в системе")

    adapters = adapter_info()
    if not adapters:
        warn("в реестре нет записей FTDI/CH340/CP210x — "
             "похоже, кабель ни разу не подключался на этой машине")
        return
    for name, entry in adapters:
        port = str(entry.get("PortName", "?"))
        latency = entry.get("LatencyTimer")
        family = "FTDI" if name.startswith("FTDIBUS") else (
            "CH340" if "1A86" in name else "CP210x")
        # Запись в Enum остаётся и после отключения устройства: о текущем
        # наличии говорит только DEVICEMAP\SERIALCOMM.
        present = port.upper() in ports
        state = "подключён" if present else "не активен сейчас"
        detail = f"{family} {port} ({state})"
        if latency is not None:
            detail += f", LatencyTimer={latency} мс"
        if not present:
            warn(detail + " — устройство было установлено раньше; "
                          "подключите кабель")
        elif latency is not None and int(latency) != 1:
            warn(detail + " — по инструкции нужно 1 мс, иначе таймауты")
        else:
            say(OK, detail)


def check_sgdb(ini: dict, ediabas_root: Path | None,
               manifest: Path | None) -> None:
    head("SGBD приборки и сверка с манифестом")
    ecupath = ini_get(ini, "EcuPath", "Configuration", "EDIABAS") if ini else ""
    ecu_dir = Path(ecupath) if ecupath else (
        ediabas_root / "ECU" if ediabas_root else None)
    if not ecu_dir or not ecu_dir.exists():
        bad(f"каталог ЭБУ не найден: {ecu_dir}")
        return

    wanted = ["KOMB87.prg", "KOMB87.PRG"]
    sgdb = next((ecu_dir / n for n in wanted if (ecu_dir / n).exists()), None)
    if sgdb is None:
        bad(f"{ecu_dir}\\KOMB87.prg отсутствует — читать приборку нечем")
        return
    digest = sha256(sgdb)
    say(OK, f"{sgdb}  {sgdb.stat().st_size} Б")
    say(OK, f"sha256 {digest[:16]}…")

    if manifest and manifest.exists():
        table = json.loads(manifest.read_text(encoding="utf-8"))["files"]
        matches = [n for n, m in table.items() if m["sha256"] == digest]
        if matches:
            say(OK, f"совпадает с манифестом: {', '.join(matches)}")
        else:
            warn("этого SGBD нет в firmware-manifest.json — "
                 "результаты могут расходиться с описанными в docs/research")

        # Прочие версии KOMB87.prg из манифеста: ищем по размеру и говорим
        # прямо, какая это версия — они разбирались в docs/research по-разному.
        others = {n: m for n, m in table.items()
                  if n.upper().startswith("KOMB87") and n not in matches}
        if others:
            print("       другие версии KOMB87.prg из манифеста:")
            for name, meta in sorted(others.items()):
                same_size = [p.name for p in ecu_dir.glob("*.prg")
                             if p.stat().st_size == meta["size"]]
                tail = (f"  <- по размеру похож: {', '.join(same_size)}"
                        if same_size else "  (не найден)")
                print(f"         {name:<30} {meta['size']:>9} Б{tail}")


def check_tools(ediabas_root: Path | None) -> None:
    head("Остальные инструменты BMW")
    checks = [
        ("Tool32.exe — ручной запуск джобов (главный путь для чтения)",
         [ediabas_root / "BIN" / "Tool32.exe"] if ediabas_root else []),
        ("NCS Expert (кодирование)",
         [Path(r"C:\NCSEXPER\BIN\NCSEXPER.EXE")]),
        ("NFS.exe (браузер SP-Daten)", [Path(r"C:\EC-APPS\NFS\BIN\NFS.exe")]),
    ]
    for title, candidates in checks:
        found = next((p for p in candidates if p.exists()), None)
        if found:
            say(OK, f"{title}: {found}")
        else:
            warn(f"{title} — не найден")

    # WinKFP: важен не только exe, но и наличие образов нашего семейства
    # в его каталоге DATA — иначе прошивать нечего.
    winkfp = [Path(r"C:\EC-APPS\NFS\BIN\winkfpt.exe"),
              Path(r"C:\WINFKP\BIN\WinKFP.exe"),
              Path(r"G:\BMW Standard Tools\EC-APPS\NFS\BIN\winkfpt.exe")]
    for exe in winkfp:
        if not exe.exists():
            continue
        data = exe.parent.parent / "DATA"
        families = []
        if data.is_dir():
            # re.search, а не match: семейства называются BKOML2, DKOML2,
            # HKOML2, KOMBL2 — «KOM» стоит в середине трёх из четырёх.
            families = sorted(d.name for d in data.iterdir()
                              if d.is_dir() and re.search(r"KOMB|KOML", d.name))
        if families:
            say(OK, f"WinKFP: {exe} — образы нашего щитка есть: "
                    f"{', '.join(families)}")
        else:
            warn(f"WinKFP: {exe} — в {data} НЕТ ни одного семейства KOMBI "
                 f"(BKOML2/DKOML2/HKOML2/KOMBL2): прошить щиток нечем")

    # INPA без каталога SGDAT бесполезна: exe на месте, а моделей нет.
    for load in (Path(r"C:\EC-APPS\INPA\BIN\INPALOAD.exe"),
                 Path(r"G:\BMW Standard Tools\EC-APPS\INPA\BIN\INPALOAD.exe"),
                 Path(r"G:\BMW Standard Tools\EC-APPS\INPA_FXX\BIN\INPALOAD.exe")):
        if not load.exists():
            continue
        sgdat = load.parent.parent / "SGDAT"
        count = sum(1 for _ in sgdat.rglob("*") if _.is_file()) if sgdat.is_dir() else 0
        e90 = any(sgdat.rglob("E90.*")) if sgdat.is_dir() else False
        if count >= 100:
            say(OK, f"INPA: {load} — моделей в SGDAT: {count}"
                    + (", E90 есть" if e90 else ""))
        else:
            warn(f"INPA: {load} — в SGDAT всего {count} файл(ов): модель не "
                 f"выбрать, для E90 нужна другая копия INPA")


def check_installations() -> Path | None:
    """Разбирает «несколько установок»: какая EDIABAS реально используется.

    Windows берёт api32.dll по порядку PATH, а EDIABAS.INI — из каталога,
    указанного переменной ediabas_config_dir. Если эти два места из разных
    установок, конфигурация и библиотека расходятся: снаружи это выглядит как
    «INPA не видит машину» при формально правильных файлах.
    """
    head("Установки EDIABAS: какая активна")
    entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    with_dll: list[Path] = []
    winner: Path | None = None
    for entry in entries:
        dll = Path(entry) / "api32.dll"
        if dll.is_file():
            if winner is None:
                winner = Path(entry)
            with_dll.append(Path(entry))
    if winner is None:
        bad("ни в одном каталоге PATH нет api32.dll — EDIABAS недоступен")
        return None
    say(OK, f"активная библиотека: {winner / 'api32.dll'}")

    # Дубликаты и лишние копии в PATH: сами по себе безвредны, но именно они
    # превращают смену порядка в необъяснимую поломку.
    uniq = sorted({os.path.normcase(os.path.abspath(str(p))) for p in with_dll})
    if len(uniq) > 1:
        # Печатаем уникальные каталоги: один и тот же путь в PATH обычно
        # встречается дважды в разном регистре и создаёт ложное «их много».
        uniq_dirs = sorted({str(p) for p in with_dll
                            if os.path.normcase(os.path.abspath(str(p))) in uniq})
        warn(f"в PATH {len(uniq)} разные установки EDIABAS (работает первая): "
             + "; ".join(uniq_dirs))
    if len(with_dll) != len(uniq):
        warn(f"в PATH дубликаты записей EDIABAS ({len(with_dll)} записей, "
             f"{len(uniq)} разных каталогов) — стоит почистить")

    cfg = os.environ.get("ediabas_config_dir") or os.environ.get("EDIABAS_CONFIG_DIR")
    if not cfg:
        warn("переменная ediabas_config_dir не задана — EDIABAS.INI будет "
             "искаться иначе (текущий каталог/каталог библиотеки)")
    elif os.path.normcase(os.path.abspath(cfg)) == os.path.normcase(
            os.path.abspath(str(winner))):
        say(OK, f"ediabas_config_dir={cfg} совпадает с активной библиотекой")
    else:
        warn(f"ediabas_config_dir={cfg}, а библиотека грузится из {winner} — "
             f"конфигурация и код из разных установок, это частая причина "
             f"«ничего не работает»")

    copies: list[tuple[Path, str, str, str]] = []
    for root in DISCOVERY_ROOTS:
        base = Path(root)
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            rel = os.path.relpath(dirpath, base)
            if rel.count(os.sep) >= 6:
                dirnames[:] = []
                continue
            if "EDIABAS.INI" in filenames:
                here = Path(dirpath)
                ini = read_ini(here / "EDIABAS.INI")
                obd = read_ini(here / "OBD.INI")
                copies.append((
                    here,
                    ini_get(ini, "Interface", "Configuration", "EDIABAS"),
                    ini_get(ini, "EcuPath", "Configuration", "EDIABAS"),
                    ini_get(obd, "Port", "OBD"),
                ))
    if copies:
        print("  найденные установки (Interface и порт из их конфигов):")
        for here, interface, ecupath, port in copies:
            mark = " <-- активная" if os.path.normcase(os.path.abspath(str(here))) == \
                os.path.normcase(os.path.abspath(str(winner))) else ""
            print(f"    {here}{mark}")
            print(f"        Interface={interface or '?'}, Port={port or '?'}, "
                  f"EcuPath={ecupath or '?'}")
            if interface and interface.upper() != "STD:OBD" and not mark:
                warn(f"у {here} Interface={interface}: если этот каталог окажется "
                     f"в PATH раньше, K+DCAN перестанет работать")
    return winner.parent if winner.name.upper() == "BIN" else winner


def scan_firmware(roots: list[str], manifest: Path) -> None:
    """Манифест сверяется по хешу: имена в установке отличаются от наших."""
    head("Проприетарные файлы: поиск по хешу манифеста")
    table = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    by_size: dict[int, list[str]] = {}
    for name, meta in table.items():
        by_size.setdefault(meta["size"], []).append(name)

    found: dict[str, list[str]] = {}
    size_seen: set[int] = set()
    hashed = 0
    for root in roots:
        if not Path(root).exists():
            warn(f"каталог {root} не существует — пропущен")
            continue
        for dirpath, _dirs, filenames in os.walk(root):
            for fn in filenames:
                path = Path(dirpath) / fn
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size not in by_size:
                    continue
                hashed += 1
                size_seen.add(size)
                digest = sha256(path)
                for name in by_size[size]:
                    if table[name]["sha256"] == digest:
                        found.setdefault(name, []).append(str(path))

    say(OK, f"проверено по хешу: {hashed}; совпало записей: "
            f"{len(found)} из {len(table)}")
    for name in sorted(found):
        say(OK, f"{name} <- {found[name][0]}"
                + (f" (копий: {len(found[name])})" if len(found[name]) > 1 else ""))

    # Файл с нужным размером, но другим хешем — это другая версия/локализация,
    # а не отсутствие файла: путать их нельзя, выводы будут разные.
    other_version = [n for n in sorted(set(table) - set(found))
                     if table[n]["size"] in size_seen]
    absent = [n for n in sorted(set(table) - set(found))
              if table[n]["size"] not in size_seen]
    if other_version:
        warn(f"другой версии ({len(other_version)}): "
             + ", ".join(f"{n} ({table[n]['size']} Б)" for n in other_version))
        print("       Размер совпадает, содержимое — нет: на диске другая")
        print("       ревизия. Сверьтесь с docs/research, если опираетесь на них.")
    if absent:
        warn(f"отсутствует ({len(absent)}): {', '.join(absent)}")
        print("       Ищите их в установке SP-Daten/NCS/WinKFP и копируйте")
        print("       в local-firmware/ — после этого работает "
              "`python tools/check-firmware.py`")


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Проверка окружения EDIABAS/BMW Standard Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ediabas", help="каталог установки (по умолчанию C:\\EDIABAS)")
    ap.add_argument("--manifest", type=Path,
                    default=Path(__file__).resolve().parents[1] / "firmware-manifest.json",
                    help="манифест проприетарных файлов")
    ap.add_argument("--firmware-scan",
                    help="каталоги через запятую: искать файлы манифеста по хешу")
    args = ap.parse_args()

    print("Проверка окружения для чтения приборки BMW (KOMB87 / EDIABAS)")

    check_python()
    active = check_installations()
    root = find_ediabas(args.ediabas) or active
    ini, obd = check_ediabas(root)
    check_cable(obd, ini, root)
    check_sgdb(ini, root, args.manifest)
    check_tools(root)
    if args.firmware_scan:
        scan_firmware([r.strip() for r in args.firmware_scan.split(",") if r.strip()],
                      args.manifest)

    head("Итог")
    blocks = [t for s, t in problems if s == "bad"]
    warns = [t for s, t in problems if s == "warn"]
    if not blocks and not warns:
        print("  всё на месте — можно запускать "
              "`py -3-32 flasher/kombi_read_flash.py --ident`")
        return 0
    print(f"  критично: {len(blocks)}, предупреждений: {len(warns)}")
    for text in blocks:
        print(f"    X {text}")
    for text in warns:
        print(f"    ! {text}")
    if blocks:
        return 2
    print("\n  Предупреждения не мешают проверке на столе, но без кабеля "
          "`--ident` не пройдёт.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
