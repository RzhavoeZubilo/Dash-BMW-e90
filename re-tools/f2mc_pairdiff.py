"""
Pair up family-discriminating functions and show exactly where they diverge.

f2mc_family.py reports functions that are unanimously present in one cluster
family and absent from the other. But its signature is an exact hash of the
whole mnemonic sequence, so a function that differs by a SINGLE instruction
lands in both "box-only" and "nobox-only" lists as two unrelated entries. The
symptom is obvious in its output: the two lists mirror each other, e.g. a
1497-instruction box function opposite a 1496-instruction nobox one.

Those near-identical pairs are the whole point -- a one-feature difference
like "draw a frame around the gear letter" should look like a small, isolated
edit inside an otherwise identical routine. This tool re-pairs the two lists
by sequence similarity and prints the differing region with context.

Candidates are ranked by how *isolated* the edit is: a high overall similarity
with few changed blocks beats a function that differs everywhere.

Usage:
    python3 f2mc_pairdiff.py /tmp/fw [--top 20] [--show 5]
"""
import json
import os
import sys
from difflib import SequenceMatcher


def best_match(src, pool):
    """Best sequence match for `src` among `pool`, with a length prefilter to
    keep the O(n*m) matcher off obviously hopeless candidates."""
    n = len(src["mnemonics"])
    best, best_ratio = None, 0.0
    for cand in pool:
        m = len(cand["mnemonics"])
        if not (0.85 * n <= m <= 1.18 * n + 4):
            continue
        sm = SequenceMatcher(None, src["mnemonics"], cand["mnemonics"],
                             autojunk=False)
        if sm.real_quick_ratio() <= best_ratio or sm.quick_ratio() <= best_ratio:
            continue
        r = sm.ratio()
        if r > best_ratio:
            best, best_ratio = cand, r
    return best, best_ratio


def diff_blocks(a, b):
    """Changed opcode blocks between two mnemonic sequences."""
    sm = SequenceMatcher(None, a, b, autojunk=False)
    return [op for op in sm.get_opcodes() if op[0] != "equal"]


def main(argv):
    outdir = argv[1] if len(argv) > 1 else "/tmp/fw"
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 20
    show = int(argv[argv.index("--show") + 1]) if "--show" in argv else 5

    res = json.load(open(os.path.join(outdir, "family_result.json")))
    box, nobox = res["box_only"], res["nobox_only"]
    print(f"pairing {len(box)} box-only against {len(nobox)} nobox-only functions\n")

    pairs = []
    for f in box:
        m, r = best_match(f, nobox)
        if m is None:
            continue
        blocks = diff_blocks(f["mnemonics"], m["mnemonics"])
        changed = sum(max(i2 - i1, j2 - j1) for _, i1, i2, j1, j2 in blocks)
        pairs.append({"box": f, "nobox": m, "ratio": r,
                      "blocks": blocks, "changed": changed})

    # most interesting = highly similar overall, but with a small, tight edit
    pairs.sort(key=lambda p: (-p["ratio"], p["changed"], len(p["blocks"])))

    print(f"{'box':>10} {'nobox':>10} {'sim':>6} {'insns':>6} {'chg':>5} {'blocks':>7}")
    for p in pairs[:top]:
        print(f"  0x{p['box']['entry']:06X} 0x{p['nobox']['entry']:06X} "
              f"{p['ratio']:6.4f} {p['box']['n_insns']:6} "
              f"{p['changed']:5} {len(p['blocks']):7}")

    print("\n" + "=" * 72)
    print("differing regions of the tightest candidates")
    print("=" * 72)
    for p in pairs[:show]:
        bm, nm = p["box"]["mnemonics"], p["nobox"]["mnemonics"]
        print(f"\n--- box 0x{p['box']['entry']:06X} ({len(bm)} insns) vs "
              f"nobox 0x{p['nobox']['entry']:06X} ({len(nm)} insns), "
              f"similarity {p['ratio']:.4f}, {len(p['blocks'])} changed block(s)")
        for tag, i1, i2, j1, j2 in p["blocks"]:
            ctx0 = max(0, i1 - 3)
            print(f"  @insn {i1}..{i2} ({tag})")
            for k in range(ctx0, i1):
                print(f"      ctx  {bm[k]}")
            for k in range(i1, i2):
                print(f"      BOX  {bm[k]}")
            for k in range(j1, j2):
                print(f"      NO   {nm[k]}")
            for k in range(i2, min(len(bm), i2 + 3)):
                print(f"      ctx  {bm[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
