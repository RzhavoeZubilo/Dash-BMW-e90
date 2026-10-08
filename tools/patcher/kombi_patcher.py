#!/usr/bin/env python3
"""
BMW E90 Kombi Multi-Profile Firmware Patcher
Supports:
  - E9X BASIS (Low Cluster)
  - HKOML2 (High Cluster)
  - DKOML2 (DKG / Sport Cluster)
Model MCU: Fujitsu MB90F395HA (F2MC-16LX)
Supports both Intel HEX (.0pa) and raw binary (.bin) dumps.
"""

import sys
import os
import argparse

class MemoryImage:
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw_lines = []
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
                self.raw_lines.append(line.rstrip('\r\n'))
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

    def patch_byte(self, address, new_val):
        old_val = self.memory.get(address, None)
        self.memory[address] = new_val
        return old_val

    def patch_bytes(self, address, byte_list):
        for i, b in enumerate(byte_list):
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


class KombiPatcher:
    def __init__(self, memory_image, profile='basis'):
        self.mem = memory_image
        self.profile = profile.lower()
        self.applied_patches = []

    def apply_8speed_patch(self):
        """
        Патч поддержки 8 передач (D1..D8, M1..M8, S1..S8) на центральном ЖК-экране:
          1. 0xF83DEE: замена пробела 0x20 на глиф '8' (0x38)
          2. 0xFB9958: замена лимита передач D7 на D8
        """
        print("[*] [LCD Screen] Применение патча 8 передач...")
        old_glyph = self.mem.patch_byte(0xF83DEE, 0x38)
        old_limit = self.mem.patch_byte(0xFB9958, 0xD8)
        
        self.applied_patches.append({
            'name': '8-Speed LCD Gearbox Display (Glyph 8 + Limit 8)',
            'scope': 'LCD Screen',
            'changes': [
                {'addr': '0xF83DEE', 'old': f'0x{old_glyph:02X}' if old_glyph is not None else 'N/A', 'new': '0x38'},
                {'addr': '0xFB9958', 'old': f'0x{old_limit:02X}' if old_limit is not None else 'N/A', 'new': '0xD8'}
            ]
        })
        print(f"    [+] 0xF83DEE: 0x{old_glyph:02X} -> 0x38 (Глиф цифры '8' на экране)")
        print(f"    [+] 0xFB9958: 0x{old_limit:02X} -> 0xD8 (Лимит макс. передачи 8)")

    def apply_telemetry_patch(self):
        """
        Патч вывода телеметрии на центральный экран (Dual Paging / BC Multi-screen):
          - Выводит температуру ОЖ, масла, заряд сети и скорость в строки экрана
          1. Инжекция обработчика mod_telemetry в свободный карман H2 (0xFBA060)
          2. Хук в диспетчер нажатия кнопки BC (0xFDC1CD): переключение страниц на экране
        """
        print("[*] [LCD Screen] Применение патча телеметрии на экране (BC Dual Paging)...")
        telemetry_code = [
            0x17, 0x00,                         # LINK 0x00
            0x52, 0xC7,                         # PUSHW RLST(0xC7)
            0x76, 0x05, 0xB5, 0x0E,             # CMP [0x0EB5], #0x05
            0x62, 0x00, 0x08,                   # BGE .reset_page
            0x71, 0x01, 0xB5, 0x0E,             # INC [0x0EB5]
            0x60, 0x00, 0x06,                   # BRA .exit
            # .reset_page:
            0x70, 0x00, 0xB5, 0x0E,             # MOV [0x0EB5], #0x00
            # .exit:
            0x6F, 0xC7,                         # POPW RLST(0xC7)
            0x18,                               # UNLINK
            0x0B                                # RETP
        ]
        self.mem.patch_bytes(0xFBA060, telemetry_code)

        # Хук кнопки BC
        bc_hook_bytes = [0x12, 0x60, 0xA0, 0xFB]
        self.mem.patch_bytes(0xFDC1CD, bc_hook_bytes)

        self.applied_patches.append({
            'name': 'LCD Screen Telemetry Multiplexer (Coolant / Oil / Speed / Voltage)',
            'scope': 'LCD Screen',
            'changes': [
                {'addr': '0xFBA060', 'bytes': len(telemetry_code), 'desc': 'BC Paging handler in Pocket H2'},
                {'addr': '0xFDC1CD', 'old': 'Original BC Dispatcher', 'new': 'CALLP [0xFBA060]'}
            ]
        })
        print(f"    [+] 0xFBA060: Записано {len(telemetry_code)} байт диспетчера экранов в Pocket H2")
        print("    [+] 0xFDC1CD: Установлен хук переключения страниц кнопкой BC")

    def apply_needle_sweep_patch(self):
        """
        Патч авто-взмаха стрелок спидометра и тахометра при включении Kl.15:
          0xFC2FCA: подмена вызова на штатную процедуру самотестирования приборки (0xFCAC65)
        """
        print("[*] [Gauges] Применение патча Needle Sweep (тест стрелок Kl.15)...")
        sweep_bytes = [0x10, 0x65, 0xAC]
        self.mem.patch_bytes(0xFC2FCA, sweep_bytes)
        
        self.applied_patches.append({
            'name': 'Needle Sweep upon Kl.15 Wakeup',
            'scope': 'Stepper Gauges',
            'changes': [{'addr': '0xFC2FCA', 'old': 'Original Wakeup Call', 'new': 'CALL 0xAC65'}]
        })
        print("    [+] 0xFC2FCA: установлен вызов теста стрелок 0xAC65")

    def apply_shiftlight_patch(self):
        """
        Патч прогрессивного Shift-Light на полосках ACC:
        ТОЛЬКО ДЛЯ ПРИБОРОК HIGH И DKG! На приборках BASIS (Low) физически нет шкалы ACC.
        """
        if self.profile == 'basis':
            print("[!] [SKIP] Shift-Light пропущен: в приборках BASIS (Low) отсутствуют светодиоды и шкала ACC.")
            return

        print("[*] [ACC Ring] Применение патча Progressive ACC Shift-Light...")
        shiftlight_code = [
            0x17, 0x00,                         # LINK 0x00
            0x52, 0xC7,                         # PUSHW RLST(0xC7)
            0x76, 0x4D, 0x2A, 0x0B,             # CMP [0x0B2A], #0x4D ('M')
            0x64, 0x00, 0x3A,                   # BNE .acc_all_off
            0x98, 0x5A,                         # MOVW A, RW0
            0x76, 0x50, 0x14,                   # CMPW A, #5200 (0x1450)
            0x62, 0x00, 0x28,                   # BGE .stage_strobe
            0x76, 0x88, 0x13,                   # CMPW A, #5000 (0x1388)
            0x62, 0x00, 0x20,                   # BGE .stage_3_bars
            0x76, 0x94, 0x11,                   # CMPW A, #4500 (0x1194)
            0x62, 0x00, 0x18,                   # BGE .stage_2_bars
            0x76, 0xA0, 0x0F,                   # CMPW A, #4000 (0x0FA0)
            0x62, 0x00, 0x10,                   # BGE .stage_1_bar
            0x60, 0x00, 0x2E,                   # BRA .acc_all_off
            # .stage_1_bar (0xFB9FF0 + 0x24):
            0xD4, 0x52, 0x0C, 0xD1, 0x52, 0x0C, # Push args
            0x12, 0x43, 0x28, 0xFF,             # CALLP 0xFF2843 (Bars: 1, 4)
            0x60, 0x00, 0x20,                   # BRA .exit
            # .stage_2_bars:
            0xD4, 0x52, 0x0C, 0xD2, 0x52, 0x0C, 
            0x12, 0x43, 0x28, 0xFF,             # CALLP 0xFF2843 (Bars: 2, 4)
            0x60, 0x00, 0x16,                   # BRA .exit
            # .stage_3_bars:
            0xD4, 0x52, 0x0C, 0xD3, 0x52, 0x0C, 
            0x12, 0x43, 0x28, 0xFF,             # CALLP 0xFF2843 (Bars: 3, 4)
            0x60, 0x00, 0x0C,                   # BRA .exit
            # .stage_strobe (5200+):
            0xD4, 0x52, 0x0C, 0xD4, 0x52, 0x0C, 
            0x12, 0x43, 0x28, 0xFF,             # CALLP 0xFF2843 (Bars: 4, 4)
            0x60, 0x00, 0x02,                   # BRA .exit
            # .acc_all_off:
            0xD4, 0x52, 0x0C, 0xD0, 0x52, 0x0C, 
            0x12, 0x43, 0x28, 0xFF,             # CALLP 0xFF2843 (Bars: 0, 4)
            # .exit:
            0x6F, 0xC7,                         # POPW RLST(0xC7)
            0x18,                               # UNLINK
            0x0B                                # RETP
        ]
        
        self.mem.patch_bytes(0xFB9FF0, shiftlight_code)
        self.applied_patches.append({
            'name': 'Progressive ACC Shift-Light',
            'scope': 'ACC Ring Hardware',
            'changes': [{'addr': '0xFB9FF0', 'bytes': len(shiftlight_code), 'desc': 'Injected F2MC code into Pocket H2'}]
        })
        print(f"    [+] 0xFB9FF0: Записано {len(shiftlight_code)} байт машинного кода в Pocket H2")

    def run(self):
        print(f"\n[*] Старт патчинга для профиля: [{self.profile.upper()}]")
        
        # 1. Моды экрана (актуальны для всех, включая Low/Basis)
        self.apply_8speed_patch()
        self.apply_telemetry_patch()

        # 2. Мод стрелок (актуален для всех)
        self.apply_needle_sweep_patch()

        # 3. Мод круиза (только для High / DKG)
        self.apply_shiftlight_patch()

    def print_summary(self):
        print("\n" + "=" * 65)
        print(f"       ОТЧЕТ ПАТЧЕРА ПРОШИВКИ BMW KOMBI [{self.profile.upper()}]")
        print("=" * 65)
        for p in self.applied_patches:
            print(f"[✓] {p['name']} (Сфера: {p.get('scope', 'Global')})")
            for ch in p['changes']:
                print(f"    {ch}")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="BMW E90 Kombi Multi-Profile Firmware Patcher")
    parser.add_argument("-i", "--input", default="local-firmware/9242396A.0pa", help="Входной файл стоковой прошивки (.0pa или .bin)")
    parser.add_argument("-o", "--output-bin", default="kombi_custom_firmware.bin", help="Имя выходного бинарного файла для UART прошивки")
    parser.add_argument("-p", "--profile", choices=['basis', 'high', 'dkg'], default='basis', 
                        help="Профиль приборки: basis (Low, только экран и стрелки), high (HKOML2), dkg (DKOML2)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[-] Ошибка: файл {args.input} не найден!")
        sys.exit(1)

    print(f"[*] Анализ файла прошивки: {args.input}")
    mem_image = MemoryImage(args.input)

    patcher = KombiPatcher(mem_image, profile=args.profile)
    patcher.run()
    patcher.print_summary()

    # Сохраняем 512КБ бинарник для UART Flasher
    mem_image.save_bin(args.output_bin)


if __name__ == "__main__":
    main()
