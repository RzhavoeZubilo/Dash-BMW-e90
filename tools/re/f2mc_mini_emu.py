#!/usr/bin/env python3
"""Минимальный интерпретатор F2MC-16LX -- НЕ полный эмулятор процессора.

Покрывает только опкоды, реально встречающиеся в патчах этого проекта
(сейчас -- обработчик температуры ОЖ, см. docs/research/HANDOFF.md).
Семантика каждой инструкции взята из data/languages/F2MC.slaspec
(локальный клон Ghidra-спецификации, см. tools/F2MC-16LX/ в соседней
папке "прошивки приборок") и перепроверена вручную. Цель -- не
дизассемблировать прошивку (это делает f2mc_disasm.py), а ИСПОЛНИТЬ
небольшой написанный вручную фрагмент байт-кода и показать, что он
даёт ожидаемое состояние памяти/регистров, прежде чем прошивать его
в реальный чип. Если инструкция встретилась, а эмулятор её не знает --
он останавливается с явной ошибкой, а не угадывает поведение.
"""
from __future__ import annotations

import argparse


class Flags:
    __slots__ = ("Z", "N", "C", "V")

    def __init__(self) -> None:
        self.Z = self.N = self.C = self.V = 0


class CPU:
    """Регистровая модель: AL/AH (16-бит каждый, вместе -- 32-битный A для
    MULUW/DIVUW), RW0-RW7 (16-бит), плоская память как dict {адрес: байт}."""

    def __init__(self, mem: dict[int, int] | None = None) -> None:
        self.AL = 0
        self.AH = 0
        self.RW = [0] * 8
        self.flags = Flags()
        self.mem = mem if mem is not None else {}
        self.pc = 0
        self.trace: list[str] = []
        self.halted = False

    # ---- память: читаем/пишем явно, без скрытого угадывания ----
    def mb(self, addr: int) -> int:
        return self.mem.get(addr & 0xFFFFFF, 0xFF)  # 0xFF = типичное "стёрто"

    def mw(self, addr: int) -> int:
        return self.mb(addr) | (self.mb(addr + 1) << 8)

    def set_mb(self, addr: int, val: int) -> None:
        self.mem[addr & 0xFFFFFF] = val & 0xFF

    def set_mw(self, addr: int, val: int) -> None:
        self.set_mb(addr, val & 0xFF)
        self.set_mb(addr + 1, (val >> 8) & 0xFF)

    def A(self) -> int:
        return (self.AH << 16) | self.AL  # для MULUW -- "A" как 32-битный

    def zset(self, v: int, width: int = 16) -> None:
        self.flags.Z = 1 if (v & ((1 << width) - 1)) == 0 else 0

    def nset(self, v: int, width: int = 16) -> None:
        self.flags.N = 1 if (v >> (width - 1)) & 1 else 0

    def fetch(self, code: bytes, base: int, n: int) -> bytes:
        off = self.pc - base
        b = code[off:off + n]
        self.pc += n
        return b

    def step(self, code: bytes, base: int) -> None:
        off = self.pc - base
        if off < 0 or off >= len(code):
            raise RuntimeError(f"PC 0x{self.pc:06X} вне диапазона загруженного кода")
        op = code[off]
        start_pc = self.pc
        self.pc += 1

        if op == 0x6C:  # BBC/BBS addr16:bit, rel -- нужен только BBC (op1=4, mode=3)
            b2 = code[off + 1]
            op1 = (b2 >> 5) & 7
            mode = (b2 >> 3) & 3
            bit = b2 & 7
            if mode != 3:
                raise NotImplementedError("0x6C: только addr16-режим (mode=3) реализован")
            addr = code[off + 2] | (code[off + 3] << 8)
            self.pc = start_pc + 5
            val = self.mb(addr)
            bitval = (val >> bit) & 1
            rel = code[off + 4]
            rel = rel - 256 if rel >= 128 else rel
            target = base + ((self.pc - base + rel) & 0xFFFF)
            if op1 == 4:  # BBC: переход, если бит ОЧИЩЕН
                taken = bitval == 0
            elif op1 == 5:  # BBS: переход, если бит УСТАНОВЛЕН
                taken = bitval == 1
            else:
                raise NotImplementedError(f"0x6C op1={op1} не реализован")
            self.trace.append(
                f"{start_pc:06X}: {'BBC' if op1==4 else 'BBS'} [{addr:04X}]:{bit} "
                f"(bit={bitval}) -> {'переход' if taken else 'не переходим'}"
            )
            if taken:
                self.pc = target

        elif op == 0x52:  # MOV A, addr16
            addr = code[off + 1] | (code[off + 2] << 8)
            self.pc = start_pc + 3
            self.AL = self.mb(addr)
            self.zset(self.AL, 8)
            self.nset(self.AL, 8)
            self.trace.append(f"{start_pc:06X}: MOV A,[{addr:04X}] -> A=0x{self.AL:02X}")

        elif op == 0x2A:  # CBNE A, imm8, rel
            imm8 = code[off + 1]
            rel = code[off + 2]
            rel = rel - 256 if rel >= 128 else rel
            self.pc = start_pc + 3
            target = base + ((self.pc - base + rel) & 0xFFFF)
            taken = (self.AL & 0xFF) != imm8
            self.trace.append(
                f"{start_pc:06X}: CBNE A,0x{imm8:02X} (A=0x{self.AL:02X}) -> "
                f"{'переход' if taken else 'не переходим'}"
            )
            if taken:
                self.pc = target

        elif op == 0x4A:  # MOVW A, imm16
            imm16 = code[off + 1] | (code[off + 2] << 8)
            self.pc = start_pc + 3
            self.AL = imm16
            self.zset(self.AL)
            self.nset(self.AL)
            self.trace.append(f"{start_pc:06X}: MOVW A,0x{imm16:04X}")

        elif op == 0x39:  # SUBW A, imm16  (AL = AL - imm16, по спецификации)
            imm16 = code[off + 1] | (code[off + 2] << 8)
            self.pc = start_pc + 3
            res = (self.AL - imm16) & 0xFFFF
            self.flags.C = 1 if self.AL < imm16 else 0
            self.AL = res
            self.zset(self.AL)
            self.nset(self.AL)
            self.trace.append(f"{start_pc:06X}: SUBW A,0x{imm16:04X} -> A=0x{self.AL:04X}")

        elif 0xD0 <= op <= 0xDF:  # MOVN A, #imm4  (AH=AL; AL=imm)
            imm = op & 0xF
            self.pc = start_pc + 1
            self.AH = self.AL
            self.AL = imm
            self.flags.N = 0
            self.zset(self.AL)
            self.trace.append(f"{start_pc:06X}: MOVN A,#{imm} -> AH=0x{self.AH:04X} AL=0x{self.AL:04X}")

        elif op == 0x2F:  # MULUW A  (32-битный A = zext(AH) * zext(AL))
            self.pc = start_pc + 1
            prod = (self.AH & 0xFFFF) * (self.AL & 0xFFFF)
            self.AH = (prod >> 16) & 0xFFFF
            self.AL = prod & 0xFFFF
            self.trace.append(f"{start_pc:06X}: MULUW A -> AH:AL=0x{self.AH:04X}:{self.AL:04X} (={prod})")

        elif op == 0xCB:  # MOVW @RW3+d8, A
            d8 = code[off + 1]
            self.pc = start_pc + 2
            addr = frame_slot(self.RW[3], d8)
            self.set_mw(addr, self.AL)
            self.trace.append(
                f"{start_pc:06X}: MOVW @RW3+0x{d8:02X},A -> "
                f"mem[0x{addr:04X}]=0x{self.AL:04X}"
            )

        elif op == 0x60:  # BRA rel
            rel = code[off + 1]
            rel = rel - 256 if rel >= 128 else rel
            self.pc = start_pc + 2
            target = base + ((self.pc - base + rel) & 0xFFFF)
            self.trace.append(f"{start_pc:06X}: BRA -> 0x{target:06X}")
            self.pc = target

        elif op == 0x63:  # JMPP addr24
            addr = code[off + 1] | (code[off + 2] << 8) | (code[off + 3] << 16)
            self.pc = start_pc + 4
            self.trace.append(f"{start_pc:06X}: JMPP 0x{addr:06X}")
            self.pc = addr
            self.halted = True  # выходим из загруженного фрагмента -- дальше не наш код

        else:
            raise NotImplementedError(
                f"Опкод 0x{op:02X} по адресу 0x{start_pc:06X} не реализован в мини-эмуляторе"
            )


def frame_slot(rw3: int, d8: int) -> int:
    """Адрес `@RW3+d8` -- d8 ЗНАКОВЫЙ (F2MC.slaspec: `d8 = (0,7) signed;`).
    0xFE/0xFC и т.п. -- это -2/-4, а не +254/+252. Перепутать легко (сам
    так ошибся при первой версии проверочного кода ниже) -- отдельная
    функция, чтобы впредь эта арифметика не дублировалась и не плыла."""
    d8s = d8 - 256 if d8 >= 128 else d8
    return (rw3 + d8s) & 0xFFFFFF


def run(code: bytes, base: int, cpu: CPU, max_steps: int = 200) -> CPU:
    cpu.pc = base
    steps = 0
    while not cpu.halted and (cpu.pc - base) < len(code) and steps < max_steps:
        cpu.step(code, base)
        steps += 1
    if steps >= max_steps:
        raise RuntimeError("превышен лимит шагов -- похоже на бесконечный цикл")
    return cpu


COOLANT_HANDLER = bytes.fromhex(
    "6C98B92806"      # FB9FF0: BBC [0x28B9]:0, FB9FFB
    "523A41"          # FB9FF5: MOV A,[0x413A]
    "2AFF07"          # FB9FF8: CBNE A,0xFF, FBA002
    "4AFEFF"          # FB9FFB: MOVW A,0xFFFE           (.no_data)
    "CBFE"            # FB9FFE: MOVW @RW3+0xFE,A
    "600A"            # FBA000: BRA FBA00C
    "523A41"          # FBA002: MOV A,[0x413A]          (.have_data)
    "393000"          # FBA005: SUBW A,0x0030
    "DA"              # FBA008: MOVN A,#10
    "2F"              # FBA009: MULUW A
    "CBFE"            # FBA00A: MOVW @RW3+0xFE,A
    "D2"              # FBA00C: MOVN A,#2               (.common)
    "CBFC"            # FBA00D: MOVW @RW3+0xFC,A
    "63A599FE"        # FBA00F: JMPP 0xFE99A5
)
HANDLER_BASE = 0xFB9FF0


def make_cpu(raw_temp: int | None, valid: bool) -> CPU:
    cpu = CPU()
    cpu.RW[3] = 0x2000  # произвольная "рамка" -- в реальности адрес стека,
                         # для теста важны только смещения от неё
    cpu.set_mb(0x413A, raw_temp if raw_temp is not None else 0xFF)
    # [0x28B9] бит 0 = флаг валидности
    cur = cpu.mb(0x28B9)
    cpu.set_mb(0x28B9, (cur | 1) if valid else (cur & ~1))
    return cpu


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=lambda x: int(x, 0), default=0x74,
                     help="сырой байт [0x413A] (по умолчанию 0x74=116 -> 68°C)")
    ap.add_argument("--invalid", action="store_true",
                     help="смоделировать 'нет данных' (флаг валидности = 0)")
    ap.add_argument("--quiet", action="store_true", help="не печатать трассировку")
    args = ap.parse_args()

    cpu = make_cpu(args.raw, valid=not args.invalid)
    run(COOLANT_HANDLER, HANDLER_BASE, cpu)

    if not args.quiet:
        for line in cpu.trace:
            print(line)
        print()

    result_val = cpu.mw(frame_slot(cpu.RW[3], 0xFE))
    result_dec_flag = cpu.mw(frame_slot(cpu.RW[3], 0xFC))
    print(f"Итог: mem[@RW3+0xFE] = 0x{result_val:04X} ({result_val if result_val < 0x8000 else result_val-0x10000})")
    print(f"      mem[@RW3+0xFC] = 0x{result_dec_flag:04X} (2 = точка подавлена)")
    print(f"      PC после выхода из фрагмента = 0x{cpu.pc:06X} "
          f"({'верно, = 0xFE99A5' if cpu.pc == 0xFE99A5 else 'ОШИБКА, ожидался 0xFE99A5'})")

    if args.invalid or args.raw == 0xFF:
        # 0xFF -- это тоже "нет данных" (сигнал CAN не пришёл), даже если
        # флаг валидности не сброшен отдельно -- обработчик проверяет оба
        # условия (BBC по флагу, затем CBNE по 0xFF).
        ok = result_val == 0xFFFE
        print(f"Проверка 'нет данных': {'OK' if ok else 'ОШИБКА'} (ожидалось 0xFFFE)")
    else:
        expected_c = args.raw - 48
        expected_stored = (expected_c * 10) & 0xFFFF
        ok = result_val == expected_stored
        print(f"Проверка: raw=0x{args.raw:02X}={args.raw} -> {expected_c}°C x10 = {expected_stored} "
              f"({'OK' if ok else 'ОШИБКА'})")
    return 0 if ok and result_dec_flag == 2 and cpu.pc == 0xFE99A5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
