"""
Family-level comparison: what distinguishes the DKOML2 ("box") firmwares from
the HKOML2 ("no box") firmwares, as opposed to what merely distinguishes one
build from another.

Method. Every hardware part number is a separately compiled and linked build,
so a single DKOML2-vs-HKOML2 pair leaves hundreds of unmatched functions that
are just compile churn. Here each function is reduced to its operand-free
mnemonic-sequence signature (stable across relinking) and then scored by how
its presence tracks the FAMILY:

    a signature present in K of the 4 DKOML2 builds and M of the 9 HKOML2
    builds is family-discriminating when K/4 and M/9 are far apart.

A signature in 4/4 DKOML2 and 0/9 HKOML2 is a genuine box-family trait. A
signature in 2/4 and 1/9 is build noise. The control that makes this work is
the within-family comparison printed first: if DKOML2 builds disagree with
each other as much as they disagree with HKOML2, no conclusion is possible.

Usage:
    python3 f2mc_batch.py /tmp/fw DKOML2/*.0pa HKOML2/*.0pa
    python3 f2mc_family.py /tmp/fw
"""
import glob
import json
import os
import sys
from collections import defaultdict
from itertools import combinations


def load(outdir):
    fams = defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(outdir, "*.json"))):
        d = json.load(open(path))
        fams[d["family"]][d["variant"]] = d["functions"]
    return fams


def sigsets(variants):
    """variant -> set of signatures"""
    return {v: {f["signature"] for f in funcs.values()}
            for v, funcs in variants.items()}


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def main(argv):
    outdir = argv[1] if len(argv) > 1 else "/tmp/fw"
    fams = load(outdir)
    if len(fams) < 2:
        print(f"need two families in {outdir}, found: {list(fams)}")
        return 1

    D = sigsets(fams["DKOML2"])
    H = sigsets(fams["HKOML2"])
    print(f"DKOML2 (box):    {len(D)} variants, "
          f"{[len(s) for s in D.values()]} signatures")
    print(f"HKOML2 (no box): {len(H)} variants, "
          f"{[len(s) for s in H.values()]} signatures")

    # --- the control: is within-family agreement higher than across-family? --
    def pairstats(sets_a, sets_b=None):
        if sets_b is None:
            pairs = combinations(sets_a.values(), 2)
        else:
            pairs = ((x, y) for x in sets_a.values() for y in sets_b.values())
        vals = [jaccard(x, y) for x, y in pairs]
        return sum(vals) / len(vals), min(vals), max(vals)

    dd = pairstats(D)
    hh = pairstats(H)
    dh = pairstats(D, H)
    print("\nCONTROL -- signature-set Jaccard similarity (mean / min / max):")
    print(f"  DKOML2 vs DKOML2: {dd[0]:.3f}  ({dd[1]:.3f}-{dd[2]:.3f})")
    print(f"  HKOML2 vs HKOML2: {hh[0]:.3f}  ({hh[1]:.3f}-{hh[2]:.3f})")
    print(f"  DKOML2 vs HKOML2: {dh[0]:.3f}  ({dh[1]:.3f}-{dh[2]:.3f})")
    if dh[0] >= min(dd[0], hh[0]) - 0.01:
        print("  !! within-family agreement is NOT higher than across-family:")
        print("     family-level signal is too weak for the counts below to mean much.")
    else:
        print("  -> within-family agreement is higher: family signal is real.")

    # --- family-discriminating signatures ----------------------------------
    nd, nh = len(D), len(H)
    dcount = defaultdict(int)
    hcount = defaultdict(int)
    for s in D.values():
        for sig in s:
            dcount[sig] += 1
    for s in H.values():
        for sig in s:
            hcount[sig] += 1

    box_only = [sig for sig in dcount if dcount[sig] == nd and hcount.get(sig, 0) == 0]
    nobox_only = [sig for sig in hcount if hcount[sig] == nh and dcount.get(sig, 0) == 0]
    print("\nfamily-discriminating signatures (unanimous in one family, absent in the other):")
    print(f"  in ALL {nd} DKOML2 and NO HKOML2: {len(box_only)}")
    print(f"  in ALL {nh} HKOML2 and NO DKOML2: {len(nobox_only)}")

    # map signatures back to concrete functions in a reference variant
    def detail(sigs, variants, label, n=25):
        ref = sorted(variants)[0]
        funcs = variants[ref]
        bysig = defaultdict(list)
        for f in funcs.values():
            bysig[f["signature"]].append(f)
        rows = []
        for sig in sigs:
            for f in bysig.get(sig, []):
                rows.append(f)
        rows.sort(key=lambda f: -f["n_insns"])
        print(f"\n{label} (reference variant {ref}, {len(rows)} functions):")
        for f in rows[:n]:
            print(f"  0x{f['entry']:06X}  insns={f['n_insns']:<5} size={f['size']:<5} "
                  f"calls={len(f['calls']):<3} sig={f['signature']}")
        return rows

    box_rows = detail(box_only, fams["DKOML2"], "BOX-ONLY functions")
    nobox_rows = detail(nobox_only, fams["HKOML2"], "NOBOX-ONLY functions")

    with open(os.path.join(outdir, "family_result.json"), "w") as fh:
        json.dump({"box_only": box_rows, "nobox_only": nobox_rows,
                   "control": {"dd": dd, "hh": hh, "dh": dh}}, fh, indent=1)
    print(f"\nwrote {os.path.join(outdir, 'family_result.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
