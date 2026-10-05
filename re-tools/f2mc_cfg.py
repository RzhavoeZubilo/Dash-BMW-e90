"""
Recursive-descent disassembler / function finder for F2MC-16LX KOMBI firmware.

Builds on f2mc_disasm.disasm_one(): follows CALL/JMP/conditional-branch targets,
stops at RET/RETP/RETI, tracks visited ranges, and emits a function list with
entry address, size, call targets, and a normalized "shape" signature designed
for structural comparison between two firmware images (DKOML2 vs HKOML2) --
i.e. the thing byte-level diffing can't do, because each hardware variant is a
separately compiled and linked build.

Why a signature: absolute addresses and immediates differ between builds even
for identical source. So we hash the mnemonic-only instruction sequence (all
operands stripped) plus a coarse control-flow shape. Two functions compiled
from the same source in different builds should collide on the mnemonic hash
even though ~80% of their bytes differ.

Usage:
    # analyze the code region, seeding from CALL-vector tables + LINK prologues
    # (0xF9C000-0xFEFFFF is the real code; 0xF80000-0xF9BFFF is tables/data)
    python3 f2mc_cfg.py <file.0pa> --range 0xF9C000,0xFF0000 --json out.json

    # analyze from explicit entry points (e.g. the interrupt vector handlers)
    python3 f2mc_cfg.py DKOML2/9213308A.0pa --seeds 0x55B3,0x5644

    # dump a single function's disassembly
    python3 f2mc_cfg.py <file.0pa> --func 0xF80123

    # write the full function table as JSON, for cross-firmware comparison
    python3 f2mc_cfg.py <file.0pa> --scan --json out.json

Known limitations (deliberate, see ANALYSIS_NOTES.md):
  - Indirect control flow (JMP @A, JMP earw, CALL earw, JCTX) terminates a
    path; those targets are not resolved, so some code stays undiscovered.
  - Bank-override prefixes (PCB:/DTB:/ADB:/SPB:, opcodes 0x04-0x07) are not
    tracked across instructions.
  - Indirect CALL VCT4[n] resolves only for n=8..15: the pointer table sits in
    the top 32 bytes of each bank and the .0pa exports stop at 0xXXFFEF.
"""
import json
import sys

from f2mc_disasm import COND, SIMPLE, disasm_one, pcrel

# ---------------------------------------------------------------------------
# image loading
# ---------------------------------------------------------------------------

ADDR_SPACE = 0x1000000  # 24-bit


def load_image(path):
    """Parse a .0pa/.0ba into (data, defined) flat 16MB arrays where index ==
    absolute address. `defined[a]` is 1 only where the HEX file actually
    supplied a byte, so the walker can tell real content from unmapped gaps
    (this is why we don't just use dump_flat.py's 0xFF-filled output)."""
    from parse_ihex import parse_ihex

    mem, _, _ = parse_ihex(path)
    data = bytearray(ADDR_SPACE)
    defined = bytearray(ADDR_SPACE)
    for a, b in mem.items():
        data[a] = b
        defined[a] = 1
    return data, defined


# ---------------------------------------------------------------------------
# control-flow classification
# ---------------------------------------------------------------------------

# flow kinds
SEQ = "seq"          # falls through only
CBRANCH = "cbranch"  # falls through AND may branch to target
JUMP = "jump"        # unconditional, no fall-through
CALL = "call"        # falls through, target is a subroutine entry
RET = "ret"          # terminates the path
IJUMP = "ijump"      # indirect jump: terminates (target unknown)
ICALL = "icall"      # indirect call: falls through (target unknown)

# opcodes whose *last byte* is a signed PC-relative displacement
_REL_LAST = set([0x60, 0x2A, 0x3A]) | set(range(0xF0, 0x100))

# 0x70-block sub-operations that are control flow, keyed by (opcode, h3)
_EXT_FLOW = {
    (0x70, 2): CBRANCH,  # CWBNE earw, imm16, rel
    (0x70, 7): CBRANCH,  # CBNE ear, imm8, rel
    (0x71, 0): IJUMP,    # JMPP earl
    (0x71, 1): ICALL,    # CALLP earl
    (0x73, 0): IJUMP,    # JMP earw
    (0x73, 1): ICALL,    # CALL earw
    (0x74, 7): CBRANCH,  # DBNZ ear, rel
    (0x76, 7): CBRANCH,  # DWBNZ earw, rel
}


def classify(data, defined, off, addr, length):
    """Return (flow_kind, target_or_None) for the instruction at `off`.

    `length` must be the instruction length from disasm_one, since PC-relative
    targets are defined against inst_next (= addr + length) and the rel byte is
    always the final byte of the instruction.
    """
    op = data[off]
    bank = addr & 0xFF0000

    def rel_target():
        d = data[off + length - 1]
        return pcrel(addr, length + (d - 256 if d >= 128 else d))

    if op in _REL_LAST:
        return (JUMP if op == 0x60 else CBRANCH), rel_target()

    if op == 0x62:  # JMP addr16 -> PCB:addr16
        return JUMP, bank | int.from_bytes(data[off + 1:off + 3], "little")
    if op == 0x64:  # CALL addr16 -> PCB:addr16
        return CALL, bank | int.from_bytes(data[off + 1:off + 3], "little")
    if op == 0x63:  # JMPP addr24
        return JUMP, int.from_bytes(data[off + 1:off + 4], "little")
    if op == 0x65:  # CALLP addr24
        return CALL, int.from_bytes(data[off + 1:off + 4], "little")
    if op in (0x66, 0x67, 0x6B):  # RETP / RET / RETI
        return RET, None
    if op in (0x61, 0x13):  # JMP @A / JCTX @A
        return IJUMP, None
    if op in (0x68, 0x69, 0x6A):  # INT / INTP -- returns via RETI, so fall through
        return SEQ, None

    if 0xE0 <= op <= 0xEF:
        # CALL VCT4[n]: indirect through a pointer at (bank | 0xFFFE - 2n).
        # Those table slots live in the top 32 bytes of each bank; the .0pa
        # exports stop at 0xXXFFEF, so slots for n=8..15 are present and
        # resolvable while n=0..7 are not shipped in the image.
        slot = bank | (0xFFFE - 2 * (op & 0xF))
        if defined[slot] and defined[slot + 1]:
            return CALL, bank | int.from_bytes(data[slot:slot + 2], "little")
        return ICALL, None

    if 0x70 <= op <= 0x7F:
        h3 = (data[off + 1] >> 5) & 0x7
        kind = _EXT_FLOW.get((op, h3))
        if kind == CBRANCH:
            return CBRANCH, rel_target()
        if kind:
            return kind, None
        return SEQ, None

    if op == 0x6C:
        # BBC / BBS always branch; op 7 branches only in its SBBS (addr16) form
        # -- in io form it is WBTC, which has no rel byte at all.
        b2 = data[off + 1]
        op1, mode = (b2 >> 5) & 0x7, (b2 >> 3) & 0x3
        if op1 in (4, 5) or (op1 == 7 and mode == 3):
            return CBRANCH, rel_target()
        return SEQ, None

    return SEQ, None


def mnemonic(text):
    """Strip operands, leaving just the mnemonic -- the unit of comparison for
    cross-build structural matching."""
    return text.split()[0] if text else "?"


# ---------------------------------------------------------------------------
# recursive descent
# ---------------------------------------------------------------------------

class Function:
    __slots__ = ("entry", "insns", "calls", "end", "truncated", "bad", "tailcalls")

    def __init__(self, entry):
        self.entry = entry
        self.insns = {}      # addr -> (length, text)
        self.calls = set()   # resolved call targets
        self.tailcalls = set()
        self.end = entry
        self.truncated = False  # ran off into undefined memory / hit a limit
        self.bad = 0            # count of undecodable (DB) bytes

    @property
    def size(self):
        return self.end - self.entry

    @property
    def n_insns(self):
        return len(self.insns)

    def mnemonics(self):
        return [mnemonic(self.insns[a][1]) for a in sorted(self.insns)]

    def signature(self):
        """Order-preserving mnemonic-sequence hash: stable across builds that
        differ only in absolute addresses/immediates."""
        import hashlib
        return hashlib.sha1(",".join(self.mnemonics()).encode()).hexdigest()[:16]

    def shape(self):
        """Coarse, operand-free control-flow fingerprint. Deliberately lossy so
        it still matches when a compiler reorders or slightly re-schedules."""
        m = self.mnemonics()
        branches = sum(1 for x in m if x.startswith("B") and x != "BRA")
        return (self.n_insns, branches, len(self.calls))


def decode_at(data, defined, a, cache=None):
    """Decode + classify one instruction, memoized. Functions overlap heavily
    (shared tails, jump targets reached from several seeds), so without a cache
    the same bytes get decoded 4-5x over a full-bank scan."""
    if cache is not None and a in cache:
        return cache[a]
    length, text = disasm_one(data, a, a)
    if any(not defined[a + i] for i in range(length)):
        result = None  # instruction straddles the end of mapped memory
    else:
        kind, target = classify(data, defined, a, a, length)
        result = (length, text, kind, target)
    if cache is not None:
        cache[a] = result
    return result


def walk_function(data, defined, entry, max_insns=20000, cache=None):
    """Trace one function from `entry`, following intra-function control flow."""
    f = Function(entry)
    stack = [entry]
    while stack:
        a = stack.pop()
        while True:
            if a in f.insns or not (0 <= a < ADDR_SPACE):
                break
            if not defined[a]:
                f.truncated = True
                break
            if len(f.insns) >= max_insns:
                f.truncated = True
                break

            decoded = decode_at(data, defined, a, cache)
            if decoded is None:
                f.truncated = True
                break
            length, text, kind, target = decoded

            f.insns[a] = (length, text)
            if text.startswith("DB "):
                f.bad += 1
            f.end = max(f.end, a + length)

            if kind in (RET, IJUMP):
                break
            if kind == CALL and target is not None:
                f.calls.add(target)
            if kind == CBRANCH and target is not None:
                stack.append(target)
            if kind == JUMP:
                if target is None:
                    break
                # A jump far away (other bank, or beyond a plausible function
                # span) is treated as a tail call rather than inlined here --
                # otherwise one runaway jump merges half the bank into one
                # "function".
                if (target & 0xFF0000) != (entry & 0xFF0000) or abs(target - entry) > 0x4000:
                    f.tailcalls.add(target)
                    break
                a = target
                continue
            a += length
    return f


def analyze(data, defined, seeds, max_funcs=100000, cache=None):
    """Recursive descent from `seeds`, discovering callees transitively."""
    if cache is None:
        cache = {}
    funcs = {}
    worklist = list(dict.fromkeys(seeds))
    while worklist and len(funcs) < max_funcs:
        entry = worklist.pop()
        if entry in funcs or not (0 <= entry < ADDR_SPACE) or not defined[entry]:
            continue
        f = walk_function(data, defined, entry, cache=cache)
        funcs[entry] = f
        for t in f.calls | f.tailcalls:
            if t not in funcs:
                worklist.append(t)
    return funcs


# ---------------------------------------------------------------------------
# seeding
# ---------------------------------------------------------------------------

def vct4_seeds(data, defined, bank):
    """Entry points from the CALL VCT4 pointer table at the top of a bank."""
    out = []
    for n in range(16):
        slot = (bank << 16) | (0xFFFE - 2 * n) if bank < 0x100 else bank | (0xFFFE - 2 * n)
        if slot < ADDR_SPACE and defined[slot] and defined[slot + 1]:
            target = (slot & 0xFF0000) | int.from_bytes(data[slot:slot + 2], "little")
            if defined[target]:
                out.append(target)
    return out


def prologue_seeds(data, defined, lo, hi):
    """Scan for `LINK #imm8` (0x08), the standard stack-frame prologue, as a
    heuristic function-start signal. Produces false positives (0x08 also occurs
    inside operands/data) -- callers should filter on decode quality."""
    out = []
    for a in range(lo, min(hi, ADDR_SPACE - 1)):
        if defined[a] and data[a] == 0x08 and defined[a + 1]:
            out.append(a)
    return out


def bank_range(bank):
    base = bank << 16 if bank < 0x100 else bank & 0xFF0000
    return base, base + 0x10000


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _quality(f):
    """Fraction of instructions that decoded to raw bytes -- high means the
    'function' is probably misidentified data."""
    return f.bad / f.n_insns if f.n_insns else 1.0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = argv[1]
    args = argv[2:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    data, defined = load_image(path)

    seeds = []
    if opt("--seeds"):
        seeds += [int(x, 0) for x in opt("--seeds").split(",")]
    if opt("--func"):
        entry = int(opt("--func"), 0)
        f = walk_function(data, defined, entry)
        for a in sorted(f.insns):
            length, text = f.insns[a]
            raw = bytes(data[a:a + length]).hex()
            print(f"{a:06X}: {raw:<12} {text}")
        print(f"\n; {f.n_insns} insns, 0x{f.entry:06X}-0x{f.end:06X} "
              f"(size {f.size}), calls={len(f.calls)}, bad={f.bad}, "
              f"truncated={f.truncated}, sig={f.signature()}")
        return 0

    if opt("--range"):
        lo, hi = [int(x, 0) for x in opt("--range").split(",")]
        seeds += prologue_seeds(data, defined, lo, hi)
        for b in range(lo >> 16, (hi >> 16) + 1):
            seeds += vct4_seeds(data, defined, b)

    banks = [int(x, 0) for x in opt("--bank", "").split(",") if x] if opt("--bank") else []
    if "--scan" in args:
        targets = banks or [b >> 16 for b in range(0, ADDR_SPACE, 0x10000)
                            if defined[b]]
        for b in targets:
            lo, hi = bank_range(b)
            seeds += vct4_seeds(data, defined, b)
            seeds += prologue_seeds(data, defined, lo, hi)

    if not seeds:
        print("no seeds: pass --seeds, --func, or --scan [--bank 0xF8]")
        return 1

    funcs = analyze(data, defined, seeds)

    good = {a: f for a, f in funcs.items() if _quality(f) < 0.15 and f.n_insns >= 3}
    print(f"{path}")
    print(f"  seeds:      {len(seeds)}")
    print(f"  functions:  {len(funcs)} discovered, {len(good)} pass quality filter")
    if good:
        sizes = sorted(f.size for f in good.values())
        cov = sum(f.n_insns for f in good.values())
        print(f"  size:       median {sizes[len(sizes)//2]}, max {sizes[-1]}")
        print(f"  instrs:     {cov} decoded in accepted functions")
        trunc = sum(1 for f in good.values() if f.truncated)
        print(f"  truncated:  {trunc}")

    if opt("--json"):
        out = {
            f"{a:06X}": {
                "entry": a,
                "size": f.size,
                "n_insns": f.n_insns,
                "calls": sorted(f.calls),
                "tailcalls": sorted(f.tailcalls),
                "truncated": f.truncated,
                "bad": f.bad,
                "signature": f.signature(),
                "shape": f.shape(),
                "mnemonics": f.mnemonics(),
            }
            for a, f in good.items()
        }
        with open(opt("--json"), "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"  wrote {opt('--json')} ({len(out)} functions)")

    if "--list" in args:
        for a in sorted(good):
            f = good[a]
            print(f"  0x{a:06X}  size={f.size:<6} insns={f.n_insns:<5} "
                  f"calls={len(f.calls):<3} sig={f.signature()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
