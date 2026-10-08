"""
Batch-analyze every firmware variant of both cluster families.

Why this exists: comparing ONE DKOML2 image against ONE HKOML2 image cannot
separate "this differs because of the gear box feature" from "this differs
because it is a different compile". Each hardware part number is its own
build, so a single pair comparison leaves ~460 unmatched functions that are
mostly build noise.

The fix is a control group. Run every variant of both families, then keep only
functions whose presence/absence tracks the FAMILY rather than the build:
present in all/most DKOML2 (box) and absent from all HKOML2 (no box), or vice
versa. Differences that are merely per-build churn show up scattered across
variants within a family and get filtered out. See f2mc_family.py.

The code region is auto-detected per file rather than hardcoded, because
variants don't all lay memory out the same way: a 16KB block counts as code
when its byte entropy is high and its self-correlation at stride 16 is low
(tables and erased flash fail one or both).

Usage:
    python3 f2mc_batch.py <outdir> <file.0pa> [file.0pa ...]
"""
import json
import math
import os
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from f2mc_cfg import analyze, load_image, prologue_seeds, vct4_seeds

BLOCK = 0x4000


def _entropy(b):
    if not b:
        return 0.0
    c = Counter(b)
    n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def _stride16(b):
    if len(b) <= 16:
        return 1.0
    return sum(1 for i in range(len(b) - 16) if b[i] == b[i + 16]) / (len(b) - 16)


def code_blocks(data, defined):
    """Auto-detect code regions: dense (high entropy) and non-repetitive."""
    out = []
    for base in range(0, 0x1000000, BLOCK):
        if not defined[base]:
            continue
        b = bytes(data[a] for a in range(base, base + BLOCK) if defined[a])
        if len(b) < 0x800:
            continue
        if b.count(0xFF) / len(b) > 0.5:
            continue
        if _entropy(b) > 6.3 and _stride16(b) < 0.15:
            out.append((base, base + BLOCK))
    return out


def run_one(args):
    path, outdir = args
    name = os.path.splitext(os.path.basename(path))[0]
    family = os.path.basename(os.path.dirname(path))
    data, defined = load_image(path)

    blocks = code_blocks(data, defined)
    seeds = []
    for lo, hi in blocks:
        seeds += prologue_seeds(data, defined, lo, hi)
    for bank in sorted({lo >> 16 for lo, _ in blocks}):
        seeds += vct4_seeds(data, defined, bank)

    funcs = analyze(data, defined, seeds)

    # keep only call-confirmed entries inside a detected code block: the LINK
    # scan over-generates (a 0x08 byte mid-function looks like a prologue) and
    # recursion wanders into the data region, where data-as-code invents
    # large fake functions
    called = set()
    for f in funcs.values():
        called |= f.calls | f.tailcalls
    def in_code(a):
        return any(lo <= a < hi for lo, hi in blocks)

    out = {}
    for a, f in funcs.items():
        if a in called and in_code(a) and f.n_insns >= 3 and f.bad / f.n_insns < 0.15:
            out[f"{a:06X}"] = {
                "entry": a,
                "size": f.size,
                "n_insns": f.n_insns,
                "calls": sorted(f.calls),
                "signature": f.signature(),
                "shape": f.shape(),
                "mnemonics": f.mnemonics(),
            }

    dest = os.path.join(outdir, f"{family}_{name}.json")
    with open(dest, "w") as fh:
        json.dump({"path": path, "family": family, "variant": name,
                   "blocks": blocks, "functions": out}, fh)
    return f"{family}/{name}: {len(blocks)} code blocks, {len(out)} functions"


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    outdir, paths = argv[1], argv[2:]
    os.makedirs(outdir, exist_ok=True)
    with Pool(min(6, len(paths))) as pool:
        for line in pool.imap_unordered(run_one, [(p, outdir) for p in paths]):
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
