"""Байты патча ОЖ сверяются с HANDOFF.md («Итоговые байты обработчика»),
а сам обработчик прогоняется через f2mc_mini_emu уже из пропатченного образа."""
from pathlib import Path

import pytest

import f2mc_mini_emu as emu
import kombi_patcher as kp
from f2mc_disasm import disassemble

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASE = 0xF80000
SIZE = 512 * 1024

# Дословно из таблицы HANDOFF.md, адрес -> байты
HANDOFF_HANDLER = [
    (0xFB9FF0, "6C 98 B9 28 06"),
    (0xFB9FF5, "52 3A 41"),
    (0xFB9FF8, "2A FF 07"),
    (0xFB9FFB, "4A FE FF"),
    (0xFB9FFE, "CB FE"),
    (0xFBA000, "60 0A"),
    (0xFBA002, "52 3A 41"),
    (0xFBA005, "39 30 00"),
    (0xFBA008, "DA"),
    (0xFBA009, "2F"),
    (0xFBA00A, "CB FE"),
    (0xFBA00C, "D2"),
    (0xFBA00D, "CB FC"),
    (0xFBA00F, "63 A5 99 FE"),
]
HANDOFF_HOOK = (0xFE996C, "63 F0 9F FB")


def stock_like_image(tmp_path, overrides=()):
    """Синтетический 512 КБ образ: 0xFF везде, кроме байт, которые патч сверяет."""
    buf = bytearray(b"\xFF" * SIZE)
    for addr, data in [(0xFE97DB, "62 6C 99"), (0xFE99A5, "72 93 F6"),
                       (0xFE996C, "57 10 16 F1"), *overrides]:
        b = bytes.fromhex(data)
        buf[addr - BASE:addr - BASE + len(b)] = b
    f = tmp_path / "stock.bin"
    f.write_bytes(bytes(buf))
    return kp.MemoryImage(str(f))


def test_handler_bytes_match_handoff():
    expected = b"".join(bytes.fromhex(h) for _, h in HANDOFF_HANDLER)
    assert kp.COOLANT_HANDLER_ADDR == HANDOFF_HANDLER[0][0]
    assert kp.COOLANT_HANDLER == expected
    assert len(kp.COOLANT_HANDLER) == 35
    # тот же код, что проверен интерпретатором
    assert kp.COOLANT_HANDLER == emu.COOLANT_HANDLER


def test_handler_instruction_boundaries_match_handoff():
    listing = disassemble(kp.COOLANT_HANDLER, base_addr=kp.COOLANT_HANDLER_ADDR)
    assert [(a, raw) for a, _, raw, _ in listing] == \
        [(a, h.replace(" ", "").lower()) for a, h in HANDOFF_HANDLER]
    assert listing[-1][3] == "JMPP [0xFE99A5]"


def test_hook_bytes_match_handoff():
    addr, h = HANDOFF_HOOK
    assert kp.COOLANT_HOOK_ADDR == addr
    assert kp.COOLANT_HOOK == bytes.fromhex(h)
    (_, length, _, text), = disassemble(kp.COOLANT_HOOK, base_addr=addr)
    assert (length, text) == (4, "JMPP [0xFB9FF0]")


def test_apply_writes_exactly_39_bytes(tmp_path):
    assert sum(len(new) for _, _, new in kp.COOLANT_PATCH.writes) == 39
    mem = stock_like_image(tmp_path)
    before = dict(mem.memory)
    kp.apply_all(mem)
    changed = [a for a in mem.memory if mem.memory[a] != before.get(a)]
    # 39 записанных байт, из них два (в «2A FF 07» и «4A FE FF») совпадают со стёртой flash
    assert len(changed) == 37
    assert all(0xFE996C <= a < 0xFE9970 or 0xFB9FF0 <= a < 0xFBA013 for a in changed)
    assert mem.read_bytes(0xFE996C, 4) == bytes.fromhex(HANDOFF_HOOK[1])
    assert mem.read_bytes(0xFB9FF0, 35) == kp.COOLANT_HANDLER


@pytest.mark.parametrize("raw,expected", [(0x74, 680), (0x30, 0), (0x00, -480), (0xC8, 1520)])
def test_patched_image_runs_in_emulator(tmp_path, raw, expected):
    mem = stock_like_image(tmp_path)
    kp.apply_all(mem)
    code = mem.read_bytes(kp.COOLANT_HANDLER_ADDR, len(kp.COOLANT_HANDLER))
    cpu = emu.run(code, kp.COOLANT_HANDLER_ADDR, emu.make_cpu(raw, valid=True))
    assert cpu.mw(emu.frame_slot(cpu.RW[3], 0xFE)) == expected & 0xFFFF
    assert cpu.mw(emu.frame_slot(cpu.RW[3], 0xFC)) == 2
    assert cpu.pc == 0xFE99A5


@pytest.mark.parametrize("override", [
    (0xFE996C, "63 F0 9F FB"),   # уже пропатчен
    (0xFE97DB, "62 00 00"),      # диспетчер ведёт не туда
    (0xFBA010, "00"),            # карман занят
])
def test_refuses_mismatching_image_and_writes_nothing(tmp_path, override):
    mem = stock_like_image(tmp_path, overrides=[override])
    before = dict(mem.memory)
    with pytest.raises(kp.PatchError):
        kp.apply_all(mem)
    assert mem.memory == before


def test_no_draft_modules_left():
    # модули черновика с невалидным кодом F2MC-16LX не должны вернуться молча
    assert kp.PATCHES == [kp.COOLANT_PATCH]
    src = Path(kp.__file__).read_text(encoding="utf-8")
    for name in ("apply_shiftlight_patch", "apply_telemetry_patch",
                 "apply_needle_sweep_patch", "apply_8speed_patch"):
        assert name not in src


def _local(name):
    p = REPO_ROOT / "local-firmware" / name
    if not p.exists():
        pytest.skip(f"нет local-firmware/{name} (образы не в репозитории)")
    return kp.MemoryImage(str(p))


def test_applies_to_real_9213308A():
    mem = _local("9213308A.0pa")
    kp.apply_all(mem)
    assert mem.read_bytes(0xFB9FF0, 35) == kp.COOLANT_HANDLER


@pytest.mark.parametrize("name", ["9242396A.0pa", "9242397A.0pa", "9283870A.0pa"])
def test_refuses_other_real_images(name):
    mem = _local(name)
    with pytest.raises(kp.PatchError):
        kp.apply_all(mem)


def test_refuses_to_build_image_from_0pa_or_blank_loader(tmp_path):
    hexfile = tmp_path / "x.0pa"
    hexfile.write_text(":02000004 00F8 02\n".replace(" ", "") + ":00000001FF\n")
    assert "0pa" in kp.full_dump_problem(kp.MemoryImage(str(hexfile)))
    short = tmp_path / "short.bin"
    short.write_bytes(b"\xFF" * 1024)
    assert "512" in kp.full_dump_problem(kp.MemoryImage(str(short)))
    blank = tmp_path / "blank.bin"
    blank.write_bytes(b"\x00" * (512 * 1024 - 0x4010) + b"\xFF" * 0x4010)
    assert "загрузчика" in kp.full_dump_problem(kp.MemoryImage(str(blank)))
    ok = tmp_path / "ok.bin"
    ok.write_bytes(b"\x00" * (512 * 1024))
    assert kp.full_dump_problem(kp.MemoryImage(str(ok))) is None
