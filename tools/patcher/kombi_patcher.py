#!/usr/bin/env python3
"""
BMW E90 Kombi firmware patcher (Fujitsu MB90F395HA, F2MC-16LX).

Содержит ТОЛЬКО патчи, проверенные разбором (правило проекта: без догадок).
Сейчас это один патч -- температура ОЖ в режиме 0 BC-дисплея, байты и
обоснование: docs/research/HANDOFF.md, раздел «Итоговые байты обработчика»;
проверка исполнением: tools/re/f2mc_mini_emu.py.

Модули раннего черновика (8 передач, телеметрия, needle sweep, shift-light)
удалены 2026-10-24: в телеметрии и shift-light байты не являются валидным
кодом F2MC-16LX, needle sweep на 9283870A ничего не меняет, а на остальных
образах портит инструкцию, смысл 8 передач не подтверждён до конца.
Разбор -- HANDOFF.md, раздел «2026-10-24: аудит kombi_patcher.py».

Каждый патч перед записью сверяет ожидаемые исходные байты. Если хоть один
байт не совпал (другой образ, уже пропатченный образ) -- ничего не пишется
и выходной файл не создаётся.

Вход для записи результата -- только настоящий полный дамп приборки (.bin,
512 КБ, база 0xF80000), снятый по UART. Из .0pa файл не создаётся: в .0pa нет
загрузчика (0xFFBFF0-0xFFFFFF) и участка 0xFB9FF0-0xFBBFFF, который на живом
дампе E71 (той же платформы) занят кодом загрузчика; образ из .0pa, залитый
целиком, стёр бы загрузчик. .0pa годится только для проверки патча (тесты).
"""

import sys
import os
import argparse


class PatchError(Exception):
    pass


class MemoryImage:
    def __init__(self, filepath):
        self.filepath = filepath
        self.memory = {}
        self.is_bin = False
        self.load()

    def load(self):
        # Check if file is raw binary (512KB) or Intel HEX (.0pa)
        with open(self.filepath, 'rb') as f:
            first_byte = f.read(1)

        if first_byte != b':' and first_byte != b';':
            # It's a raw binary dump
            self.is_bin = True
            with open(self.filepath, 'rb') as f:
                data = f.read()
            base_address = 0xF80000
            for i, b in enumerate(data):
                self.memory[base_address + i] = b
            print(f"[+] Загружен бинарный дамп: {self.filepath} ({len(data)} байт, база 0x{base_address:06X})")
            return

        # It's Intel HEX (.0pa)
        base_address = 0
        with open(self.filepath, 'r', errors='ignore') as f:
            for line in f:
                line_str = line.strip()
                if not line_str.startswith(':'):
                    continue
                rec_len = int(line_str[1:3], 16)
                addr = int(line_str[3:7], 16)
                rec_type = int(line_str[7:9], 16)
                data_hex = line_str[9:9 + rec_len * 2]

                if rec_type == 0:  # Data
                    phys = base_address + addr
                    for i in range(rec_len):
                        self.memory[phys + i] = int(data_hex[i*2:(i+1)*2], 16)
                elif rec_type == 4:  # Extended Linear Address
                    base_address = int(data_hex, 16) << 16
                elif rec_type == 2:  # Extended Segment Address
                    base_address = int(data_hex, 16) << 4
        print(f"[+] Загружен образ .0pa (Intel HEX): {self.filepath} (байт в памяти: {len(self.memory)})")

    def read_bytes(self, address, n, fill=0xFF):
        # неописанные в .0pa байты -- стёртая flash (0xFF), как и в save_bin
        return bytes(self.memory.get(address + i, fill) for i in range(n))

    def patch_bytes(self, address, data):
        for i, b in enumerate(data):
            self.memory[address + i] = b

    def save_bin(self, output_filepath, start_addr=0xF80000, size=512*1024):
        """Export contiguous 512KB binary for direct UART Flasher"""
        buf = bytearray(b'\xFF' * size)
        for offset in range(size):
            addr = start_addr + offset
            if addr in self.memory:
                buf[offset] = self.memory[addr]
        with open(output_filepath, 'wb') as f:
            f.write(buf)
        print(f"[+] Экспорт бинарного файла: {output_filepath} ({len(buf)} байт)")


class Patch:
    """
    checks -- [(addr, bytes)]: байты, от которых патч зависит, но не меняет.
    writes -- [(addr, old, new)]: что перезаписывается; old сверяется до записи.
    """
    def __init__(self, name, firmware, checks, writes):
        self.name = name
        self.firmware = firmware
        self.checks = checks
        self.writes = writes

    def verify(self, mem):
        problems = []
        expected = [(a, b) for a, b in self.checks] + [(a, old) for a, old, _ in self.writes]
        for addr, want in expected:
            got = mem.read_bytes(addr, len(want))
            if got != want:
                problems.append(f"0x{addr:06X}: ожидалось {want.hex(' ')}, в образе {got.hex(' ')}")
        return problems

    def apply(self, mem):
        problems = self.verify(mem)
        if problems:
            raise PatchError(
                f"{self.name}: образ не совпадает с {self.firmware}, ничего не записано\n    "
                + "\n    ".join(problems))
        for addr, _, new in self.writes:
            mem.patch_bytes(addr, new)


# Обработчик режима 0 BC-дисплея: температура ОЖ (°C x10) в @RW3-2, флаг
# подавления точки = 2 в @RW3-4, выход JMPP 0xFE99A5 (общий хвост диспетчера).
# Байты -- побайтно из таблицы HANDOFF.md «Итоговые байты обработчика».
COOLANT_HANDLER_ADDR = 0xFB9FF0
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

# Старое начало дефолт-обработчика режима 0 (единственная ссылка на него --
# JMP 0xFE996C в 0xFE97DB) заменяется дальним переходом в банк 0xFB.
COOLANT_HOOK_ADDR = 0xFE996C
COOLANT_HOOK = bytes.fromhex("63F09FFB")            # JMPP 0xFB9FF0
COOLANT_HOOK_OLD = bytes.fromhex("571016F1")        # MOVW A,[0x1610]; BNZ (1-й байт)

COOLANT_PATCH = Patch(
    name="Coolant temperature on BC display (mode 0)",
    firmware="9213308A (DKOML2)",
    checks=[
        (0xFE97DB, bytes.fromhex("626C99")),        # JMP 0xFE996C в диспетчере 0xFE979E
        (0xFE99A5, bytes.fromhex("7293F6")),        # MOV A,@RW3-0x0A -- цель JMPP на выходе
    ],
    writes=[
        (COOLANT_HOOK_ADDR, COOLANT_HOOK_OLD, COOLANT_HOOK),
        (COOLANT_HANDLER_ADDR, b'\xFF' * len(COOLANT_HANDLER), COOLANT_HANDLER),
    ],
)

PATCHES = [COOLANT_PATCH]


def apply_all(mem, patches=PATCHES):
    """Сначала проверяет все патчи, потом пишет -- либо все, либо ничего."""
    problems = []
    for p in patches:
        problems += [f"{p.name}: {x}" for x in p.verify(mem)]
    if problems:
        raise PatchError("образ не подходит, ничего не записано:\n    " + "\n    ".join(problems))
    for p in patches:
        p.apply(mem)
        print(f"[✓] {p.name} [{p.firmware}]")
        for addr, _, new in p.writes:
            print(f"    0x{addr:06X}: {len(new)} байт")


LOADER_START, FLASH_END = 0xFFBFF0, 0x1000000


def full_dump_problem(mem):
    """Пояснение, почему вход нельзя превращать в образ для заливки, или None."""
    if not mem.is_bin:
        return "Вход -- .0pa, а не дамп: в нём нет загрузчика."
    if len(mem.memory) != 512 * 1024:
        return f"Дамп должен быть ровно 512 КБ, а в нём {len(mem.memory)} байт."
    if all(mem.memory[a] == 0xFF for a in range(LOADER_START, FLASH_END)):
        return "Область загрузчика 0xFFBFF0-0xFFFFFF пустая -- это не полный дамп."
    return None


def main():
    parser = argparse.ArgumentParser(description="BMW E90 Kombi firmware patcher (только проверенные патчи)")
    parser.add_argument("-i", "--input", required=True, help="полный дамп приборки по UART (.bin, 512 КБ)")
    parser.add_argument("-o", "--output-bin", default="kombi_custom_firmware.bin", help="Имя выходного бинарного файла для UART прошивки")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[-] Ошибка: файл {args.input} не найден!")
        sys.exit(1)

    mem_image = MemoryImage(args.input)
    problem = full_dump_problem(mem_image)
    if problem:
        print(f"[-] {problem} Выходной файл не создан.")
        sys.exit(1)
    try:
        apply_all(mem_image)
    except PatchError as e:
        print(f"[-] {e}")
        sys.exit(1)

    # Сохраняем 512КБ бинарник для UART Flasher
    mem_image.save_bin(args.output_bin)


if __name__ == "__main__":
    main()
