"""
Structural comparison of two KOMBI firmware images (DKOML2 "box" vs HKOML2
"no box"), working from the JSON function tables produced by f2mc_cfg.py.

Byte-level diffing is useless here: every hardware part number is a separately
compiled and linked build, so ~80% of bytes differ even between two firmwares
that behave identically. This compares *structure* instead -- the mnemonic-only
instruction sequence of each function, which survives relinking because it
drops all absolute addresses and immediates.

Two filters make the result trustworthy:

  * confirmed entries only. f2mc_cfg.py seeds on every `LINK #imm8` byte, which
    over-generates: a 0x08 byte inside a real function's body looks like a
    prologue and yields a bogus "function" that is really a suffix of its
    neighbour (that's why raw output shows clusters like 0xFA05A9 / 0xFA05D1 /
    0xFA05D9 all a few bytes apart with near-identical sizes). A function is
    kept only if some other function actually CALLs its entry address, or if it
    came from a CALL-vector table.

  * code region only. Recursive descent follows calls wherever they lead,
    including into the 0xF80000-0xF9BFFF table/data region, where walking data
    as code invents large fake functions. Entries outside the code region are
    dropped.

Usage:
    python3 f2mc_cfg.py DKOML2/9213308A.0pa --range 0xF9C000,0xFF0000 --json dk.json
    python3 f2mc_cfg.py HKOML2/9168320A.0pa --range 0xF9C000,0xFF0000 --json hk.json
    python3 f2mc_compare.py dk.json hk.json [--code-lo 0xF9C000] [--code-hi 0xFF0000]
"""
import json
import sys
from collections import defaultdict

CODE_LO = 0xF9C000
CODE_HI = 0xFF0000


def load(path, lo, hi):
    raw = json.load(open(path))
    funcs = {v["entry"]: v for v in raw.values()}
    called = set()
    for f in funcs.values():
        called.update(f["calls"])
        called.update(f["tailcalls"])
    keep = {a: f for a, f in funcs.items()
            if lo <= a < hi and a in called}
    return funcs, keep


def index_by(keep, field):
    idx = defaultdict(list)
    for f in keep.values():
        idx[f[field] if field != "shape" else tuple(f["shape"])].append(f)
    return idx


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    lo = int(argv[argv.index("--code-lo") + 1], 0) if "--code-lo" in argv else CODE_LO
    hi = int(argv[argv.index("--code-hi") + 1], 0) if "--code-hi" in argv else CODE_HI

    all_d, dk = load(argv[1], lo, hi)
    all_h, hk = load(argv[2], lo, hi)

    print(f"code region 0x{lo:06X}-0x{hi:06X}")
    print(f"  {argv[1]}: {len(all_d)} raw -> {len(dk)} call-confirmed")
    print(f"  {argv[2]}: {len(all_h)} raw -> {len(hk)} call-confirmed")

    dsig, hsig = index_by(dk, "signature"), index_by(hk, "signature")
    shared = set(dsig) & set(hsig)
    nd = sum(len(dsig[s]) for s in shared)
    nh = sum(len(hsig[s]) for s in shared)
    print("\nexact mnemonic-sequence match:")
    print(f"  shared signatures: {len(shared)}")
    print(f"  matched: {nd}/{len(dk)} ({100*nd/max(1,len(dk)):.1f}%) DK, "
          f"{nh}/{len(hk)} ({100*nh/max(1,len(hk)):.1f}%) HK")

    only_d = [f for s in set(dsig) - set(hsig) for f in dsig[s]]
    only_h = [f for s in set(hsig) - set(dsig) for f in hsig[s]]
    print(f"  unmatched: {len(only_d)} DK-only, {len(only_h)} HK-only")

    # Second pass over the unmatched: a near-match by coarse shape means "same
    # function, small edit" -- exactly what a one-feature difference looks like.
    hshape = index_by({f["entry"]: f for f in only_h}, "shape")
    near, novel = [], []
    for f in only_d:
        cands = hshape.get(tuple(f["shape"]), [])
        (near if cands else novel).append(f)
    print(f"\n  of the DK-only: {len(near)} have a same-shape HK counterpart "
          f"(likely same function, small edit),")
    print(f"                  {len(novel)} have no shape counterpart at all")

    def show(label, fs, n=15):
        print(f"\n{label}")
        for f in sorted(fs, key=lambda x: -x["n_insns"])[:n]:
            print(f"  0x{f['entry']:06X}  insns={f['n_insns']:<5} "
                  f"size={f['size']:<5} calls={len(f['calls']):<3} "
                  f"sig={f['signature']}")

    show("largest DK-only functions with NO shape counterpart in HK:", novel)
    show("largest DK-only functions WITH a same-shape HK counterpart:", near)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
