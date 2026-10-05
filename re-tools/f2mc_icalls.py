"""
Resolve indirect calls through pointer tables, so the call graph stops dead-ending.

The recursive-descent walker in f2mc_cfg.py follows only direct CALL/CALLP. Real
dispatch in this firmware goes through pointer tables in the data region, so a
walk from main() reaches ~16 functions and stops. This module finds those tables
and expands them into extra entry points.

The idiom (seen at 0xFC8CAD, dispatching on the config value DIR[0x71]):

    MOV  A, DIR[0x71]        ; index
    ZEXTW
    MOV  R0,0x01 ; LSLL A,R0 ; index *= 2  (16-bit entries)
    ADDL A, 0x00F84084       ; <- table base as a 32-bit immediate
    MOVL RL2,A
    MOVW A,@RL2+0x00         ; load the entry
    MOVW RW4,A
    CALL RW4                 ; indirect call

So: an `ADDL A,#imm32` whose immediate lands in the data region, followed
within a short window by an indirect `CALL`/`JMP` through a register, marks a
function-pointer table. Entries are 16-bit and live in the *code* bank of the
referencing instruction (CALL through a register uses PCB).

Table length is not encoded anywhere, so entries are read until one fails to
look like a function start -- that over- rather than under-reads, and bogus
targets are dropped later by the quality filter in f2mc_cfg.

Usage:
    python3 f2mc_icalls.py <file.0pa> [--expand] [--find-writes 0x09FB,0x0171]
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))

from f2mc_cfg import analyze, load_image, prologue_seeds, walk_function
from f2mc_disasm import disasm_one

DATA_LO, DATA_HI = 0xF80000, 0xF9C000
CODE_LO, CODE_HI = 0xF90000, 0xFF0000


def is_indirect_call(data, a):
    """CALL earw / CALLP earl / JMP earw / JMPP earl (the 0x70-block forms)."""
    op = data[a]
    if op not in (0x71, 0x73):
        return False
    h3 = (data[a + 1] >> 5) & 0x7
    return h3 in (0, 1)


def find_tables(data, defined, valid):
    """Locate pointer tables: `ADDL A,#imm32` into the data region, followed by
    an indirect call/jump within a short window."""
    va = sorted(valid)
    idx = {a: i for i, a in enumerate(va)}
    tables = {}
    for a in va:
        if data[a] != 0x18:  # ADDL A, imm32
            continue
        base = int.from_bytes(bytes(data[a + 1:a + 5]), "little")
        if not (DATA_LO <= base < DATA_HI):
            continue
        i = idx[a]
        called = False
        for k in range(i + 1, min(i + 12, len(va))):
            if is_indirect_call(data, va[k]):
                called = True
                break
            if data[va[k]] in (0x66, 0x67, 0x6B):  # hit a return first
                break
        if called:
            tables.setdefault(base, []).append(a)
    return tables


def looks_like_entry(data, defined, addr):
    """A plausible function start: mapped, and decodes to a prologue or at least
    a sane first instruction."""
    if not (CODE_LO <= addr < CODE_HI) or not defined[addr]:
        return False
    op = data[addr]
    if op in (0x08, 0x4F):          # LINK / PUSHW RLST -- classic prologue
        return True
    if op in (0x40, 0x52, 0x60, 0x62, 0x64, 0x65, 0x73, 0x71):
        return True                  # small accessor / tail-jump stub
    return False


def read_table(data, defined, base, bank, max_entries=64):
    """Read 16-bit entries until one stops looking like a function start."""
    out = []
    for n in range(max_entries):
        p = base + 2 * n
        if not (defined[p] and defined[p + 1]):
            break
        target = bank | int.from_bytes(bytes(data[p:p + 2]), "little")
        if not looks_like_entry(data, defined, target):
            break
        out.append(target)
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = argv[1]
    data, defined = load_image(path)

    cache = {}
    seeds = []
    for lo in range(CODE_LO, CODE_HI, 0x10000):
        seeds += prologue_seeds(data, defined, lo, min(lo + 0x10000, CODE_HI))
    funcs = analyze(data, defined, seeds, cache=cache)
    valid = set()
    for f in funcs.values():
        if f.n_insns >= 2 and f.bad / max(1, f.n_insns) < 0.05:
            valid.update(f.insns)
    print(f"baseline: {len(funcs)} functions, {len(valid)} instruction addresses")

    tables = find_tables(data, defined, valid)
    print(f"pointer tables referenced by indirect calls: {len(tables)}")

    new_targets = set()
    for base, sites in sorted(tables.items()):
        bank = sites[0] & 0xFF0000
        entries = read_table(data, defined, base, bank)
        if entries:
            new_targets.update(entries)
            print(f"  0x{base:06X}: {len(entries):2} entries, "
                  f"referenced from {len(sites)} site(s) -> "
                  + " ".join(f"{e:06X}" for e in entries[:6])
                  + (" ..." if len(entries) > 6 else ""))

    print(f"\nnew entry points from tables: {len(new_targets)}")
    if "--expand" in argv:
        funcs2 = analyze(data, defined, sorted(new_targets) + seeds, cache=cache)
        valid2 = set()
        for f in funcs2.values():
            if f.n_insns >= 2 and f.bad / max(1, f.n_insns) < 0.05:
                valid2.update(f.insns)
        print(f"expanded: {len(funcs2)} functions, {len(valid2)} instruction addresses "
              f"(+{len(valid2 - valid)} newly reachable)")
        valid = valid2

    if "--find-writes" in argv:
        wanted = [int(x, 0) for x in argv[argv.index("--find-writes") + 1].split(",")]
        print(f"\nsearching for writes to " + ", ".join(f"0x{w:04X}" for w in wanted))
        for w in wanted:
            lo, hi = w & 0xFF, (w >> 8) & 0xFF
            hits = []
            for a in sorted(valid):
                op = data[a]
                if op in (0x53, 0x5B) and data[a + 1] == lo and data[a + 2] == hi:
                    hits.append(a)
                elif op in (0x41, 0x49, 0x44) and data[a + 1] == lo and (w >> 8) == 0x01:
                    hits.append(a)  # dir form, DPR=0x01
            print(f"  0x{w:04X}: {len(hits)} write(s)")
            for a in hits:
                l, t = disasm_one(data, a, a)
                print(f"      {a:06X}: {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
