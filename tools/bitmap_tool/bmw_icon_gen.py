#!/usr/bin/env python3
"""
BMW E90 VDO LCD Matrix Icon & Font Generator
Converts ASCII art or pixel maps to 1-bit monochrome byte arrays for Fujitsu MB90F395HA LCD Buffer.
"""

import sys

# Factory Stock Coolant Temp Icon (16x16 1-bit pixel map)
# Waves at bottom + vertical thermometer stem + bulb
COOLANT_ICON_16x16 = [
    "....######......",
    "...#......#.....",
    "...#.####.#.....",
    "...#.#..#.#.....",
    "...#.#..#.#.....",
    "...#.####.#.....",
    "...#.#..#.#.....",
    "...#.#..#.#.....",
    "..##.####.##....",
    ".#..........#...",
    ".#..######..#...",
    ".#..........#...",
    "..##########....",
    ".#.#..#.#..#.#..",
    "#...##...##...#.",
    "................"
]

# Factory Stock Oil Can Icon (20x14 1-bit pixel map)
OIL_CAN_ICON_20x14 = [
    "....................",
    "...............#....",
    "..............##....",
    "...#########.###....",
    "..#.........####....",
    "..#.........#..#....",
    "..#.........#..#....",
    "..#.........#..#....",
    "..#.........####....",
    "..#.........#.......",
    "..#.........#.......",
    "...#########........",
    "....#.....#.........",
    ".....#####.........."
]

# Factory Gas Pump / Tank Icon (14x16 1-bit pixel map)
GAS_PUMP_ICON_14x16 = [
    "....######....",
    "...#......#...",
    "...#.####.#.#.",
    "...#.####.##..",
    "...#......#...",
    "...#......#.#.",
    "...########.#.",
    "...#......#.#.",
    "...#......#.#.",
    "...#......#.#.",
    "...#......###.",
    "...#......#...",
    "...#......#...",
    "...########...",
    "..##########..",
    ".............."
]

def ascii_to_bytes(grid):
    height = len(grid)
    width = len(grid[0])
    bytes_per_row = (width + 7) // 8
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
    print("=== BMW E90 Matrix Icons Generator ===")
    for name, icon in [("icon_coolant_16x16", COOLANT_ICON_16x16),
                       ("icon_oil_20x14", OIL_CAN_ICON_20x14),
                       ("icon_gas_14x16", GAS_PUMP_ICON_14x16)]:
        w, h, raw = ascii_to_bytes(icon)
        print_c_array(name, w, h, raw)
        print()

if __name__ == "__main__":
    main()
