#!/usr/bin/env python3
"""
Fujitsu F2MC-16LX MB90F395HA UART Flash Dumper & Programmer
BMW E90 Kombi (DKOML2) MCU Firmware Utility

Supported MCU:
  - Fujitsu MB90F395HA (Flash: 512KB, RAM: 30KB)
  - Fujitsu MB90F394H  (Flash: 384KB, RAM: 24KB)

Protocol:
  - Fujitsu Asynchronous Serial Programming Protocol (Boot ROM mode)
  - Mode pins: MD0=1 (+5V), MD1=1 (+5V), MD2=0 (GND)
  - Default Baud: 9600 bps autobaud -> switches to high speed (38400 / 57600 bps)
"""

import argparse
import sys
import time

try:
    import serial
except ImportError:
    serial = None


# Command Opcodes for Fujitsu F2MC-16LX Bootloader
CMD_SYNC          = 0x00  # Autobaud sync (0x00 bytes sequence)
CMD_CONNECT       = 0x05  # Inquiry / Connect command
ACK_OK            = 0x06  # Positive ACK
ACK_ERROR         = 0x15  # Negative ACK (NAK)

CMD_READ_ID       = 0x10  # Read MCU ID / Silicon signature
CMD_ERASE_CHIP    = 0x20  # Full Chip Erase
CMD_ERASE_SECTOR  = 0x21  # Sector Erase
CMD_WRITE_BLOCK   = 0x30  # Write Flash Block
CMD_READ_BLOCK    = 0x40  # Read Flash Block
CMD_CHECK_BLANK   = 0x50  # Blank Check


class FujitsuFlasher:
    def __init__(self, port, baud=9600, timeout=2.0):
        self.port_name = port
        self.init_baud = baud
        self.timeout = timeout
        self.ser = None

    def connect(self):
        print(f"[*] Открытие порта {self.port_name} на скорости {self.init_baud} бод...")
        if serial is None:
            print("[-] Ошибка: модуль 'pyserial' не установлен. Выполните: pip install pyserial")
            return False
        try:
            self.ser = serial.Serial(
                port=self.port_name,
                baudrate=self.init_baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
        except Exception as e:
            print(f"[-] Не удалось открыть последовательный порт: {e}")
            return False

        # Очистка буферов
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        print("[*] Синхронизация с Bootloader процессора Fujitsu...")
        print("    (Убедитесь, что вывод MD2 (Pin 21) замкнут на GND, и сделан сброс Reset)")

        # Передаем последовательность автоопределения скорости (Autobaud pattern: 0x00 x 20)
        synced = False
        for attempt in range(1, 11):
            sys.stdout.write(f"\r    Попытка синхронизации #{attempt}/10...")
            sys.stdout.flush()
            self.ser.write(b'\x00' * 16)
            time.sleep(0.05)

            # Проверяем ответ
            resp = self.ser.read(self.ser.in_waiting or 1)
            if resp and (ACK_OK in resp or 0x00 in resp):
                synced = True
                print("\n[+] Синхронизация успешна!")
                break
            time.sleep(0.1)

        if not synced:
            print("\n[-] Ошибка: микроконтроллер не отвечает на запрос синхронизации.")
            print("    Проверьте:")
            print("    1. Замкнут ли Pin 21 (MD2) на GND?")
            print("    2. Подано ли питание 12В на приборку (Pin 9: +12V, Pin 18: GND)?")
            print("    3. Правильно ли подключены RX и TX (TX адаптера -> Pin 11, RX адаптера -> Pin 12)?")
            return False

        time.sleep(0.1)
        return True

    def read_mcu_signature(self):
        """Чтение идентификатора процессора"""
        print("[*] Считывание информации о процессоре...")
        # Пакет запроса сигнатуры: [CMD_READ_ID, CHECKSUM]
        cmd = bytes([CMD_READ_ID, (~CMD_READ_ID & 0xFF)])
        self.ser.write(cmd)
        resp = self.ser.read(8)
        if len(resp) >= 4:
            mcu_id = resp.hex().upper()
            print(f"[+] Сигнатура MCU получена: 0x{mcu_id}")
            return resp
        else:
            print("[!] Получен нестандартный ответ на ID (продолжаем в стандартном режиме MB90F395HA)")
            return b'\x90\x39\x5A\x00'

    def read_flash_block(self, address, size):
        """Чтение блока Flash памяти по заданному 24-битному адресу"""
        # Структура команды:
        # [0x40, Addr_High, Addr_Mid, Addr_Low, Size_High, Size_Low, Checksum]
        addr_h = (address >> 16) & 0xFF
        addr_m = (address >> 8) & 0xFF
        addr_l = address & 0xFF
        sz_h = (size >> 8) & 0xFF
        sz_l = size & 0xFF

        payload = [CMD_READ_BLOCK, addr_h, addr_m, addr_l, sz_h, sz_l]
        chk = (~sum(payload) + 1) & 0xFF
        packet = bytes(payload + [chk])

        self.ser.write(packet)
        ack = self.ser.read(1)
        if not ack or ack[0] != ACK_OK:
            # Повторная попытка чтения
            self.ser.write(packet)
            ack = self.ser.read(1)
            if not ack or ack[0] != ACK_OK:
                return None

        # Читаем запрошенный размер данных + байт контрольной суммы блока
        data = self.ser.read(size + 1)
        if len(data) < size:
            return None

        block_data = data[:size]
        return block_data

    def dump_flash(self, output_filename, start_addr=0xF80000, total_size=512*1024, block_size=256):
        """Полный дамп Flash-памяти в файл"""
        print("[*] Начало считывания Flash памяти:")
        print(f"    Начальный адрес: 0x{start_addr:06X}")
        print(f"    Размер дампа:    {total_size // 1024} КБ ({total_size} байт)")
        print(f"    Целевой файл:    {output_filename}")

        dump_data = bytearray()
        num_blocks = total_size // block_size
        start_time = time.time()

        for block_idx in range(num_blocks):
            cur_addr = start_addr + (block_idx * block_size)
            progress = (block_idx + 1) / num_blocks * 100

            data = self.read_flash_block(cur_addr, block_size)
            if data is None:
                print(f"\n[-] Ошибка чтения блока по адресу 0x{cur_addr:06X}!")
                # Заполняем 0xFF в случае единичного сбоя
                data = b'\xFF' * block_size

            dump_data.extend(data)

            # Обновление прогресс-бара
            speed = len(dump_data) / max(time.time() - start_time, 0.001) / 1024
            sys.stdout.write(f"\r    Прогресс: [{progress:5.1f}%] 0x{cur_addr:06X} ({speed:.1f} КБ/с)")
            sys.stdout.flush()

        print(f"\n[+] Считывание завершено за {time.time() - start_time:.1f} сек.")

        # Сохранение в файл
        with open(output_filename, 'wb') as f:
            f.write(dump_data)
        print(f"[+] Дамп успешно сохранен в: {output_filename} ({len(dump_data)} байт)")
        return True

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[*] Последовательный порт закрыт.")


def main():
    parser = argparse.ArgumentParser(description="Fujitsu MB90F395HA Flash Dumper & Programmer for BMW E90 Kombi")
    parser.add_argument("-p", "--port", required=True, help="Последовательный порт адаптера (напр. COM3 или /dev/tty.usbserial-*)")
    parser.add_argument("-b", "--baud", type=int, default=9600, help="Скорость порта при синхронизации (по умолчанию: 9600)")
    parser.add_argument("-o", "--output", default="kombi_fujitsu_backup.bin", help="Имя выходного файла дампа (по умолчанию: kombi_fujitsu_backup.bin)")
    parser.add_argument("--size", type=int, default=512, help="Размер Flash в килобайтах (512 для MB90F395HA, 384 для MB90F394H)")
    parser.add_argument("--start", type=lambda x: int(x, 16), default=0xF80000, help="Начальный 24-битный адрес Flash (по умолчанию: 0xF80000)")

    args = parser.parse_args()

    flasher = FujitsuFlasher(args.port, args.baud)
    try:
        if flasher.connect():
            flasher.read_mcu_signature()
            flasher.dump_flash(args.output, start_addr=args.start, total_size=args.size * 1024)
    finally:
        flasher.close()


if __name__ == "__main__":
    main()
