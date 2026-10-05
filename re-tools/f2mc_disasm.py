"""
Minimal F2MC-16LX (Fujitsu, used in BMW KOMBI PL2 / MB90F395HA) disassembler.

Hand-ported from the authoritative Ghidra SLEIGH spec:
  https://github.com/mehmooda/F2MC-16LX  (data/languages/F2MC.slaspec)

This is NOT a complete/verified disassembler -- it covers the regular,
well-documented parts of the opcode map (0x00-0x7F fixed & prefix forms,
0x80-0xFF short register forms) well enough for linear sweep / function-
boundary spotting. Extended addressing submodes under 0x70-0x7F are
approximated: length is computed correctly (that's the important part for
staying in sync), but not every operand is rendered with full fidelity.
Treat output as a research aid, not ground truth -- cross-check anything
that matters against the real Fujitsu Programming Manual (CM44-00201-3E).

Confirmed chip: both DKOML2 (box) and E9XHIGH (no box) clusters use the
IDENTICAL MB90F395HA silicon (read off the physical chip package) -- so any
rendering difference is 100% firmware, not hardware.

Usage:
    python3 f2mc_disasm.py <flat.bin> [start_addr] [count]

Use dump_flat.py first to turn a .0pa Intel HEX file into a flat binary
this script can load.
"""
import sys

REG1R = ["R0","R1","R2","R3","R4","R5","R6","R7"]
REG1RW = ["RW0","RW1","RW2","RW3","RW4","RW5","RW6","RW7"]
BANKREG = ["DTB","PCB","ADB","SSB"]

# simple fixed-length, fixed-mnemonic table for 0x00-0x6B (opcode -> (mnemonic, extra_bytes, operand_desc))
SIMPLE = {
    0x00: ("NOP", 0, None),
    0x01: ("IN9", 0, None),
    0x02: ("ADDDC A", 0, None),
    0x03: ("NEG A", 0, None),
    0x04: ("PCB:", 0, None),      # bank-override prefix
    0x05: ("DTB:", 0, None),
    0x06: ("ADB:", 0, None),
    0x07: ("SPB:", 0, None),
    0x08: ("LINK", 1, "imm8"),
    0x09: ("UNLINK", 0, None),
    0x0A: ("MOV RP,", 1, "imm8"),
    0x0B: ("NEGW A", 0, None),
    0x0C: ("LSLW A", 0, None),
    0x0E: ("ASRW A", 0, None),
    0x0F: ("LSRW A", 0, None),
    0x10: ("CMR", 0, None),
    0x11: ("NCC", 0, None),
    0x12: ("SUBDC A", 0, None),
    0x13: ("JCTX @A", 0, None),
    0x14: ("EXT", 0, None),
    0x15: ("ZEXT", 0, None),
    0x16: ("SWAP", 0, None),
    0x17: ("ADD SSP,", 1, "imm8"),
    0x18: ("ADDL A,", 4, "imm32"),
    0x19: ("SUBL A,", 4, "imm32"),
    0x1A: ("MOV ILM,", 1, "imm8"),
    0x1B: ("CMPL A,", 4, "imm32"),
    0x1C: ("EXTW", 0, None),
    0x1D: ("ZEXTW", 0, None),
    0x1E: ("SWAPW", 0, None),
    0x1F: ("ADD SSP,", 2, "imm16"),
    0x20: ("ADD A,", 1, "dir"),
    0x21: ("SUB A,", 1, "dir"),
    0x22: ("ADDC A", 0, None),
    0x23: ("CMP A", 0, None),
    0x24: ("AND CCR,", 1, "imm8"),
    0x25: ("OR CCR,", 1, "imm8"),
    0x26: ("DIVU A", 0, None),
    0x27: ("MULU A", 0, None),
    0x28: ("ADDW A", 0, None),
    0x29: ("SUBW A", 0, None),
    0x2A: ("CBNE A,", 2, "imm8,rel"),
    0x2B: ("CMPW A", 0, None),
    0x2C: ("ANDW A", 0, None),
    0x2D: ("ORW A", 0, None),
    0x2E: ("XORW A", 0, None),
    0x2F: ("MULUW A", 0, None),
    0x30: ("ADD A,", 1, "imm8"),
    0x31: ("SUB A,", 1, "imm8"),
    0x32: ("SUBC A", 0, None),
    0x33: ("CMP A,", 1, "imm8"),
    0x34: ("AND A,", 1, "imm8"),
    0x35: ("OR A,", 1, "imm8"),
    0x36: ("XOR A,", 1, "imm8"),
    0x37: ("NOT A", 0, None),
    0x38: ("ADDW A,", 2, "imm16"),
    0x39: ("SUBW A,", 2, "imm16"),
    0x3A: ("CWBNE A,", 3, "imm16,rel"),
    0x3B: ("CMPW A,", 2, "imm16"),
    0x3C: ("ANDW A,", 2, "imm16"),
    0x3D: ("ORW A,", 2, "imm16"),
    0x3E: ("XORW A,", 2, "imm16"),
    0x3F: ("NOTW A", 0, None),
    0x40: ("MOV A,", 1, "dir"),
    0x41: ("MOV", 1, "dir,A"),
    0x42: ("MOV A,", 1, "imm8"),
    0x43: ("MOVX A,", 1, "imm8"),
    0x44: ("MOV", 2, "dir,imm8"),
    0x45: ("MOVX A,", 1, "dir"),
    0x46: ("MOVW A,SSP", 0, None),
    0x47: ("MOVW SSP,A", 0, None),
    0x48: ("MOVW A,", 1, "dir"),
    0x49: ("MOVW", 1, "dir,A"),
    0x4A: ("MOVW A,", 2, "imm16"),
    0x4B: ("MOVL A,", 4, "imm32"),
    0x4C: ("PUSHW A", 0, None),
    0x4D: ("PUSHW AH", 0, None),
    0x4E: ("PUSHW PS", 0, None),
    0x4F: ("PUSHW", 1, "rlst"),
    0x50: ("MOV A,", 1, "io"),
    0x51: ("MOV", 1, "io,A"),
    0x52: ("MOV A,", 2, "addr16"),
    0x53: ("MOV", 2, "addr16,A"),
    0x54: ("MOV", 2, "io,imm8"),
    0x55: ("MOVX A,", 1, "io"),
    0x56: ("MOVW", 3, "io,imm16"),
    0x57: ("MOVW A,", 2, "addr16"),
    0x58: ("MOVW A,", 1, "io"),
    0x59: ("MOVW", 1, "io,A"),
    0x5A: ("MOVW A,", 2, "addr16"),
    0x5B: ("MOVW", 2, "addr16,A"),
    0x5C: ("POPW A", 0, None),
    0x5D: ("POPW AH", 0, None),
    0x5E: ("POPW PS", 0, None),
    0x5F: ("POPW", 1, "rlst"),
    0x60: ("BRA", 1, "rel"),
    0x61: ("JMP @A", 0, None),
    0x62: ("JMP", 2, "pcaddr16"),
    0x63: ("JMPP", 3, "addr24"),
    0x64: ("CALL", 2, "pcaddr16"),
    0x65: ("CALLP", 3, "addr24"),
    0x66: ("RETP", 0, None),
    0x67: ("RET", 0, None),
    0x68: ("INT", 1, "vct8"),
    0x69: ("INT", 2, "pcaddr16"),
    0x6A: ("INTP", 3, "addr24"),
    0x6B: ("RETI", 0, None),
}

COND = ["Z","NZ","C","NC","N","P","V","NV","T","NT","LT","GE","LE","GT","LS","HI"]


def pcrel(addr, delta):
    """Resolve a PC-relative target.

    The F2MC-16LX program counter is 16-bit and lives inside the bank selected
    by PCB; arithmetic on it wraps within the 64K bank and does NOT carry into
    the bank number. `delta` is the displacement from `addr` (callers pass
    instruction_length + rel for `rel` operands, since the spec defines those
    against inst_next).
    """
    return (addr & 0xFF0000) | ((addr + delta) & 0xFFFF)


def fmt_imm(data, off, width):
    if off + width > len(data):
        return "??"
    val = int.from_bytes(data[off:off+width], "little")
    return f"0x{val:0{width*2}X}"


# --- 0x6F extended block ----------------------------------------------------
# Byte2 fields (F2MC.slaspec): opcode6fh=(4,7), opcode6fb3=(3,3),
# reg6f=(1,2), opcode6fb0=(0,0).
#
# The length rule is what matters most: an instruction is 3 bytes (trailing d8)
# exactly when opcode6fb0=0 and either opcode6fh is 3 or 4 (both b3 values are
# defined there), or opcode6fh is 2 with b3=0. Everything else is 2 bytes.
# The previous hardcoded list of "byte2 values that take a d8" was wrong in
# both directions -- it included b0=1 encodings that take no operand and, more
# damagingly, omitted the whole opcode6fh=3/4 range (byte2 0x30-0x4F), so every
# `MOV A,@RWn+d8` / `MOV @RWn+d8,A` was decoded one byte short.

_6F_FIXED = {
    0x05: "MOV A,@A", 0x06: "MOV A,PCB", 0x0C: "LSLW A,R0", 0x0D: "MOVW A,@A",
    0x0E: "ASRW A,R0", 0x0F: "LSRW A,R0", 0x15: "MOV @AL,AH", 0x16: "MOVX A,@A",
    0x1C: "LSLL A,R0", 0x1D: "MOVW @AL,AH", 0x1E: "ASRL A,R0", 0x1F: "LSRL A,R0",
    0x2C: "LSL A,R0", 0x2D: "NRML A,R0", 0x2E: "ASR A,R0", 0x2F: "LSR A,R0",
    0x78: "MUL A", 0x79: "MULW A", 0x7A: "DIV A",
}


def disasm_6f(data, off):
    if off + 2 > len(data):
        return 2, "0x6F ??"
    b2 = data[off + 1]
    h = (b2 >> 4) & 0xF
    b3 = (b2 >> 3) & 1
    reg = (b2 >> 1) & 0x3      # RL0-RL3 (24-bit pointer registers)
    b0 = b2 & 1

    if b0 == 0 and (h in (3, 4) or (h == 2 and b3 == 0)):
        d8 = data[off + 2] if off + 2 < len(data) else 0
        operand = f"@RL{reg}+0x{d8:02X}"
        if h == 2:
            text = f"MOVX A,{operand}"
        elif h == 3:
            text = f"{'MOVW' if b3 else 'MOV'} {operand},A"
        else:
            text = f"{'MOVW' if b3 else 'MOV'} A,{operand}"
        return 3, text

    return 2, _6F_FIXED.get(b2, f"0x6F/0x{b2:02X}")


# --- 0x6C bit-manipulation block --------------------------------------------
# The single most important group for this project: every lamp/indicator/flag
# in automotive cluster firmware is a bit, so "does this display slot get a
# box?" is very likely a SETB/CLRB/BBC/BBS on a display flag byte.
#
# Byte2 layout (F2MC.slaspec, `a6caddr` + the 0x6C instruction list):
#   bits[7:5] = opcode6c1    -- operation
#   bits[4:3] = opcode6caddr -- addressing mode of the bit's base address
#   bits[2:0] = opcode6c3    -- which bit (0-7)
#
# Addressing modes: 0 = io (1 byte, I/O area 0x0000-0x00FF)
#                   1 = dir (1 byte, direct page -- effective address is
#                       bank:DPR:adir, and DPR is a runtime register, so the
#                       real address can't be resolved statically)
#                   3 = addr16 (2 bytes, bank from DTB / prefix override)
#                   2 = not defined by the spec
#
# Operations: 0 MOVB A,b  1 MOVB b,A  2 CLRB  3 SETB  4 BBC(+rel)  5 BBS(+rel)
#             6 WBTS (io only)  7 WBTC (io only) / SBBS (addr16 only, +rel)
# NOTE the op-7 split: WBTC has NO trailing rel byte but SBBS does, so the
# operation alone doesn't determine the length -- the addressing mode does.
# Getting this wrong shifts every following instruction by one byte.

_6C_OPS = {0: "MOVB", 1: "MOVB", 2: "CLRB", 3: "SETB",
           4: "BBC", 5: "BBS", 6: "WBTS", 7: "WBTC"}


def _a6caddr(data, off, mode):
    """Render the 0x6C base-address operand. Returns (extra_bytes, text)."""
    if mode == 0:
        if off + 3 > len(data):
            return 1, "IO[??]"
        return 1, f"IO[0x{data[off+2]:02X}]"
    if mode == 1:
        if off + 3 > len(data):
            return 1, "DIR[??]"
        return 1, f"DIR[0x{data[off+2]:02X}]"
    if mode == 3:
        if off + 4 > len(data):
            return 2, "[??]"
        return 2, f"[0x{int.from_bytes(data[off+2:off+4], 'little'):04X}]"
    return 1, "??"  # mode 2: no production in the spec


def disasm_6c(data, off, addr):
    if off + 2 > len(data):
        return 2, "0x6C ??"
    b2 = data[off + 1]
    op1 = (b2 >> 5) & 0x7
    mode = (b2 >> 3) & 0x3
    bit = b2 & 0x7

    extra, operand = _a6caddr(data, off, mode)
    length = 2 + extra

    # op 7 is WBTC for io-mode but SBBS for addr16-mode; only SBBS takes a rel
    if op1 == 7 and mode == 3:
        mnem, has_rel = "SBBS", True
    else:
        mnem, has_rel = _6C_OPS.get(op1, "?"), op1 in (4, 5)

    if op1 == 0:
        text = f"{mnem} A,{operand}:{bit}"
    elif op1 == 1:
        text = f"{mnem} {operand}:{bit},A"
    else:
        text = f"{mnem} {operand}:{bit}"

    if has_rel:
        d = data[off + length] if off + length < len(data) else 0
        rel = d - 256 if d >= 128 else d
        length += 1
        text += f", 0x{pcrel(addr, length + rel):06X}"

    return length, text


# --- 0x70-0x7F extended-addressing ALU block --------------------------------
# Byte2 layout (verified against F2MC.slaspec's ear/earw/earl/v70var productions,
# https://github.com/mehmooda/F2MC-16LX):
#   bits[7:5] = opcode70h3  -- sub-operation select for 0x70-0x77 (8 ops per base
#               opcode), or the outer register select (reg7r/reg7b, R0-R7/RW0-RW7)
#               for 0x79-0x7F, or opcode70h2/opcode70hb3 (mul/div variant) for 0x78.
#   bits[4:3] = opcode70b34 -- addressing-mode select for the "ear"/"earw"/"earl"
#               operand (shared meaning across all of 0x70-0x7F):
#                 0 -> plain register (R0-R7 / RW0-RW7 / RL0-RL3, size depends on
#                      whether the instruction wants ear/earw/earl), no extra bytes
#                 1 -> @RWn indirect, n in 0-3, bank fixed by hardware wiring
#                      (RW0,RW1->DTB, RW2->ADB, RW3->SSB); bit2 selects a "+1"
#                      byte-offset variant; no extra bytes
#                 2 -> @RWn+d8, n in 0-7 (reg70w), 1 extra byte (signed d8)
#                 3 -> further split by bits[2:1]:
#                      b2=0            -> @RWn+d16, n in 0-1 (RW0/RW1), 2 extra
#                                         bytes (signed d16)
#                      b2=1,b1=0       -> @RWn+RW7, n in 0-1, no extra bytes
#                      b2=1,b1=1,b0=0  -> PC-relative: target = inst_start + d16
#                      b2=1,b1=1,b0=1  -> absolute addr16 (unsigned)
#   bits[2:0] = register select for the b34=0/1/2/3(b2=0/b1=0) cases (reg70r /
#               reg70w / reg70l / reg70wl2 / reg70wl1 -- which subfield applies
#               depends on b34, see above).
# Bank for the @RWn+d8 (b34=2) and @RWn+d16 (b34=3,b2=0) forms defaults to DTB
# unless a PCB:/DTB:/ADB:/SPB: prefix byte (0x04-0x07) preceded the instruction;
# we don't track that prefix state here (linear per-instruction decode), so we
# render those without an explicit bank tag -- treat as "current data bank".

_EAR_REG = {"r": REG1R, "w": REG1RW}


def _ext_addr_operand(data, off, b2, addr):
    """Decode the shared ear/earw/earl addressing-mode operand at byte2=data[off+1].
    `addr` is the real address of the instruction start (== inst_start in the
    SLEIGH spec), needed for the PC-relative form.
    Returns (extra_bytes_after_byte2, operand_text_or_None). operand_text is None
    for the register-direct case (b34=0) -- caller fills in the register name
    using the correct register set (R/RW/RL) for the instruction's operand size.
    """
    b34 = (b2 >> 3) & 0x3
    if b34 == 0:
        return 0, None
    if b34 == 1:
        variant = (b2 >> 2) & 1
        regsel = b2 & 0x3
        bank = ["DTB", "DTB", "ADB", "SSB"][regsel]
        suffix = "+1" if variant else ""
        return 0, f"@{bank}:RW{regsel}{suffix}"
    if b34 == 2:
        regsel = b2 & 0x7
        if off + 3 > len(data):
            return 1, "@RW?+??"
        d8 = data[off + 2]
        if d8 >= 128:
            d8 -= 256
        sign = "+" if d8 >= 0 else "-"
        return 1, f"@RW{regsel}{sign}0x{abs(d8):02X}"
    # b34 == 3
    b2f = (b2 >> 2) & 1
    if b2f == 0:
        regsel = b2 & 0x1
        if off + 4 > len(data):
            return 2, "@RW?+????"
        d16 = int.from_bytes(data[off+2:off+4], "little")
        if d16 >= 0x8000:
            d16 -= 0x10000
        sign = "+" if d16 >= 0 else "-"
        return 2, f"@RW{regsel}{sign}0x{abs(d16):04X}"
    b1f = (b2 >> 1) & 1
    if b1f == 0:
        regsel = b2 & 0x1
        return 0, f"@RW{regsel}+RW7"
    b0f = b2 & 1
    if off + 4 > len(data):
        return 2, "[????]"
    raw16 = int.from_bytes(data[off+2:off+4], "little")
    if b0f == 0:
        # spec: reloc = inst_start + d16  (relative to the START of the
        # instruction, NOT to inst_next like the ordinary `rel` operand)
        d16 = raw16 - 0x10000 if raw16 >= 0x8000 else raw16
        target = pcrel(addr, d16)
        return 2, f"REL[0x{target:06X}]"
    else:
        return 2, f"[0x{raw16:04X}]"


def _ext_operand(data, off, b2, kind, addr):
    """Render the ear(kind='r',1B) / earw(kind='w',2B) / earl(kind='l',4B) operand.
    Returns (extra_bytes, text)."""
    b34 = (b2 >> 3) & 0x3
    extra, addr_text = _ext_addr_operand(data, off, b2, addr)
    if b34 != 0:
        return extra, addr_text
    # register-direct form: which register set depends on operand size
    if kind == "l":
        regsel = (b2 >> 1) & 0x3  # reg70l: bits[2:1], RL0-RL3
        return 0, f"RL{regsel}"
    if kind == "w":
        regsel = b2 & 0x7  # reg70w: bits[2:0], RW0-RW7
        return 0, REG1RW[regsel]
    regsel = b2 & 0x7  # reg70r: bits[2:0], R0-R7
    return 0, REG1R[regsel]


# op -> {h3: (mnemonic_template, ear_kind, extra_operand)}
# extra_operand: None | "imm8" | "imm16" | "rel" | "imm8,rel" | "imm16,rel"
# mnemonic_template uses {A} for the accumulator operand position via explicit
# strings below (kept simple/explicit rather than templated further).
_H3_TABLE = {
    0x70: {
        0: ("ADDL A,", "l", None), 1: ("SUBL A,", "l", None),
        2: ("CWBNE", "w", "imm16,rel"), 3: ("CMPL A,", "l", None),
        4: ("ANDL A,", "l", None), 5: ("ORL A,", "l", None),
        6: ("XORL A,", "l", None), 7: ("CBNE", "r", "imm8,rel"),
    },
    0x71: {
        0: ("JMPP", "l", None), 1: ("CALLP", "l", None),
        2: ("INCL", "l", None), 3: ("DECL", "l", None),
        4: ("MOVL A,", "l", None), 5: ("MOVL_TO", "l", None),
        6: ("MOV_EAR_IMM8", "r", "imm8"), 7: ("MOVEA A,", "w", None),
    },
    0x72: {
        0: ("ROLC", "r", None), 1: ("RORC", "r", None),
        2: ("INC", "r", None), 3: ("DEC", "r", None),
        4: ("MOV A,", "r", None), 5: ("MOV_TO", "r", None),
        6: ("MOVX A,", "r", None), 7: ("XCH A,", "r", None),
    },
    0x73: {
        0: ("JMP", "w", None), 1: ("CALL", "w", None),
        2: ("INCW", "w", None), 3: ("DECW", "w", None),
        4: ("MOVW A,", "w", None), 5: ("MOVW_TO", "w", None),
        6: ("MOVW_EARW_IMM16", "w", "imm16"), 7: ("XCHW A,", "w", None),
    },
    0x74: {
        0: ("ADD A,", "r", None), 1: ("SUB A,", "r", None),
        2: ("ADDC A,", "r", None), 3: ("CMP A,", "r", None),
        4: ("AND A,", "r", None), 5: ("OR A,", "r", None),
        6: ("XOR A,", "r", None), 7: ("DBNZ", "r", "rel"),
    },
    0x75: {
        0: ("ADD_TO_A", "r", None), 1: ("SUB_TO_A", "r", None),
        2: ("SUBC A,", "r", None), 3: ("NEG", "r", None),
        4: ("AND_TO_A", "r", None), 5: ("OR_TO_A", "r", None),
        6: ("XOR_TO_A", "r", None), 7: ("NOT", "r", None),
    },
    0x76: {
        0: ("ADDW A,", "w", None), 1: ("SUBW A,", "w", None),
        2: ("ADDCW A,", "w", None), 3: ("CMPW A,", "w", None),
        4: ("ANDW A,", "w", None), 5: ("ORW A,", "w", None),
        6: ("XORW A,", "w", None), 7: ("DWBNZ", "w", "rel"),
    },
    0x77: {
        0: ("ADDW_TO_A", "w", None), 1: ("SUBW_TO_A", "w", None),
        2: ("SUBCW A,", "w", None), 3: ("NEGW", "w", None),
        4: ("ANDW_TO_A", "w", None), 5: ("ORW_TO_A", "w", None),
        6: ("XORW_TO_A", "w", None), 7: ("NOTW", "w", None),
    },
}

# templates that put the operand on the LEFT ("earw, A" / "earl, A" style)
_TO_A_MNEM = {
    "MOVL_TO": "MOVL", "MOV_TO": "MOV", "MOVW_TO": "MOVW",
    "ADD_TO_A": "ADD", "SUB_TO_A": "SUB", "AND_TO_A": "AND", "OR_TO_A": "OR",
    "XOR_TO_A": "XOR", "ADDW_TO_A": "ADDW", "SUBW_TO_A": "SUBW",
    "ANDW_TO_A": "ANDW", "ORW_TO_A": "ORW", "XORW_TO_A": "XORW",
}


def disasm_70(data, off, op, addr):
    if off + 2 > len(data):
        return 2, f"0x{op:02X} ??"
    b2 = data[off + 1]

    if op == 0x78:
        # MUL/DIV, operand size + suffix selected by opcode70h2 (bits 6:5),
        # MUL vs DIV by opcode70hb3 (bit 7).
        h2 = (b2 >> 5) & 0x3
        is_div = (b2 >> 7) & 1
        kind, suffix = {0: ("r", "U"), 1: ("w", "UW"), 2: ("r", ""), 3: ("w", "W")}[h2]
        extra, operand = _ext_operand(data, off, b2, kind, addr)
        mnem = ("DIV" if is_div else "MUL") + suffix
        length = 2 + extra
        return length, f"{mnem} A,{operand}"

    if 0x79 <= op <= 0x7F:
        # outer register (bits[7:5]) combined with an ear/earw operand.
        outer = (b2 >> 5) & 0x7
        table = {
            0x79: ("MOVEA", "w", REG1RW, False),
            0x7A: ("MOV", "r", REG1R, False),
            0x7B: ("MOVW", "w", REG1RW, False),
            0x7C: ("MOV", "r", REG1R, True),
            0x7D: ("MOVW", "w", REG1RW, True),
            0x7E: ("XCH", "r", REG1R, False),
            0x7F: ("XCHW", "w", REG1RW, False),
        }
        mnem, kind, regset, ear_first = table[op]
        extra, operand = _ext_operand(data, off, b2, kind, addr)
        length = 2 + extra
        regname = regset[outer]
        if ear_first:
            return length, f"{mnem} {operand},{regname}"
        return length, f"{mnem} {regname},{operand}"

    # 0x70-0x77
    h3 = (b2 >> 5) & 0x7
    mnem, kind, extra_op = _H3_TABLE[op][h3]
    extra, operand = _ext_operand(data, off, b2, kind, addr)
    length = 2 + extra

    if mnem in _TO_A_MNEM:
        text = f"{_TO_A_MNEM[mnem]} {operand},A"
    elif mnem == "MOV_EAR_IMM8":
        if off + length + 1 > len(data):
            return length + 1, "MOV ??"
        text = f"MOV {operand},{fmt_imm(data, off+length, 1)}"
        length += 1
    elif mnem == "MOVW_EARW_IMM16":
        text = f"MOVW {operand},{fmt_imm(data, off+length, 2)}"
        length += 2
    else:
        text = f"{mnem} {operand}"

    # `rel` operands are relative to inst_next (the address AFTER the whole
    # instruction), per the spec's `rel: reloc = inst_next + pcrel`.
    if extra_op == "rel":
        d = data[off+length] if off+length < len(data) else 0
        rel = d - 256 if d >= 128 else d
        length += 1
        target = pcrel(addr, length + rel)
        text = f"{text}, 0x{target:06X}"
    elif extra_op == "imm8,rel":
        d = data[off+length+1] if off+length+1 < len(data) else 0
        rel = d - 256 if d >= 128 else d
        imm_txt = fmt_imm(data, off+length, 1)
        length += 2
        target = pcrel(addr, length + rel)
        text = f"{text}, {imm_txt}, 0x{target:06X}"
    elif extra_op == "imm16,rel":
        d = data[off+length+2] if off+length+2 < len(data) else 0
        rel = d - 256 if d >= 128 else d
        imm_txt = fmt_imm(data, off+length, 2)
        length += 3
        target = pcrel(addr, length + rel)
        text = f"{text}, {imm_txt}, 0x{target:06X}"

    return length, text


def disasm_one(data, off, addr=None):
    """Return (length, text) for the instruction at data[off:]. Best-effort.

    `addr` is the real address this instruction lives at. It matters for the
    banked forms (`JMP`/`CALL addr16` take their bank from PCB, i.e. from the
    instruction's own bank) and for every PC-relative target. Defaults to
    `off`, which is correct for the flat full-address-space images produced by
    dump_flat.py (where file offset == address).
    """
    if off >= len(data):
        return 1, "??"
    if addr is None:
        addr = off
    bank = addr & 0xFF0000
    op = data[off]

    if op in SIMPLE:
        mnem, extra, kind = SIMPLE[op]
        if kind is None:
            return 1, mnem
        if kind == "rel":
            if off+2 > len(data): return 1+extra, mnem+" ??"
            d = data[off+1]
            rel = d - 256 if d >= 128 else d
            target = pcrel(addr, 2 + rel)
            return 2, f"{mnem} 0x{target:06X}"
        if kind == "dir":
            return 1+extra, f"{mnem} DIR[0x{data[off+1]:02X}]" if off+1 < len(data) else mnem+" ??"
        if kind == "io":
            return 1+extra, f"{mnem} IO[0x{data[off+1]:02X}]" if off+1 < len(data) else mnem+" ??"
        if kind == "imm8":
            return 1+extra, f"{mnem} {fmt_imm(data, off+1, 1)}"
        if kind == "imm16":
            return 1+extra, f"{mnem} {fmt_imm(data, off+1, 2)}"
        if kind == "imm32":
            return 1+extra, f"{mnem} {fmt_imm(data, off+1, 4)}"
        if kind == "addr16":
            # data-space addr16: bank comes from DTB (or a prefix override),
            # which we don't track -- render bank-less.
            return 1+extra, f"{mnem} [{fmt_imm(data, off+1, 2)}]"
        if kind == "pcaddr16":
            # code-space addr16: bank is PCB, i.e. this instruction's own bank
            if off+3 > len(data):
                return 1+extra, mnem+" ??"
            target = bank | int.from_bytes(data[off+1:off+3], "little")
            return 1+extra, f"{mnem} 0x{target:06X}"
        if kind == "addr24":
            return 1+extra, f"{mnem} [{fmt_imm(data, off+1, 3)}]"
        if kind == "vct8":
            return 1+extra, f"{mnem} VCT[0x{data[off+1]:02X}]" if off+1 < len(data) else mnem+" ??"
        if kind == "dir,A":
            return 1+extra, f"{mnem} DIR[0x{data[off+1]:02X}],A" if off+1 < len(data) else mnem+" ??"
        if kind == "io,A":
            return 1+extra, f"{mnem} IO[0x{data[off+1]:02X}],A" if off+1 < len(data) else mnem+" ??"
        if kind == "addr16,A":
            return 1+extra, f"{mnem} [{fmt_imm(data, off+1, 2)}],A"
        if kind == "dir,imm8":
            return 1+extra, f"{mnem} DIR[0x{data[off+1]:02X}],{fmt_imm(data, off+2, 1)}" if off+2 < len(data) else mnem+" ??"
        if kind == "io,imm8":
            return 1+extra, f"{mnem} IO[0x{data[off+1]:02X}],{fmt_imm(data, off+2, 1)}" if off+2 < len(data) else mnem+" ??"
        if kind == "io,imm16":
            return 1+extra, f"{mnem} IO[0x{data[off+1]:02X}],{fmt_imm(data, off+2, 2)}" if off+3 < len(data) else mnem+" ??"
        if kind == "rlst":
            return 1+extra, f"{mnem} RLST(0x{data[off+1]:02X})" if off+1 < len(data) else mnem+" ??"
        if kind == "imm8,rel":
            imm = data[off+1] if off+1 < len(data) else 0
            d = data[off+2] if off+2 < len(data) else 0
            rel = d - 256 if d >= 128 else d
            target = pcrel(addr, 3 + rel)
            return 3, f"{mnem} 0x{imm:02X}, 0x{target:06X}"
        if kind == "imm16,rel":
            imm = int.from_bytes(data[off+1:off+3], "little") if off+3 <= len(data) else 0
            d = data[off+3] if off+3 < len(data) else 0
            rel = d - 256 if d >= 128 else d
            target = pcrel(addr, 4 + rel)
            return 4, f"{mnem} 0x{imm:04X}, 0x{target:06X}"
        return 1+extra, mnem

    if op == 0x6C:
        return disasm_6c(data, off, addr)

    if op == 0x6E:
        if off+2 > len(data):
            return 2, "MOVS/SCEQ/FILS ??"
        b2 = data[off+1]
        sub = (b2 >> 4) & 0xF
        names = {0:"MOVSI",1:"MOVSD",2:"MOVSWI",3:"MOVSWD",8:"SCEQI",9:"SCEQD",
                 10:"SCEQI",11:"SCEQD",12:"FILSI",14:"FILSWI"}
        return 2, f"{names.get(sub, '0x6E/'+hex(sub))}"

    if op == 0x6F:
        return disasm_6f(data, off)

    if 0x70 <= op <= 0x7F:
        return disasm_70(data, off, op, addr)

    # 0x80-0xFF: short register forms, very regular
    if 0x80 <= op <= 0xFF:
        c1 = (op >> 4) & 0xF     # opcode1c1
        c2 = (op >> 3) & 0x1     # opcode1c2 (bit3)
        reg_r = REG1R[op & 0x7]
        reg_rw = REG1RW[op & 0x7]
        if c1 == 0x8:
            return (1, f"MOV A,{reg_r}") if c2 == 0 else (1, f"MOVW A,{reg_rw}")
        if c1 == 0x9:
            return (1, f"MOV {reg_r},A") if c2 == 0 else (1, f"MOVW {reg_rw},A")
        if c1 == 0xA:
            if c2 == 0:
                return 2, f"MOV {reg_r},{fmt_imm(data, off+1, 1)}"
            else:
                return 3, f"MOVW {reg_rw},{fmt_imm(data, off+1, 2)}"
        if c1 == 0xB:
            if c2 == 0:
                return 1, f"MOVX A,{reg_r}"
            else:
                return 2, f"MOVW A,@{reg_rw}+d8({fmt_imm(data, off+1, 1)})"
        if c1 == 0xC:
            if c2 == 0:
                return 2, f"MOVX A,@{reg_rw}+d8({fmt_imm(data, off+1, 1)})"
            else:
                return 2, f"MOVW @{reg_rw}+d8({fmt_imm(data, off+1, 1)}),A"
        if c1 == 0xD:
            return 1, f"MOVN A,#{op & 0xF}"
        if c1 == 0xE:
            # spec: vct4 pointer lives at (bank | 0xFFFE - 2*n), i.e. in a table
            # at the very top of the current bank; the call is indirect through it
            n = op & 0xF
            slot = bank | (0xFFFE - 2 * n)
            return 1, f"CALL VCT4[{n}] (@0x{slot:06X})"
        if c1 == 0xF:
            cond = COND[op & 0xF]
            if off+2 > len(data):
                return 2, f"B{cond} ??"
            d = data[off+1]
            rel = d - 256 if d >= 128 else d
            target = pcrel(addr, 2 + rel)
            return 2, f"B{cond} 0x{target:06X}"

    return 1, f"DB 0x{op:02X}"


def disassemble(data, base_addr=0, start=0, count=200):
    """Linear sweep disassembly. Returns list of (addr, length, bytes_hex, text)."""
    out = []
    off = start
    n = 0
    while off < len(data) and n < count:
        length, text = disasm_one(data, off, base_addr + off)
        length = max(1, length)
        raw = data[off:off+length]
        out.append((base_addr + off, length, raw.hex(), text))
        off += length
        n += 1
    return out


if __name__ == "__main__":
    path = sys.argv[1]
    start = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    with open(path, "rb") as f:
        data = f.read()
    for addr, length, raw, text in disassemble(data, start=start, count=count):
        print(f"{addr:06X}: {raw:<10} {text}")
