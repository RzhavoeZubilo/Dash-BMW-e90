"""
Dump a BMW KOMBI .0pa/.0ba Intel HEX file to a flat binary, for feeding into
a disassembler (f2mc_disasm.py) or into Ghidra/IDA as a raw image.

By default writes ONE contiguous file per requested address range, filling
undefined bytes with 0xFF (matches the erased-flash convention used in these
dumps -- see the file's own ";$VALUE_UNUSED_BYTE 0xFF" comment).

Usage:
    python3 dump_flat.py <in.0pa> <out.bin> [lo] [hi]

lo/hi default to the full min/max address range found in the file.
"""
import sys
from parse_ihex import parse_ihex


def dump_flat(in_path, out_path, lo=None, hi=None, fill=0xFF):
    mem, mn, mx = parse_ihex(in_path)
    lo = lo if lo is not None else mn
    hi = hi if hi is not None else mx
    with open(out_path, "wb") as f:
        f.write(bytes(mem.get(a, fill) for a in range(lo, hi)))
    return lo, hi


def parse_addr(s):
    return int(s, 16) if s.lower().startswith("0x") else int(s)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 dump_flat.py <in.0pa> <out.bin> [lo] [hi]")
        sys.exit(1)
    in_path, out_path = sys.argv[1], sys.argv[2]
    lo = parse_addr(sys.argv[3]) if len(sys.argv) > 3 else None
    hi = parse_addr(sys.argv[4]) if len(sys.argv) > 4 else None
    lo, hi = dump_flat(in_path, out_path, lo, hi)
    print(f"wrote {out_path}: 0x{lo:06X}-0x{hi:06X} ({hi-lo} bytes)")
