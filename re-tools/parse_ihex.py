"""
Intel HEX parser for BMW KOMBI (Siemens VDO PL2) flash exchange files (.0pa/.0ba).

These files are plain ASCII Intel HEX (records starting with ':'), no encryption
at the container level. Use this to reconstruct a sparse memory map {address: byte}
from a .0pa/.0ba file for further analysis (diffing, disassembly, etc).

Usage:
    python3 parse_ihex.py <file.0pa>

As a library:
    from parse_ihex import parse_ihex
    mem, min_addr, max_addr = parse_ihex("path/to/file.0pa")
"""
import sys


def parse_ihex(path):
    """Parse an Intel HEX file (ASCII, possibly with BMW/Siemens comment lines
    starting with ';' before the real records) and return:
        mem: dict {absolute_address: byte_value}
        min_addr, max_addr: bounds of the addresses seen (max_addr is exclusive-ish,
                             i.e. last_address_written + 1)
    Supports record types 00 (data), 01 (EOF), 02 (extended segment address),
    04 (extended linear address). Other record types are ignored.
    """
    mem = {}
    ext_addr = 0
    max_addr = 0
    min_addr = None
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line.startswith(":"):
                continue
            try:
                data = bytes.fromhex(line[1:])
            except ValueError:
                continue
            if len(data) < 5:
                continue
            length = data[0]
            addr = (data[1] << 8) | data[2]
            rectype = data[3]
            payload = data[4 : 4 + length]
            if rectype == 0x00:  # data record
                full_addr = ext_addr + addr
                for i, b in enumerate(payload):
                    mem[full_addr + i] = b
                if full_addr + length > max_addr:
                    max_addr = full_addr + length
                if min_addr is None or full_addr < min_addr:
                    min_addr = full_addr
            elif rectype == 0x04:  # extended linear address (upper 16 bits << 16)
                ext_addr = (payload[0] << 24) | (payload[1] << 16)
            elif rectype == 0x02:  # extended segment address (segment << 4)
                ext_addr = ((payload[0] << 8) | payload[1]) << 4
            elif rectype == 0x01:  # EOF
                break
    return mem, min_addr, max_addr


def get_segments(mem):
    """Return list of (start, end) inclusive address ranges of contiguous defined bytes."""
    addrs = sorted(mem.keys())
    if not addrs:
        return []
    segs = []
    start = addrs[0]
    prev = addrs[0]
    for a in addrs[1:]:
        if a != prev + 1:
            segs.append((start, prev))
            start = a
        prev = a
    segs.append((start, prev))
    return segs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 parse_ihex.py <file.0pa>")
        sys.exit(1)
    path = sys.argv[1]
    mem, mn, mx = parse_ihex(path)
    print(f"{path}: {len(mem)} bytes defined, addr range 0x{mn:X} - 0x{mx:X}")
    print(f"segments ({len(get_segments(mem))}):")
    for s, e in get_segments(mem):
        print(f"  0x{s:06X} - 0x{e:06X}  (len={e - s + 1})")
