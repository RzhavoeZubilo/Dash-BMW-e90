#!/usr/bin/env python3
"""
BMW E90 VDO LCD Matrix Icon & Font Generator
Converts ASCII art / pixel maps to:
  1. C byte arrays (1 bit per pixel) for Fujitsu MB90F395HA ROM.
  2. Pure 1-bit Canvas pixel-drawing matrices for 1:1 hardware emulator.

ВАЖНО: это РЕКОНСТРУКЦИЯ по референсным фото реального щитка с кастомной
прошивкой Bimmerbit (не экстракция из ПЗУ оригинальной прошивки BMW -- тот
знакогенератор ещё не найден дизассемблером). Единственный источник истины
для actually используемых в проекте иконок -- JS-копии в
tools/ui_simulator/index.html (ICON_OIL/ICON_COOLANT/ICON_PUMP); этот файл
не синхронизируется с ними автоматически, обновляйте оба места вручную при
правках.
"""

# 1. Иконка температуры масла (9x9) -- перерисована по фото реального щитка
# (вертикальный штрих-стрелка над пунктирной волной), см. тот же массив
# в tools/ui_simulator/index.html::ICON_OIL. Прежняя версия (22x10,
# "канистра с ручкой и каплей") была собственной выдумкой без опоры на
# фото и выглядела нечитаемым пятном на реальном экране.
OIL_ICON_9x9 = [
    "....#....",
    "....#....",
    "....#....",
    "...###...",
    "....#....",
    ".........",
    ".#.#.#.#.",
    "#.#.#.#.#",
    "........."
]

# 2. Иконка температуры ОЖ (термометр, 5x9) -- упрощена по тому же фото,
# см. tools/ui_simulator/index.html::ICON_COOLANT.
COOLANT_ICON_5x9 = [
    "..#..",
    ".###.",
    ".#.#.",
    ".#.#.",
    ".#.#.",
    ".#.#.",
    "#####",
    "##.##",
    "#####"
]

# 3. Authentic BMW Fuel Pump / Gas Icon (14x16 pixels)
# Square pump body, nozzle hose on right with hook
GAS_PUMP_ICON_14x16 = [
    "...########...",
    "..##########..",
    "..##......##..",
    "..##.####.##..",
    "..##.####.###.",  # Hose nozzle
    "..##......#.##",
    "..##########.#",
    "..##......##.#",
    "..##......##.#",
    "..##......##.#",
    "..##......##.#",
    "..##......##.#",
    "..##......##.#",
    "..##......##.#",
    ".############.",
    "##############"
]

def print_js_matrix(name, grid):
    print(f"const {name} = [")
    for row in grid:
        bits = "".join("1" if c == "#" else "0" for c in row)
        print(f"  '{bits}',")
    print("];")

def ascii_to_bytes(grid):
    height = len(grid)
    width = len(grid[0])
    result = []

    for row in grid:
        row_bytes = []
        cur_byte = 0
        bit_idx = 0
        for char in row:
            if char == '#':
                cur_byte |= (1 << (7 - bit_idx))
            bit_idx += 1
            if bit_idx == 8:
                row_bytes.append(cur_byte)
                cur_byte = 0
                bit_idx = 0
        if bit_idx > 0:
            row_bytes.append(cur_byte)
        result.extend(row_bytes)
    return width, height, bytes(result)

def print_c_array(name, width, height, data):
    print(f"// {name}: {width}x{height} ({len(data)} bytes)")
    print(f"const uint8_t {name}[] = {{")
    for i in range(0, len(data), 8):
        chunk = data[i:i+8]
        hex_str = ", ".join(f"0x{b:02X}" for b in chunk)
        print(f"    {hex_str},")
    print("};")

def main():
    print("=== BMW E90 LCD Matrix Bitmaps ===")
    for name, icon in [("icon_oil_9x9", OIL_ICON_9x9),
                       ("icon_coolant_5x9", COOLANT_ICON_5x9),
                       ("icon_gas_14x16", GAS_PUMP_ICON_14x16)]:
        w, h, raw = ascii_to_bytes(icon)
        print_c_array(name, w, h, raw)
        print()

if __name__ == "__main__":
    main()
