"""
Byte-level diff tool for two BMW KOMBI .0pa/.0ba Intel HEX firmware files.

Usage:
    python3 diff_hex.py <file_a.0pa> <file_b.0pa> [lo] [hi]

lo/hi are optional hex or decimal address bounds (default: full overlapping range).
"""
import sys
from parse_ihex import parse_ihex


def diff(path_a, path_b, lo=None, hi=None, label_a="A", label_b="B", verbose=True):
    mem_a, mn_a, mx_a = parse_ihex(path_a)
    mem_b, mn_b, mx_b = parse_ihex(path_b)
    lo = lo if lo is not None else max(mn_a, mn_b)
    hi = hi if hi is not None else min(mx_a, mx_b)

    diffs = []
    for addr in range(lo, hi):
        a = mem_a.get(addr)
        b = mem_b.get(addr)
        if a != b:
            diffs.append((addr, a, b))

    if verbose:
        total = hi - lo
        print(
            f"{label_a} vs {label_b}: range 0x{lo:X}-0x{hi:X}, "
            f"{len(diffs)}/{total} differing bytes ({100*len(diffs)/max(total,1):.2f}%)"
        )

    # group into contiguous runs
    runs = []
    cur = None
    for addr, a, b in diffs:
        if cur and addr == cur[0][-1] + 1:
            cur[0].append(addr)
            cur[1].append((a, b))
        else:
            if cur:
                runs.append(cur)
            cur = [[addr], [(a, b)]]
    if cur:
        runs.append(cur)

    run_ranges = [(addrs[0], addrs[-1], vals) for addrs, vals in runs]
    if verbose:
        print(f"  -> {len(run_ranges)} contiguous diff runs")
        for start, end, vals in run_ranges[:40]:
            print(f"   0x{start:06X}-0x{end:06X} (len={end-start+1})")
    return run_ranges


def parse_addr(s):
    return int(s, 16) if s.lower().startswith("0x") else int(s)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 diff_hex.py <a.0pa> <b.0pa> [lo] [hi]")
        sys.exit(1)
    a, b = sys.argv[1], sys.argv[2]
    lo = parse_addr(sys.argv[3]) if len(sys.argv) > 3 else None
    hi = parse_addr(sys.argv[4]) if len(sys.argv) > 4 else None
    diff(a, b, lo=lo, hi=hi)
