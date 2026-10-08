# Handoff: BMW KOMBI (PL2) firmware reverse engineering — gear indicator box/no-box

## Goal

Two BMW E9x instrument clusters ("KOMBI", Siemens VDO, PL2 hardware family)
render the selected automatic-transmission gear letter (P/R/N/D) differently:

- **DKOML2** (owner's cluster, sourced from an E92 335i, retrofitted into an
  E90 318i) shows the gear letter **inside a square/box frame**.
- **HKOML2 / "E9XHIGH"** (a comparison "high"-trim cluster) shows the **same
  letter with no box**, plain text.

Already proven, with hard evidence, that this is **not** a BMW coding
(FSW/PSW) setting — full byte-level diff of the NCS Expert coding blob
(NETTODAT dumps) for both clusters showed the relevant flags
(`SPA_IST_GANG_ENABLE`, `GETRIEBE_ART`) are bit-identical, and none of the
16 parameters that do differ relate to gear display. So the difference is
baked into the **firmware** (or, initially considered, hardware — now ruled
out, see below).

The end goal: find the exact code/data responsible for the box, understand
it well enough to explain *why* it differs, and ideally show it can be
changed (e.g. to also drive the box appearance for other repurposed display
elements — this ties into a broader side-goal of the owner: eventually
adding fast-access board-voltage and coolant-temp readouts to a normally
visible cluster slot, using the same class of firmware understanding).

## Hard facts established so far (do not re-derive, just use)

1. **Chip confirmed by physically reading the package marking on both real
   clusters**: both DKOML2 and HKOML2 use the **identical silicon**,
   Fujitsu/Spansion **`MB90F395HA`** (F2MC-16LX core, MB90390 series). Only
   the manufacture date-code lot differs (2010 vs 2011) — same die, same
   mask. **This means the box/no-box difference is 100% software, not
   hardware capability.** Datasheet: 512 KB flash, 30 KB RAM, 24 MHz,
   24-bit address space, QFP-120.
2. The `.0pa` / `.0ba` files under `DKOML2/` and `HKOML2/` are the actual
   flash-programming images used by BMW's NCS Expert / WinKFP tooling to
   flash these clusters. Format: **plain ASCII Intel HEX** (records start
   with `:`), no container encryption. Confirmed and parsed with
   `tools/parse_ihex.py`.
3. Both firmwares use **banked 24-bit addressing**, consistent with the
   F2MC-16LX architecture:
   - a small **low bank `0x000000–0x00EFEF`** (~60 KB) present **only** in
     the DKOML2 export (`9213308A.0pa` etc.). Contents only partly
     understood — see fact #6, the earlier "vector table + dispatch code"
     reading did not hold up.
   - ~9 **upper banks `0xF80000–0xFFBFEF`** (~64 KB each, ~500 KB total) —
     present in **both** DKOML2 and HKOML2 exports. The application logic
     does live here, but only from `0xF9C000` on; see fact #5 for the
     measured code/data split.
   - HKOML2's exports do **not** include a low bank at all in what was
     provided. Unknown whether it's just not exported (shared/common
     across variants) or genuinely missing a file — worth asking the owner
     if there's additional exported material from WinKFP/ISTA for HKOML2.
4. **Naive byte-level diffing does NOT work here** (unlike the coding
   blob, which is small structured tables at fixed addresses). Evidence:
   - Diffing DKOML2's own 4 hardware-variant files
     (`9213308A/9242397A/9283870A/9347674A.0pa`, all nominally "the same"
     box-style cluster, just different physical PCB part numbers) against
     each other shows **~80% of bytes differ** in the upper banks. Each
     hardware part number is a **separately compiled and linked** firmware
     build, not a relabeled copy.
   - The low bank is more stable: `9242397A` and `9283870A` are **byte-for-
     byte identical** there; `9213308A` differs 18%, `9347674A` differs 45%.
   - Conclusion: comparing DKOML2 vs HKOML2 raw bytes will not "just show"
     a single flag the way the coding diff did. Need actual disassembly /
     structural comparison (function-level), not byte-level.
5. **Memory map (corrected 2026-08-03, measured -- supersedes the earlier
   guess that code starts at `0xF80000+0x26`):**
   - `0xF80000-0xF9BFFF` (~112 KB) is **tables/data**, not code: entropy
     3.2-5.1 with 17-62% byte self-correlation at stride 16.
   - `0xF9C000-0xFEFFFF` (~340 KB) is the **real code region**: entropy
     6.5-7.1, 2-9% self-correlation. Both firmwares agree on this split.
   - The ASCII project stamp at `0xF80000` is real, but what follows it is
     data, not logic. Disassembling `0xF80000` as code is wasted effort --
     that also explains why rendering that bank as an image looked like
     "noise": it was the wrong region.
   - Data-region differences worth a look (may be significant, may be just
     build layout -- unverified): `0xF88000-0xF8FFFF` is populated in DKOML2
     but 60%+ erased in HKOML2; `0xFEC000-0xFF7FFF` is fully erased in
     HKOML2 but populated in DKOML2.
6. **The low-bank "interrupt vector table + trampolines" reading is NOT
   confirmed -- treat it as disproven-ish (revised 2026-08-03).** The bytes
   at `0x55B3` and every 10 bytes after are fixed-layout records:
   `B1 B7 81 4C 9A <2 varying bytes> 9B EC 55`. They do not decode as code:
   the trailing `55` is `MOVX A,io`, which needs one more byte and so eats
   the first byte of the next record. That is a **data table**, and the
   "10 bytes per handler" match was pattern-fitting. Also, the real
   F2MC-16LX vector table lives at the top of bank `0xFF`, not at address 0.
   Don't build on the low bank; the code that matters is in `0xF9C000+` and
   is present in BOTH firmwares anyway.
7. Chip's official architecture reference: Fujitsu Programming Manual
   `CM44-00201-3E` (F2MC-16LX), available on bitsavers:
   https://bitsavers.trailing-edge.com/components/fujitsu/f2mc-16/F2MC-16LX/CM44-00201-3E_F2MC-LX_Programming_Manual.pdf
   — use this to verify/extend opcode handling, it's the ground truth.
8. A community-made **Ghidra processor module** for F2MC-16LX already
   exists (disassembly works, pcode is partial/incomplete per its own
   notes): https://github.com/mehmooda/F2MC-16LX — its
   `data/languages/F2MC.slaspec` file is a complete, authoritative,
   human-readable opcode table (SLEIGH DSL). `tools/f2mc_disasm.py` in this
   folder was hand-ported from that file. If the hand-rolled disassembler
   turns out insufficient, the next escalation is to actually build this
   Ghidra module (Gradle + JDK, both available in a typical dev sandbox)
   and run full Ghidra headless analysis instead of the MVP script.
9. Dead ends already explored, don't repeat:
   - `ECUFunctions/*.xml` in the BMW disk's ISTA install and `DiagDocDb.sqlite`
     (ISTA's documentation DB) — the sqlite file is **encrypted** (header
     doesn't match SQLite magic bytes), and ECUFunctions XML is just
     parameter-name translation cache. Neither has chip/hardware info.
   - WDS (Wiring Diagram System) fundamentally documents wiring/connectors,
     not internal PCB/chip design — even a working WDS session was very
     unlikely to reveal the MCU part number (this was confirmed moot once
     the chip was ID'd by physically reading the package).
   - String-searching the `.0pa` files for chip-family markers (H8S, F2MC,
     MB90, C167, V850, etc.) gave false positives (coincidental hex-digit
     matches inside the Intel HEX data, not real text labels) before the
     chip was identified physically. Physical inspection was the only
     reliable path — don't waste time trying to re-derive chip ID from the
     binary alone if it's ever in question again.

## Files in this folder

```
DKOML2/                  Intel HEX flash images + metadata for the "box" cluster
  9213308A.0pa, 9242397A.0pa, 9283870A.0pa, 9347674A.0pa   -- 4 HW-variant firmware images
  DKOML2.DAT             -- valid HW/SW-index combinations ("Zusbauvorschrift")
  DKOML2.HIS             -- flash history log
  DKOML2.HWH             -- hardware history log
  H01028K_0102FH.0ba     -- bootloader/flash-programming image

HKOML2/                  same, for the "no box" / "high" cluster (9 HW variants)

080100HKOML2.ipo,
080101DKOML2.ipo         NCS Expert flash-programming job scripts (bootloader
                         logic: Authentisierung -> FLASH_LOESCHEN -> FLASH_SCHREIBEN
                         -> signature check). Confirms: writing a patched image back
                         via the official flash job requires passing a challenge-
                         response auth AND a post-write signature check
                         (FLASH_SIGNATUR_PRUEFEN in komb87.prg) -- a naive "patch and
                         reflash via WinKFP" plan will very likely be rejected unless
                         that signature scheme can be satisfied or bypassed. Treat
                         firmware patching as a read/understand exercise for now, NOT
                         a "flash it back" plan, until that's solved.

10flash.prg              generic EDIABAS flash-parameter job file (BIP 06.04.00,
                         2007) -- not KOMBI-specific, mentions "Power-PC" only in a
                         generic multi-ECU AIF-size comment. Not a useful lead.

ANALYSIS_NOTES.md        Running research log -- READ THIS FIRST, it has the full
                         narrative history of the investigation with more detail
                         than this handoff doc.

tools/
  parse_ihex.py          Intel HEX -> {address: byte} dict + segment list.
                         `python3 parse_ihex.py <file.0pa>` to inspect any file.
  dump_flat.py           .0pa -> flat binary (gaps filled 0xFF), for feeding a
                         disassembler or Ghidra/IDA import.
                         `python3 dump_flat.py <in.0pa> <out.bin> [lo] [hi]`
  diff_hex.py            byte-level diff of two .0pa files over an address range,
                         grouped into contiguous runs.
                         `python3 diff_hex.py <a.0pa> <b.0pa> [lo] [hi]`
  f2mc_disasm.py         F2MC-16LX instruction decoder (see below).
                         `python3 f2mc_disasm.py <flat.bin> [start_addr] [count]`
  f2mc_cfg.py            Recursive-descent disassembler / function finder.
                         Follows CALL/JMP/branches, stops at RET, emits a
                         function table with mnemonic-sequence signatures.
                         `python3 f2mc_cfg.py <f.0pa> --range 0xF9C000,0xFF0000 --json out.json`
                         `python3 f2mc_cfg.py <f.0pa> --func 0xFA012D`  (dump one function)
  f2mc_batch.py          Analyze ALL variants of both families in parallel.
                         Auto-detects the code region per file by entropy.
                         `python3 f2mc_batch.py /tmp/fw DKOML2/*.0pa HKOML2/*.0pa`
  f2mc_family.py         Family-level comparison with a built-in control:
                         reports within-family vs across-family agreement,
                         then signatures unanimous in one family and absent
                         from the other.  `python3 f2mc_family.py /tmp/fw`
  f2mc_pairdiff.py       Re-pairs family-discriminating functions by sequence
                         similarity and prints the differing region, since a
                         one-instruction change otherwise appears as two
                         unrelated entries.  `python3 f2mc_pairdiff.py /tmp/fw`
  f2mc_compare.py        Structural DKOML2-vs-HKOML2 comparison from two
                         f2mc_cfg JSON dumps. Filters to call-confirmed
                         entries in the code region, then matches on
                         operand-free mnemonic signatures.
                         `python3 f2mc_compare.py dk.json hk.json`
  F2MC-16LX/             Cloned github.com/mehmooda/F2MC-16LX -- the SLEIGH
                         spec used as ground truth for the opcode table.
```

## State of `f2mc_disasm.py` — what works, what doesn't

**Solid / verified by hand-tracing:**
- All fixed-length opcodes `0x00–0x6B` (NOP, MOV/MOVW/MOVL/MOVX variants,
  ADD/SUB/CMP/AND/OR/XOR families, PUSHW/POPW, BRA/JMP/JMPP/CALL/CALLP/RET/
  RETP/INT/INTP/RETI).
- The `0x80–0xFF` short register-form block (very regular nibble-based
  encoding: `MOV`/`MOVW`/`MOVX` to/from `R0-R7`/`RW0-RW7`, `MOVN`,
  `CALL VCT4[n]`, `Bcc rel`).
- Instruction **length** computation for everything above is correct (this
  matters most for staying byte-aligned during a linear sweep).

**Approximate / needs real work:**
- ~~`0x6C` (bit ops)~~ — **DONE (2026-08-03)**, see below.
- `0x6E` (block move / fill / scan: MOVSI/MOVSD/MOVSWI/MOVSWD/SCEQI/SCEQD/
  FILSI/FILSWI) — mnemonic-only, no operand rendering.
- `0x6F` (extended ALU ops incl. MUL/DIV/ROLC/LSL family on `@A`/bank
  registers) — mnemonic-only in most cases, some length special-cases
  hardcoded from spot-checking the spec, not exhaustively derived.
- **`0x70–0x7F` — DONE (2026-08-03).** Full addressing-mode decode ported
  from `F2MC.slaspec`'s `ear`/`earw`/`earl`/`v70var` productions (the repo
  is cloned locally at `tools/F2MC-16LX/`). Implemented in `disasm_70()` +
  `_ext_addr_operand()`/`_ext_operand()`/`_H3_TABLE` in `f2mc_disasm.py`.
  Renders real operands: `@RWn+d8`, `@RWn+d16`, `@RWn+RW7`, `@DTB:RWn` /
  `@ADB:RW2` / `@SSB:RW3` (bank is hardwired to the register index for the
  `b34=1` indirect form — RW0/RW1→DTB, RW2→ADB, RW3→SSB), PC-relative
  `REL[addr]`, absolute `[addr16]`. Verified: all 4096 `(opcode, byte2)`
  combinations decode without exceptions with sane instruction lengths;
  spot-disassembly of real DKOML2 code produced plausible instructions.
  Known simplification: prefix-override bytes (`PCB:`/`DTB:`/`ADB:`/`SPB:`,
  opcodes `0x04-0x07`) that would override the default DTB bank on
  `@RWn+d8`/`@RWn+d16` forms are not tracked across instructions (decoder
  is per-instruction, not stateful) — operands from those forms are
  rendered without an explicit bank tag.
- **`0x6C` (bit ops) — DONE (2026-08-03).** The most important group for this
  project: every lamp/indicator/flag in cluster firmware is a bit, so "does
  this display element get a box?" most likely lives as a
  `SETB`/`CLRB`/`BBC`/`BBS` on a display flag byte. Byte2 layout: `[7:5]`
  operation, `[4:3]` addressing mode (0=io 1B, 1=dir 1B, 3=addr16 2B, 2=not
  defined by the spec), `[2:0]` bit number. **A real length bug was found and
  fixed here**: operation 7 is `WBTC` in io mode (NO trailing rel byte) but
  `SBBS` in addr16 mode (WITH one) — the old code always added the rel byte
  for operation 7, which would shift every following instruction by one.
  Still not done: `0x6E`/`0x6F` (rare, mnemonic-only).

**Other bugs found and fixed while building the CFG tool (2026-08-03):**
- `JMP`/`CALL addr16` (`pcaddr16`) ignored the bank. For code in bank `0xF8`
  the target is `0xF8xxxx`; the bare `addr16` was being printed. Now taken
  from PCB, i.e. the instruction's own bank.
- PC-relative targets were computed flat. The F2MC-16LX PC is 16-bit inside a
  bank and does NOT carry into the bank number — added `pcrel()` and moved
  all 8 target computations onto it.
- In `0x70-0x7F` the PC-relative form was computed from the end of the
  instruction; the spec says `reloc = inst_start + d16`, i.e. from the start.
- Cosmetic: `f"[0x{fmt_imm(...)}]"` printed a doubled prefix (`[0x0x1234]`).
## State of `f2mc_cfg.py` (recursive-descent) — works, validated

Follows `CALL`/`CALLP`/`JMP`/`JMPP`/conditional branches, stops at
`RET`/`RETP`/`RETI`, memoizes decoded instructions, and emits a function
table (entry, size, calls, mnemonic-sequence signature). A far `JMP` (other
bank, or >0x4000 away) is treated as a tail call rather than inlined —
otherwise one jump merges half a bank into a single "function".

Seeding: scan for `LINK #imm8` (0x08, the standard frame prologue) plus
pointers from the `CALL VCT4` tables.

**Validation on bank `0xFA0000-0xFB0000`:**

| | DKOML2 | HKOML2 |
|---|---|---|
| LINK seeds | 1025 | 776 |
| clean functions (reach RET, not truncated, <5% junk) | 971 (94.7%) | 757 (97.6%) |
| undecodable bytes | 3 of 137046 insns | 0 of 125514 |

Sample output — reads like real code (an interrupt-disabled critical section):

```
FA012D: LINK 0x00           ; prologue
FA012F: AND CCR, 0xBF       ; disable interrupts
FA0131: BBC [0x037F]:2, ... ; test a bit
FA0136: SETB [0x036B]:3
FA013D: BZ ...
FA013F: SETB [0x036B]:4     ; "yes" branch
FA0145: CLRB [0x036B]:4     ; "no" branch
FA0149: OR CCR, 0x40        ; re-enable interrupts
FA0178: UNLINK / RETP       ; epilogue
```

Known limitations: indirect flow (`JMP @A`, `JMP earw`, `CALL earw`, `JCTX`)
ends a path unresolved; bank-override prefixes aren't tracked across
instructions; `CALL VCT4[n]` resolves only for n=8..15 (the pointer table is
in the top 32 bytes of a bank and the `.0pa` exports stop at `0xXXFFEF`).

## ★ PRIME CANDIDATE FOUND (2026-08-03): gear-indicator attribute table

A 4-byte field sits immediately before the gear-indicator character table in
the data region, and it separates the two families perfectly:

| Family | 4 bytes before the character table | Variants |
|---|---|---|
| DKOML2 (box) | **`01 02 01 01`** | **4 of 4** |
| HKOML2 (no box) | `00 00 00 FF` (filler) | **9 of 9** |

**13 of 13 firmwares, no exceptions.** Not build noise: each of the 13 files
places the table at its own address (different link layout), yet the contents
of this field track the family exactly.

The character table itself is identical in both families (61 bytes):

```
" 1234567         <>      1234567     PRPN NND        SM     C"
      ^^^^^^^                ^^^^^^^      ^^^^^^^^        ^^
      gear numbers           numbers      P R N D         Sport/Manual
```

**How it was found:** not by disassembly, but by ASCII-string search in the
`0xF80000-0xF9BFFF` data region (the one the entropy map identified as
tables). The `PRND`+digits string exists in both firmwares; comparing its
surroundings exposed the 4-byte difference.

**Code-side confirmation.** Every indexed table lookup (the idiom
`ZEXTW; ADDL A,#imm32; MOVL RL2,A`) was enumerated: 41 in DKOML2, 36 in
HKOML2. The gear-display table group maps one-to-one between families:

| DKOML2 | HKOML2 | contents |
|---|---|---|
| **`0xF83C60` <- code `0xFAFB83`** | **absent, zero references** | **`01 02 01 01`** |
| `0xF83C64` <- `0xFAFCCC` | `0xF82000` <- `0xFBF75F` | " 1234567..." |
| `0xF83C74` <- `0xFAFCBC` | `0xF82010` <- `0xFBF74E` | " <>" |
| `0xF83C78` <- 4 sites | `0xF82014` <- 4 sites | gear numbers |
| `0xF83C88` <- 2 sites | `0xF82024` <- 2 sites | " PRPN NND" |
| `0xF83C98` <- 2 sites | `0xF82034` <- 2 sites | " SM" |
| `0xF83CB8` <- `0xFBD0E3` | `0xF82054` <- `0xFBFC9C` | numeric table |

**Every table in the group has an exact counterpart except one.** DKOML2
performs one extra indexed lookup that HKOML2 does not.

The lookup (DKOML2 9213308A, inside function `0xFAFAA6`):

```
FAFB80: MOV  A, [0x0CFD]        ; index/selector from RAM
FAFB83: ZEXTW
FAFB84: ADDL A, 0x00F83C60      ; + base = the 01 02 01 01 block
FAFB89: MOVL RL2,A              ; RL2 = &attr[index]
FAFB8B: MOV  A,@RL2+0x00        ; A = attr[index]
FAFB8E: MOVW [0x0CF6],A         ; result to RAM 0x0CF6
```

RAM tracing: `0x0CFD` (index) has 3 accesses, all inside the gear module
(`0xFAF824` write, `0xFAFB80` read, `0xFAFDA7` write). `0x0CF6` (result) has
4 writes and exactly **one** read -- a getter at `0xFAFEFD` ("if condition
return 0, else return RAM[0x0CF6]").

**Why this is probably the feature.** The DKOML2 board is marked
`PL2-DKG E89` -- DKG = Doppelkupplungsgetriebe, the dual-clutch box. The
frame around the gear letter is most likely the standard DKG gear-display
style, i.e. a deliberate variant feature. `01 02 01 01` looks like a
"render style per index" table for 4 indices.

**NOT yet proven:** the path from `RAM[0x0CF6]` to the actual frame drawing.
What IS proven: (a) the field separates the families across all 13
firmwares, (b) it sits inside the gear-indicator data group, (c) DKOML2 has
a dedicated lookup for it while HKOML2 has no reference to that location at
all, (d) it is the only table in the group without a counterpart.

## Negative result: the 96 "same shape" functions were a dead end

Worked through as planned. The tightest candidates turned out to be:

1. **Equivalent codegen.** Pair `0xFA2545`/`0xFA16B2`: box does
   `MOVN A,#3; ANDW A`, no-box does `AND A, 0x03` -- the same "mask with 3".
2. **The same thing hidden by operand width.** Pair `0xFA66BA`/`0xFA57D7`
   (similarity 0.9997): box masks `& 0x0001`, no-box `& 0xFF01`. Looks like
   a real difference, but the result is stored with a **byte** instruction
   (`MOV @RW5+0x00,A`), so the high bits are discarded and both masks are
   equivalent.
3. **Diff-alignment artifacts.** With repeated mnemonics SequenceMatcher
   picks an arbitrary insertion point, so the "difference" lands on an
   instruction present in both.

The "different compiler versions" hypothesis was tested and **rejected**:
the `MOVN->ANDW` idiom occurs at 93.6 vs 95.2 per 10k instructions, and
mnemonic distributions match overall (ratios 0.89-1.21).

A methodology bug was also fixed: box-only functions were initially matched
only against nobox-only functions, but a function can be present in SOME
HKOML2 variants and land in neither list. Matching against the full HKOML2
pool (1971 signatures from 9 variants) cut "103 unique" down to 62. The
largest of those, `0xFEC638`, disassembles to a peripheral-shutdown routine
(clears `IO[0x2D]`, `IO[0x5E]`, `IO[0x50]`... per mask bit) -- unrelated to
display.

**Lesson:** mnemonic-sequence comparison is simultaneously too coarse (it
drops the operands where constants live) and too brittle (any equivalent
re-encoding breaks the hash). Searching the DATA was far more productive
than searching the code.

## Cross-check against the DBC-mega-merge project (2026-08-03)

`/Users/densh/Work/Develop/BMW/DBC-mega-merge`
(github.com/Maseg535/E90-and-e8x-DBC-mega-merge-project) had NOT been used
in the firmware work before -- an oversight, it is directly relevant.
386 messages, 430 signals, with empirical HIL-bench additions.

**`0x1D2` (466) `TransmissionDataDisplay`, EGS -> Kombi:**

| Signal | Bits | Meaning |
|---|---|---|
| `ShiftLeverPosition` | 0-3 | 1=P, 2=R, 4=N, 8=D (HIL-validated) |
| `GearAct` | 12-15 | raw-4 = gear 1..6, only in Sport/Manual |
| **`ShiftLeverMode`** | **32-33 (2 bits)** | **0=Drive/Normal, 2=Sport/Manual** |
| `xFF` | 40-47 | **M3 DCT-specific mode byte**; always 0xFF on ZF 6HP19 |

DBC comment: *"Dashboard shows D1-D6 in Normal, S1-S6 in Sport, M1-M6 in
Manual."*

**Two independent matches with the attribute table found in firmware:**

1. `ShiftLeverMode` is a **2-bit** field -> 4 possible values. The table
   `01 02 01 01` is exactly **4 bytes**. A 2-bit field indexing a 4-byte
   table fits.
2. The firmware character table maps onto the documented behaviour:
   `" 1234567  <>  1234567  PRPN NND  SM  C"` -- gear digits, the letters
   `P R N D`, and **`SM`** = Sport / Manual, precisely the modes the DBC
   documents.

`0x304` (772) `GearDisplay` enumerates selector states (0xE3=Park,
0xC2=Reverse, 0xD1=Neutral, 0xC5..0xCA=Gear1..6). DKG is its own bus node
with `0x0B8 Torque_request_DCT`, `0x37D Status_DKG`, and `0x3B1
TransmissionData3` (the last one received by Kombi).

**Community corroboration.** e90post / NA M3 / SpoolStreet threads agree
that DCT/DKG cars show the gear differently in the cluster, and that
attempts to get the DCT gear display on a normal automatic **by coding
alone have failed** -- which matches this project's own earlier proof that
the FSW/PSW blobs are bit-identical. External sources therefore
independently support the conclusion that this is a cluster-variant trait,
exactly what the 4/4 vs 9/9 split of `01 02 01 01` shows.

**What did NOT work (do not repeat).** Trying to locate the CAN filter
table in the firmware failed two ways: (a) searching CAN IDs as 2-byte
values is pure noise -- in 500 KB any byte pair occurs dozens of times, so
every ID "appears" in every firmware; (b) searching for runs of ascending
IDs at a constant stride returns artifacts (incrementing byte patterns like
`0B1 0B3 0B5 0B7...`), and the high "% known to DBC" only reflects how
dense real IDs are in the 0x0A0-0x0C0 range. The right approach: the
MB90F395HA has an **on-chip CAN controller**; message IDs are written by
init code into its I/O registers, so look for that init code, not for a
constant table in the data region.

**github.com/topics/e90** -- 8 repos, little new: `veikkos/e90-can-cluster`
and `ilicmiljan/open-can-controller` were already in this document's
reference list (veikkos confirms the cluster shows gear + a "gear
extension" M/S/P/A/N, but documents neither the box nor trim differences);
`Maseg535/E90-and-e8x-DBC-mega-merge-project` is the local DBC project
above and is by far the most useful; the rest
(`kmalinich/node-bmw-client`, `nberlette/bmw-dbc`,
`TeksuSiK/e87-cluster-simhub`, `foxpress-design/BimmerDimmer`) are bus/sim
tooling with no bearing on firmware internals.

## ★ 0x1D2 parser found; the 0x0CFD hypothesis is REFUTED but the chain closes

**Method:** not by hunting the CAN ID (that had already failed) but backwards
from the variable. `0x0CFD` had two writers; `0xFAFDA7` turned out to be a
bulk reset (`MOVN A,#0` then a run of stores). The real source is `0xFAF824`
inside function `0xFAF7FF`.

```
FAF801: CLRB [0x2632]:0          ; clear "message updated" flag
FAF805: [0x4140] & 0x0F -> [0x0D02]    ; B0 bits 0-3
FAF80D: [0x4141] >> 4   -> [0x0D01]    ; B1 bits 4-7
FAF817: [0x4144] & 0x0F -> [0x0D00]    ; B4 bits 0-3
FAF81F: [0x4141] & 0x03 -> [0x0CFD]    ; B1 bits 0-1   <-- our index
FAF827: BBS [0x09FB]:3, FAF856         ; coding-bit gate
FAF82C: [0x4145] nibbles -> [0x0D07]   ; B5
FAF856: BBS [0x2632]:0, FAF801         ; updated mid-read -> re-read
FAF85D: RET
```

The `CLRB flag` ... `BBS flag, loop` bracket is a lock-free re-read loop --
how you read a buffer an ISR can overwrite, confirming `0x4140` is a CAN
receive buffer.

**Field-by-field against DBC `BO_ 466` (DLC 6):** B0 bits 0-3 =
`ShiftLeverPosition`; B1 bits 4-7 = `GearAct`; B4 bits 0-3 covers
`ShiftLeverMode`; B5 = `xFF` (the M3 DCT byte). Six consecutive bytes
`0x4140-0x4145` are read and the DBC DLC is 6. Five independent fields match.

**REFUTED:** `0x0CFD` is **not** `ShiftLeverMode`. That signal lives in byte
4 (bits 32-33) and the firmware puts it in `0x0D00`. `0x0CFD` is **byte 1,
bits 0-1** -- and the DBC does not describe bits 8-11 of `0x1D2` at all
(0-3 = ShiftLeverPosition, 4-7 = its XOR, 12-15 = GearAct). So it is an
**undocumented 2-bit field**. The shape of the hypothesis (a 2-bit field
from 0x1D2 indexes the 4-byte table) held; the specific field did not.

**Third independent family split.** Scanning all 13 firmwares for the idiom
`MOV A,[src]; MOVN A,#3; ANDW A; MOV [dst],A`: the extraction from
`[0x4141]` is present in **4 of 4** DKOML2 and **0 of 9** HKOML2. The source
address `0x4141` is identical across all four DKOML2 builds while the
destination moves (`0x0CFD`, `0x0B11`, `0x0B23`, `0x0B24`) -- so the buffer
sits at a fixed address rather than being compiler-allocated.

**Side by side.** HKOML2 (9119936B, `0xFBF39E`, buffer base `0x0332`) parses
the same message with the same layout -- B0 low nibble, B1 high nibble,
B4 (= base+4) low nibble, then the same coding-bit gate -- and **differs by
exactly one extraction: DKOML2 additionally takes B1 bits 0-1.** DKOML2 also
handles B5 (the DCT byte) whereas HKOML2's gate body is empty (its branch
targets the very next instruction).

**The data path is now closed except for the last hop:**

```
CAN 0x1D2, byte 1, bits 0-1     (undocumented; only DKG clusters read it)
  -> RAM[0x0CFD]                (FAF824)
  -> index into table 0xF83C60  (FAFB84, ADDL A,#0x00F83C60)
     contents: 01 02 01 01      (4/4 DKOML2, 0/9 HKOML2)
  -> RAM[0x0CF6]                (FAFB8E)
  -> getter 0xFAFEFD            (its only reader)
  -> ??? rendering              (still unproven)
```

Three independent family splits now support it -- the data table, the lookup
into it, and the CAN field feeding it -- each 4/4 versus 0/9.

**Worth contributing back to the DBC project:** `0x1D2` byte 1, bits 0-1 is
an undocumented 2-bit signal read only by DKG clusters, driving the gear
display style. The DBC currently leaves bits 8-11 of that message undefined.


## ★★ ЦЕПОЧКА ЗАМКНУТА: найден код, рисующий рамку (2026-08-03)

Геттер `0x0CF6` — это функция с входом **`0xFAFEB3`** (не `0xFAFEFD`, это
инструкция внутри неё). Возвращает атрибут только если
`([0x09FB] >> 6) == 2` (двухбитное поле кодирования), иначе 0.

**Вызывающий ровно один: `0xFE6197`**, внутри функции **`0xFE616F`** — и это
оказался код отрисовки индикатора передачи. Признаки: `CBNE A, 0x20`
(сравнение с ASCII-пробелом из найденной таблицы символов), сборка строки из
1 или 2 символов (`D` против `D3`/`S4`), центрирование
`SUBW A,@RW3-0x0E; NEGW A; LSRW A` = `(ширина − ширина_текста)/2`.

Атрибут кладётся в `RW6` (`FE619C`) и используется в трёх местах:

```
FE6257: A=RW6 / CMPW #2 / BNZ →   ; если 2 — тикает таймер мигания:
FE625C:   now=[0xF9FF7A]; if now-[0x180C] > 50 -> инвертировать [0x2CDE]

FE62DD: A=RW6 / CMPW #1 / BZ  → FE62EC   ; атрибут 1 -> рисовать рамку
FE62E2: A=RW6 / CMPW #2 / BNZ → FE6346   ; не 2 -> без рамки
FE62E7: A=[0x2CDE] / BZ       → FE6346   ; 2: рамка только в фазе мигания
FE62EC: ─────── блок отрисовки рамки ───────
FE6346: ─────── только текст, без рамки ───
```

Блок `FE62EC`:

```
FE62EC: MOVL A,0xAAAAAAAA -> CALLP [0xFDBA65]   ; 50% дизер-узор пера
FE62F9: PUSHW RW0,RW2, #2      -> CALLP [0xFDBE94]  ; горизонт. линия (верх)
FE630A: PUSHW RW0,RW2, RW4-1   -> CALLP [0xFDBE94]  ; горизонт. линия (низ)
FE6318: PUSHW RW2, #3, A-2     -> CALLP [0xFDBED7]  ; вертик. линия (лево)
FE6329: PUSHW RW0, #3, A-2     -> CALLP [0xFDBED7]  ; вертик. линия (право)
FE633A: ...                    -> CALLP [0xFDBC98]  ; затем сам текст
```

Что это горизонталь и вертикаль — проверено по самим примитивам. Оба
сдвигают координаты на начало окна (`[0x1716]`=X, `[0x1718]`=Y):
- `0xFDBE94` прибавляет X к **двум** аргументам и Y к **одному**
  → две X-координаты + одна Y = **горизонтальная линия** (→ `0xFDEA3B`)
- `0xFDBED7` прибавляет X к **одному** и Y к **двум**
  → одна X + две Y = **вертикальная линия** (→ `0xFDEAC2`)

Две горизонтальные + две вертикальные = **контур прямоугольника вокруг
символа передачи. Это и есть искомый квадратик.**

### Полная цепочка от шины до пикселей

```
CAN 0x1D2, байт 1, биты 0-1      недокументированное поле, читают только DKG
  -> RAM[0x0CFD]                 FAF824   (4/4 DKOML2, 0/9 HKOML2)
  -> attr = [0xF83C60][индекс]   FAFB84/FAFB8B, таблица 01 02 01 01
  -> RAM[0x0CF6]                 FAFB8E
  -> геттер 0xFAFEB3             гейт ([0x09FB]>>6)==2
  -> рендер 0xFE616F, attr->RW6  FE619C
  -> attr==1 : рамка постоянная
     attr==2 : рамка мигающая (период 50 тиков)
     иначе   : только текст, без рамки
  -> рамка = 2 гориз. + 2 вертик. линии = прямоугольник
```

Значения таблицы `01 02 01 01` теперь читаются осмысленно: индексы 0, 2, 3
дают **1** (рамка постоянно), индекс 1 даёт **2** (рамка мигает). У HKOML2
таблицы нет, выборки нет, атрибут не вычисляется — ветка рисования рамки
никогда не достигается.

### Оговорка о границах доказанного

Примитивы линий (`0xFDBE94`/`0xFDBED7`) и узор `0xAAAAAAAA` присутствуют в
**обоих** семействах (узор встречается 6-8 раз в каждой прошивке) — они
общего назначения и используются другими элементами интерфейса. Различие не
в наличии рисующего кода, а в том, что HKOML2 никогда не вычисляет атрибут,
который бы эту ветку включил. Именно это и подтверждают три независимых
семейных разделения со счётом 4/4 против 0/9.


## ⚠️ ПОПРАВКА от владельца (2026-08-04): рамка НЕ связана с типом коробки

Denis сообщил эмпирические данные, опровергающие интерпретацию «рамка = стиль
отображения DKG»:

- у него **обычная АКПП ZF 6HP**, а квадратик рисуется;
- по опросу других владельцев квадратик есть и с **GM 6L45**.

Привязка к DKG была натяжкой: она строилась на маркировке платы
`PL2-DKG E89` и форумных обсуждениях, а не на коде. **Считать опровергнутой.**

### Но код это предсказывал — надо было заметить раньше

Таблица по `0xF83C60` — ровно 4 байта `01 02 01 01`, а индекс маскируется
`& 0x03` (максимум 3). Значит:

| Индекс | Атрибут | Что рисуется |
|---|---|---|
| 0 | 1 | рамка сплошная |
| 1 | 2 | рамка **мигающая** |
| 2 | 1 | рамка сплошная |
| 3 | 1 | рамка сплошная |

**Значения 0 в таблице нет.** Раз `attr==1` и `attr==2` оба ведут в блок
отрисовки рамки (`FE62DD`/`FE62E2`), то при работе этой ветки рамка
рисуется ВСЕГДА, независимо от коробки. Наблюдения владельцев полностью
согласуются.

**Что на самом деле делает двухбитное поле CAN:** выбирает не «рамка или
нет», а **сплошная против мигающей**. Мигание — только при индексе 1
(таймер на `FE6257`, период 50 тиков, фаза в `[0x2CDE]`).

Итог: различие box/no-box определяется **исключительно вариантом прошивки**
(DKOML2 против HKOML2), а не тем, какая коробка стоит в машине. Все три
семейных разделения 4/4 против 0/9 говорят именно об этом.

### Единственный путь «без рамки» внутри самой DKOML2

Геттер `0xFAFEB3` возвращает 0 (рамки не будет), если
`([0x09FB] >> 6) != 2` **И** `DIR[0x71] < 4` (`0xFC8D66` — это просто
`MOV A, DIR[0x71]; RETP`). При 6-ступенчатой коробке второе условие не
выполняется, поэтому рамка и появляется. Это более интересный рычаг, чем
поле CAN, — и его стоит копать для конечной цели проекта.

### Нужен ли лог с машины

Для объяснения квадратика — **нет**, вопрос закрыт кодом. Лог ответил бы
только на узкий вопрос: принимает ли поле `0x1D2` байт 1 биты 0-1 значение
1 на конкретной машине (тогда рамка должна мигать).

**Более дешёвая проверка модели, без оборудования:** видел ли владелец
когда-нибудь, чтобы квадратик мигал? Если нет — поле на его машине никогда
не равно 1. Это бесплатно фальсифицирует или подтверждает разбор.


## Разбор 0x09FB и DIR[0x71] (2026-08-04)

Мигания владелец не наблюдал никогда → поле `0x1D2` байт1 биты0-1 на его
машине никогда не равно 1. Согласуется с таблицей: индексы 0/2/3 дают
сплошную рамку.

### 0x09FB — центральный конфигурационный байт

**133 чтения и НОЛЬ записей** во всём кодовом регионе (у соседних адресов
`0x09E2`, `0x09F2`, `0x09F4`, `0x09F8` нормальные пары чтение/запись — то
есть это не артефакт поиска). Значит байт заполняется при инициализации
блочным копированием, а не обычной записью.

Используется по всей прошивке:
- **бит 3** — гейт примерно тридцати поведений (`BBS/BBC [0x09FB]:3`),
  включая обработку байта B5 в распаковщике `0x1D2`
- **биты 4 и 5** — проверяются отдельно (`MOVB A,[0x09FB]:4/:5`)
- **биты 6-7** — двухбитное значение, сравнивается с 2 в геттере рамки

### DIR[0x71] = адрес 0x0171

`DIR` — прямая страница, эффективный адрес `DPR:adir`. Инструкция
`MOV DPR,A` (`6F 14`) в кодовом регионе **отсутствует** (95 совпадений
байтовой пары нашлись только в области данных `0xF88xxx` — случайные).
Значит DPR остаётся сброшенным значением `0x01`, и `DIR[0x71]` = `0x0171`.

**7 чтений, ноль записей** — тоже конфигурационное значение. Все семь в
плотном блоке `0xFC8CAD-0xFC8D66`, где оно используется как **индекс в три
таблицы указателей на функции**:

```
FC8CAD: A = DIR[0x71] ; ZEXTW ; A *= 2
FC8CB4: ADDL A, 0x00F84084      ; база (ещё две: 0xF84078, 0xF8406C)
FC8CBB: MOVW A,@RL2+0x00        ; загрузить указатель
FC8CBF: CALL RW4                ; косвенный вызов
```

Таблицы идут с шагом 12 байт → по 6 записей → **диапазон DIR[0x71] = 0..5**.
Функция границы `0xFC882C` подставляет 6 по умолчанию (`MOVN A,#6`), что
согласуется. `0xFC8D66` — тривиальный аксессор `MOV A, DIR[0x71]; RETP`.

### ⚠️ Направление сравнения: спека сообщества ненадёжна

Для `CMPW A` (опкод 0x2B) `F2MC.slaspec` сам себе противоречит: флаги V и C
считаются от `AL - AH`, а Z/N — от `AH - AL`. Это ровно тот случай, про
который сам модуль пишет, что pcode неполон.

**Разрешено эмпирически**, по коду с однозначной семантикой (`0xFE627D`):
`RW0` там равен 1 или 2 (число символов), а ветки дают ширину `0x1C`=28 и
`0x25`=37. Два символа обязаны получать более широкую рамку. Значит `BLE`
срабатывает при `RW0=1` — то есть шаблон `MOVN A,#k; CMPW A; Bcc` читается
как **«загруженное_значение cc k»**, а не наоборот.

### Итоговое условие рамки

```
attr = 0 (рамки НЕТ)  <=>  ([0x09FB] >> 6) != 2  И  DIR[0x71] < 4
иначе                      attr = таблица[индекс] = 1 или 2 -> рамка есть
```

При шестиступенчатой коробке `DIR[0x71]` (диапазон 0..5) не меньше 4,
поэтому рамка рисуется — **это согласуется и с ZF 6HP владельца, и с
сообщениями про GM 6L45**. Модель предсказывает наблюдаемое.

### Практический вывод

Внутри самой DKOML2 путь «без рамки» существует, но управляется **двумя
конфигурационными значениями, а не кодом и не полем CAN**. Ни одно из них
код не пишет — оба заливаются при инициализации.

Важная оговорка: то, что они не пишутся в кодовом регионе, **не доказывает**,
что источник — именно кодирование (FSW/PSW). Это может быть EEPROM,
блочное копирование через указатели или код инициализации вне
просканированного диапазона. Проверять отдельно.

Косвенное соображение: побайтово идентичные блоки кодирования у обеих
приборок означают, что эти значения в них одинаковы, то есть они **не
являются причиной** различия box/no-box (причина — наличие таблицы
атрибутов). Но потенциальным рычагом для управления рамкой они остаются.


## Поиск кода инициализации 0x09FB / 0x0171 — упёрся в стену (2026-08-04)

Что проверено и с каким результатом:

1. **Прямых записей нет нигде во всём образе** — ни `MOV [0x09FB],A` (0x53),
   ни `MOVW` (0x5B), включая низкий банк. Не только в кодовом регионе.
2. **DPR не переустанавливается** — `MOV DPR,A` (`6F 14`) в кодовом регионе
   отсутствует; 95 совпадений байтовой пары нашлись только в области данных
   `0xF88xxx` и являются случайными. Значит `DIR[0x71]` = `0x0171`.
3. **Записей в DIR[0x71] нет** ни одной выровненной (7 обращений, все чтения).
   Два кандидата в низком банке (`0x000D17`, `0x001677`) не проверены на
   выравнивание — низкий банк как код пока не разобран.
4. **Immediate-загрузки адресов рядом** (`0x09F0`, `0x09D6`, `0x09F5`...)
   ведут не в инициализацию, а в **диагностический слой**: рядом `MOVSI`
   (блочная пересылка) с буферами и идентификатором `0xE7`, плюс
   `CLRB [0x09F1]:1`. То есть блок `0x09Dx-0x09Fx` обслуживается диагностикой,
   и `0x09FB` лежит внутри него.

**Вывод:** оба значения пишутся блочным копированием, адрес назначения
которого вычисляется в рантайме (типично для применения кодирования по
таблице элементов). Статически это не выцепить без разбора либо низкого
банка как кода, либо диагностического обработчика записи кодирования.

### Что реально помогло бы (запрошено у владельца)

- **NETTODAT FSW/PSW с обеих приборок** — сырые байты блока кодирования.
- **SPDATEN для KOMBI** — описания FSW/PSW: имена параметров и их
  раскладка по байтам/битам.

Конкретный вопрос к этим данным: есть ли параметр кодирования,
занимающий **2 бита** и равный **2** (кандидат на `[0x09FB]` биты 6-7), и
параметр — **малый индекс 0..5** (кандидат на `0x0171`). Плюс проверить,
не относятся ли они к уже известным именам вида `GETRIEBE_ART` /
числа передач.

Важно: побайтово идентичные NETTODAT у обеих приборок означают, что эти
значения одинаковы в DKOML2 и HKOML2 — то есть они **не причина** различия
box/no-box. Но они остаются потенциальным рычагом, чтобы рамкой управлять.


## ★ Разбор NETTODAT + SPDATEN (2026-08-04)

### Прежний вывод «блоки кодирования побайтово идентичны» — ОПРОВЕРГНУТ

Владелец предоставил трассы и справедливо усомнился в чужой проверке.
Файлы: `high box.trc` = DKOML2 (чип 1051, плата `PL2-DKG E89`),
`high no box.TRC` = HKOML2 (чип 1121, плата `E9XHIGH`). Оба кластера
«high» — это уровень оснащения (расширенная против базовой low), а не
название прошивки; противоречия с прежними выводами нет.

**297 байт в каждом, различаются 31.** Идентичности нет.

### Байт 0 каждого блока — контрольная сумма (XOR)

Проверено: `byte0 == XOR(остальных байт)` в **15 блоках из 16**
(исключение — `003B0200`). Независимое подтверждение: в таблице имён
SPDATEN есть параметр `CSUM_ST_ANZEIGE_1` (0x0098) — «контрольная сумма
Steuerung_Anzeige_1».

Значит 9 из 31 различия — следствие, а не причина. **Реальных различий 22.**

### Имена блоков получены из KMBI_PL2.C09

Файл `SP-Daten 69.0/E89/daten/KMBI_PL2.C0[5-9]` — описание кодирования для
KOMBI семейства PL2. Блоки извлекаются по сигнатуре
`30 00 00 00 00 00 00 <длина> 00 <имя>\0`.

**Проверка отображения:** порядок и размеры блоков в файле точно совпали с
блоками в трассе для всех 11 присутствующих блоков (18, 64, 9, 2, 12, 19,
30, 6, 20, 32, 11 байт). Совпадение по двум независимым признакам.

| Адрес | Размер | Имя блока |
|---|---|---|
| `00300000` | 18 | Steuerung_Anzeige_1 |
| `00300100` | 64 | Check-Control |
| `00300200` | 9 | WEG |
| `00300300` | 2 | Ausstattung_1 |
| `00300400` | 12 | CHECKCONTROL_ALIVE |
| `00300500` | 19 | Tank_Prozess |
| `00300600` | 30 | Tank_Input |
| `00300700` | 6 | ACC |
| `00300800` | 20 | Aussentemperatur |
| `00300900` | 32 | CBS_01 |
| `00305000` | 11 | Ausstattung_PL2 |
| `00310600`, `003B0200`, `003C03/04/0F` | | нет в C09 (другой SG/индекс) |

### 22 реальных различия

| Блок | Байт | box | nobox | Оценка |
|---|---|---|---|---|
| **Steuerung_Anzeige_1** | **14** | **00** | **02** | **главный кандидат** |
| Check-Control | 61 | 7F | 7E | 1 бит |
| CHECKCONTROL_ALIVE | 1,3,4 | | | история/счётчики |
| ACC | 5 | F6 | FA | |
| Aussentemperatur | 18 | 36 | 18 | калибровка |
| CBS_01 | 3,16,23 | | | сервисные интервалы |
| **Ausstattung_PL2** | **5,9,10** | | | **кандидат (оснащение)** |
| `003B0200` | 0,2,5,7 | | | блок неизвестен |
| `003C0300` | 1,2,3 | | | блок неизвестен |
| `003C0400` | 2,3 | | | блок неизвестен |

Бóльшая часть различий — ожидаемая для двух подержанных приборок с разных
машин: пробег, сервисные счётчики, калибровки. Выделяются два блока:
**`Steuerung_Anzeige_1`** («управление отображением», байт 14 отличается
ровно одним битом: `00` у приборки с рамкой против `02` без) и
**`Ausstattung_PL2`** («оснащение PL2»).

### ❌ Чего сделать НЕ удалось

Побитовые имена параметров (`PARZUWEISUNG_FSW`) не извлечены. Формат BMW
DATEN до конца не разобран: попытка декодировать записи по сигнатуре
`30 00 00 00` дала явные ложные срабатывания (в каждой записи выпадало
`HEIMLEUCHTEN_NSW` — на деле это перечитывание заголовков блоков, а не
записей назначения параметров). Догадки в заметки не вносятся.

Таблица имён при этом разобрана успешно: `SWTFSW03.dat`, 8066 пар
KEYID→имя, правило — **KEYID это 2 байта LE непосредственно перед строкой
имени** (проверено: `A_MAX`=0x0C7C и `A_MIN`=0x0C7D идут подряд,
`A_MAX_DSC`=0x1138 / `A_MIN_DSC`=0x1139 тоже).

**Практичный обход:** у владельца на носителе есть `ncsdummy.zip` и ярлык
NCS Dummy — этот инструмент читает C0x/SWT штатно и покажет побитовые имена
без реверса формата. Это дешевле, чем дописывать парсер.

### Решающий эксперимент (обратимый)

На **своей** приборке DKOML2 изменить `Steuerung_Anzeige_1` байт 14 с `00`
на `02` (NCS Expert пересчитает XOR-контрольную сумму сам) и посмотреть,
исчезнет ли рамка.

Это согласуется с разбором прошивки: там найден путь «без рамки», гейтованный
конфигурационными значениями (`([0x09FB]>>6) != 2` И `DIR[0x71] < 4`), то
есть кодирование в принципе способно выключить рамку на DKOML2.

**Обратное — включить рамку на HKOML2 кодированием — по-прежнему не должно
работать**: у всех 9 вариантов HKOML2 отсутствует сама таблица атрибутов
`01 02 01 01`, то есть кода отрисовки рамки там нет. Если эксперимент
покажет обратное, неверен разбор прошивки, и это надо будет пересматривать.


## ★★ ЗАМКНУТО ЧЕРЕЗ SPDATEN: [0x09FB] бит 6-7 = GETRIEBE_ART (2026-08-04)

### Как удалось (после провала собственного реверса формата)

Формат BMW DATEN я реверсить не смог. Решил готовый парсер из
`/Users/densh/Work/Develop/BMW/BimmerDaten` (`daten_parser.py`). Ключ,
который я не нашёл сам: записи параметров помечены **`0x12 0x00` в позиции
+2**, группы — `0x06 0x00`, а `wortadr` это смещение байта в блоке.

Важно: реальный индекс кодирования приборки владельца — **C08**
(NCS Expert показывает `KMBI_PL2.C08 / A_PL2KMB.IPO / KOMB87.PRG`),
а не C09, который я разбирал сначала.

### Все 22 реальных различия названы — и НИ ОДНО не про передачу

| Блок | Байт | Параметр | box | nobox |
|---|---|---|---|---|
| Steuerung_Anzeige_1 | 14 | **DSC_VARIANTE** | wert_01 | 0x02 |
| Check-Control | 61 | KL_PREDRIVE_AUSWAHL_1 | wert_03 | wert_01 |
| CHECKCONTROL_ALIVE | 1,3,4 | ACC_ALIVE_ZAEHLER, ACC_ID_MONITOR, EPS_ALIVE_MONITOR, EPS_ID_MONITOR | | |
| ACC | 5 | TEMPOMAT_SETZ_ANZ_DAUER | wert_02 | 0x0A |
| Aussentemperatur | 18 | AUSSENTEMP_ANZ_FEHLER_1 | wert_03 | wert_01 |
| CBS_01 | 3,16,23 | CBS_GELB, CBS_STAT_11H, CBS_EINH_01H | | |
| Ausstattung_PL2 | 5 | LICHT_AUT_WERT_1/2/3 | aktiv | nicht_aktiv |
| Ausstattung_PL2 | 9 | DZM_UMRECHNUNG | wert_02 | wert_03 |
| Ausstattung_PL2 | 10 | FLA_VERBAUT | aktiv | nicht_aktiv |

DSC, круиз, датчик температуры, сервисные интервалы, автосвет, пересчёт
тахометра, ассистент дальнего света. **Ничего про индикатор передачи.**

### Все параметры про коробку — ИДЕНТИЧНЫ

| Параметр | Группа | Байт | Маска | box | nobox |
|---|---|---|---|---|---|
| SPORT_ANZEIGE | Steuerung_Anzeige_1 | 5 | 02 | 0x02 | 0x02 |
| MOTORSPORT | Ausstattung_1 | 1 | 08 | 0x08 | 0x08 |
| **GETRIEBE_ART** | **Ausstattung_1** | **1** | **C0** | **0x40** | **0x40** |
| SPA_IST_GANG_ENABLE | CHECKCONTROL_ALIVE | 8 | 20 | wert_01 | wert_01 |

Исходная посылка проекта («дело не в кодировании») **подтверждена** — но
теперь корректно, поимённо, а не через ошибочное «блоки побайтово идентичны».

### Главное: найдено, что такое [0x09FB] биты 6-7

`GETRIEBE_ART` имеет маску **`0xC0` — это биты 6-7**, а прошивка делает
`[0x09FB] >> 6` и сравнивает **с 2**. Значения параметра по SPDATEN:

| Значение | Смысл |
|---|---|
| 0 | handschalter (механика) |
| 1 | automatik |
| **2** | **ssg** (Sequentielles Schaltgetriebe) |

Проверка в геттере `0xFAFEB3` буквально означает **«тип коробки == ssg»**.
Обе приборки закодированы `automatik` (байт `0x4C`, биты 6-7 = 01 = 1),
поэтому код уходит на вторую ветку — проверку `DIR[0x71] < 4`.

Это **независимое подтверждение разбора прошивки из совершенно другого
источника**: двухбитное поле по битам 6-7, сравниваемое с 2, найдено сначала
в машинном коде, а затем — с тем же положением и той же семантикой — в
официальных описаниях кодирования BMW.

### ❌ Ранее предложенный эксперимент ОТМЕНЯЕТСЯ

Я предлагал поменять `Steuerung_Anzeige_1` байт 14 с `00` на `02`, считая его
кандидатом на управление рамкой. **Это была ошибка**: побитовый разбор
показал, что там `DSC_VARIANTE` — вариант DSC, к индикатору передачи
отношения не имеет. Эксперимент бесполезен, проводить не нужно.

### Итоговая, полностью замкнутая картина

```
Кодирование GETRIEBE_ART (Ausstattung_1 байт1 биты6-7) = automatik(1) у ОБЕИХ
   -> прошивка: ([0x09FB]>>6) != 2 (не ssg)
   -> проверяется DIR[0x71]; при 6-ступенчатой >= 4, значит НЕ возвращаем 0
   -> attr = таблица[индекс из CAN 0x1D2 байт1 биты0-1]
        DKOML2: таблица 01 02 01 01 существует  -> attr = 1 или 2 -> РАМКА
        HKOML2: таблицы нет вовсе (0 из 9)      -> кода рамки нет -> БЕЗ РАМКИ
```

Различие box/no-box определяется **исключительно вариантом прошивки**.
Кодирование его не задаёт и задать не может.


## Поиск писателя DIR[0x71] и 0x09FB (2026-08-04): частичный успех

### ✅ Найдена стартовая процедура и main()

`0xF9BC00-0xF9BC1F`:

```
F9BC0F: MOV A, 0x00 ; 6F 10   = MOV DTB, A    -> DTB = 0x00
F9BC13: MOV A, 0x01 ; 6F 14   = MOV DPR, A    -> DPR = 0x01
F9BC17: BBS IO[0xA1]:6, сам   ; ожидание аппаратного флага
F9BC1B: CALLP [0xFECFEB]      ; main()
F9BC1F: BRA сам               ; возврата быть не должно
```

**Поправка к прежнему утверждению:** я писал, что `MOV DPR,A` в коде
отсутствует. Это неверно — она есть по адресу `0xF9BC15`, просто чуть ниже
границы `0xF9C000`, которой я ограничивал поиск. Вывод `DIR[0x71] = 0x0171`
подтверждён, но теперь по прямому присваиванию, а не по значению сброса.

`main()` = `0xFECFEB`: инициализация портов (запись 0xED по таблице
указателей `0x9F68..0x9F7C`, настройка `IO[0xB0/B1/B6]`), затем единственный
вызов `0xFEC7CA`.

### ✅ RAM 0x09FB ИДЕНТИФИЦИРОВАН: это Ausstattung_1 байт 1

Доказано не поиском писателя, а **соответствием содержимого**. Разбор
`KMBI_PL2.C08` даёт раскладку байта 1 блока `Ausstattung_1`:

| Биты | Параметр | Как обращается прошивка |
|---|---|---|
| 0-1 | ACC_AUSSTATTUNG | — |
| 2 | KUEHL_MTL_AKTIV | — |
| **3** | **MOTORSPORT** | `BBS/BBC [0x09FB]:3` — около 30 мест |
| **4** | **SCHALT_PKT_BC** | `MOVB A,[0x09FB]:4` (0xFAD7F3, 0xFE9754) |
| **5** | **SCHALT_PKT_DAUERHAFT** | `MOVB A,[0x09FB]:5` (0xFAD7E6, 0xFE9761) |
| **6-7** | **GETRIEBE_ART** | `[0x09FB] >> 6`, сравнение с 2 |

**Каждая** битовая позиция, к которой обращается прошивка, соответствует
определённому параметру кодирования. Совпадение по 4 независимым позициям
исключает случайность. `RAM[0x09FB]` — копия `Ausstattung_1` байт 1.

Заодно проясняется, почему бит 3 гейтит десятки поведений: это MOTORSPORT
(M-пакет), логично влияющий на множество элементов отображения.

### ❌ Писатель НЕ найден; происхождение DIR[0x71] НЕ установлено

Что проверено безрезультатно:
1. Выровненных записей в `0x09FB` и `0x0171` нет **нигде** — ни addr16-форма,
   ни dir-форма, ни в верхнем банке, ни в низком.
2. Дерево вызовов от `main()` обрывается на 16 функциях: диспетчеризация идёт
   через косвенные вызовы (`CALL VCT4`, `CALL RWn` по таблицам указателей),
   которые обходчик не разрешает.
3. Блочные пересылки (`0x6E`): из 116 выровненных только 3 работают рядом с
   областью `0x09xx`, и все — в диагностическом слое (`0xFABExx-0xFAC0xx`),
   ни одна не пишет в `0x0171`.
4. Низкий банк как источник ненадёжен: разобранный по LINK-прологам, он даёт
   бессвязный код (`MOVW A, IO[0xF0]`, случайные `SUB`/`SWAP`). Единственная
   «запись» `0x001677: MOV DIR[0x71],0xC3` — почти наверняка данные,
   разобранные как код (значение 0xC3 вне диапазона 0..5). Согласуется с
   прежним выводом, что низкий банк — не код.
5. **`DIR[0x71]` не из кодирования**: в C08 нет ни одного параметра с
   диапазоном 0..5, похожего на индекс варианта или число передач.

**Вывод:** `DIR[0x71]` — вычисляемый в рантайме индекс варианта (индексирует
три таблицы по 6 указателей на функции, то есть выбор «стратегии»
отображения), а не значение кодирования. Откуда он берётся — открыто.

Наиболее вероятный механизм записи обоих значений: обобщённый цикл
применения кодирования, идущий по таблице дескрипторов и пишущий по
вычисляемому адресу. Чтобы его найти, нужно разрешать косвенные вызовы —
то есть строить полноценный граф вызовов с разбором таблиц указателей.


## Граф вызовов через таблицы указателей (2026-08-04): механизм найден, писатель — нет

Написан `tools/f2mc_icalls.py`: находит таблицы указателей по идиоме
`ADDL A,#база` -> `MOVL RLn,A` -> `MOVW A,@RLn` -> косвенный `CALL/JMP`,
разворачивает их и добавляет цели как точки входа.

**Результат разворота — отрицательный:** 18 таблиц, 35 новых точек входа,
но всего **+85 достижимых инструкций**. Косвенные вызовы оказались не тем
недостающим звеном.

### Дополнительно закрытые пробелы

- Область **`0xFF0000-0xFFC000`**, которую я раньше ни разу не сканировал
  (ограничивался `0xFF0000`): 258 функций, 6972 инструкции. Записей в
  `0x09FB`/`0x0171` там тоже нет.
- Итого по **всему образу** (178 298 проверенных адресов инструкций):
  прямых записей в эти два адреса нет ни в одной форме адресации.

### ✅ Найден настоящий механизм: движок на дескрипторах

Прошивка не пишет конфигурацию прямыми командами — она **табличная**:

```
FABF36: MOVW RW1, 0x09E4        ; RW1 = адрес переменной-указателя
FABF39: MOVL A, 0x00F8379A      ; 32-битный адрес дескриптора во flash
FABF3E: MOVL @DTB:RW1, A        ; RAM[0x09E4] = 0xF8379A
...
FABF4D: MOVL A, @DTB:RW1        ; загрузить указатель обратно
FABF4F: MOVL RL2, A
FABF51: MOV  A, @RL2+0x0A       ; поле дескриптора +0x0A, маска 0x0F
FABF62: MOVW A, @RL2+0x04       ; поле +0x04
FABF67: MOV  A, @A              ; косвенное разыменование
```

И найдены **таблицы адресов ОЗУ прямой страницы** по `0xF81D44` и
`0xF82596`: возрастающая последовательность
`0x016C, 0x016D, —, 0x016F, 0x0170, `**`0x0171`**`, 0x0172 ... 0x0178`.
То есть `0x0171` — запись в таблице «куда класть значение», а пишется он
обобщённым циклом по дескрипторам, а не именованной командой. Это
объясняет, почему ни один поиск по адресу-операнду ничего не давал.

### Поправка: низкий банк — не образ ОЗУ

`main()` делает `MOVW RW0,[0x9F68]` и пишет по полученному указателю. По
адресу `0x009F68` в образе лежит `FEFE` (заполнитель). Значит таблица
указателей заполняется в рантайме, а низкий банк `.0pa` — **ни код, ни
образ ОЗУ**, а заполнитель/служебная область. Ещё одно подтверждение, что
низкий банк разбирать как код бессмысленно.

### Что осталось открытым

Конкретный цикл, пишущий `0x0171` и `0x09FB`. Он внутри этого движка;
чтобы его дочитать, нужно разобрать формат дескриптора по `0xF8379A`
(поля +0x04 и +0x0A уже видны) и таблицы адресов по `0xF81D44`/`0xF82596`.

На выводы по рамке это не влияет: происхождение `0x09FB` уже доказано
независимо — по совпадению всех используемых битовых полей с параметрами
кодирования `Ausstattung_1` байт 1.


## ★ Формат дескриптора 0xF8379A разобран (2026-08-04)

Формат определён не гаданием по байтам, а **самим кодом** — функцией
`0xFABF32`, которая обходит таблицу:

```
ptr = 0xF8379A                     ; кладётся в RAM[0x09E4]
sum = 0x55 ; xor = 0x55
для i = 0..35:                     ; CMP A,0x24 -> 36 записей
    если (byte[ptr+0x0A] & 0x0F) == 1:
        для k = 1 .. word[ptr+0x02]-1:      ; k стартует с 1, не с 0!
            sum += byte[ word[ptr+0x04] + k ]
            xor ^= byte[ word[ptr+0x04] + k ]
    ptr += 12                       ; MOVN A,#12 ; ADDL A,ptr
```

Это **процедура проверки контрольных сумм блоков кодирования**. То, что `k`
начинается с 1, а не с 0, — прямое подтверждение найденного ранее: байт 0
каждого блока и есть контрольная сумма, поэтому в неё саму он не входит.

### Структура записи (12 байт, 36 штук с 0xF8379A)

| Смещение | Размер | Смысл |
|---|---|---|
| +0x00 | u16 | смещение (похоже на адрес в EEPROM) |
| +0x02 | u16 | **длина блока в байтах** |
| +0x04 | u16 | **адрес блока в ОЗУ** (банк DTB = 0) |
| +0x06 | u32 | источник: при `тип & 0x10 == 0` — указатель на значения по умолчанию во flash; при `!= 0` — указатель на код-обработчик |
| +0x0A | u8 | тип; младший полубитник == 1 → участвует в контрольной сумме |
| +0x0B | u8 | не выяснено |

### Карта «блок кодирования → адрес в ОЗУ»

Записи 1-9 совпали с блоками трассы **по порядку и по длине**:

| # | Длина | Адрес ОЗУ | Блок |
|---|---|---|---|
| 1 | 18 | `0x13AA` | Steuerung_Anzeige_1 |
| 2 | 64 | `0x464E` | Check-Control |
| 3 | 9 | `0x0ED1` | WEG |
| **4** | **2** | **`0x09FA`** | **Ausstattung_1** |
| 5 | 12 | `0x0C34` | CHECKCONTROL_ALIVE |
| 6 | 19 | `0x11D7` | Tank_Prozess |
| 7 | 30 | `0x121D` | Tank_Input |
| 8 | 6 | `0x0EB2` | ACC |
| 9 | 20 | `0x2A1B` | Aussentemperatur |
| 30 | 32 | `0x0439` | CBS_01 |
| 33 | 11 | `0x0A94` | Ausstattung_PL2 |

### ✅ Третье независимое подтверждение [0x09FB]

Запись 4: длина **2**, адрес ОЗУ **`0x09FA`**. Блок `Ausstattung_1` по
SPDATEN имеет размер ровно 2 байта, а `GETRIEBE_ART` лежит в его байте 1 →
**`0x09FA + 1 = 0x09FB`**.

Теперь происхождение подтверждено тремя независимыми способами:
1. совпадение всех используемых битовых полей с параметрами SPDATEN;
2. значение по умолчанию во flash (`0xF83955` = `00 08`: MOTORSPORT
   установлен, GETRIEBE_ART = 0 = handschalter — правдоподобная заводская
   заготовка);
3. явная запись в таблице дескрипторов.

### ✅ И третье подтверждение, что DIR[0x71] — НЕ кодирование

Ни один из 36 дескрипторов не покрывает адрес `0x0171`. Совпадает с тем,
что в `KMBI_PL2.C08` нет параметра с диапазоном 0..5, и с тем, что прямых
записей в него нет нигде в образе. `0x0171` — вычисляемая в рантайме
переменная выбора варианта отображения.

### Побочная ценность для цели с вольтметром/температурой ОЖ

Таблица даёт полную карту «кодирование → ОЗУ» для 36 областей. Это ровно
то, что понадобится, чтобы понять, куда прошивка кладёт значения и какие
области можно переиспользовать.

Замечание: `0xFABF32` — только проверка сумм. Процедура **применения**
кодирования (заливка из EEPROM в ОЗУ) использует ту же таблицу, но
находится в другом месте; её конкретный цикл всё ещё не найден.


## ★★ Процедура применения кодирования НАЙДЕНА (2026-08-04)

Найдена целиком подсистема кодирования, работающая по таблице дескрипторов
`0xF8379A`:

| Адрес | Роль |
|---|---|
| `0xFABDF1` | применить **все 36 блоков** — внешний цикл `i < 0x24` |
| **`0xFABE0C`** | **применить ОДИН блок: копирование в ОЗУ** |
| `0xFABE8E` | прочитать блок из EEPROM (поля `+0x00` смещение, `+0x02` длина, `+0x04` адрес ОЗУ) -> `CALLP [0xFBD1A4]` |
| `0xFABF00` | проверка: сверяет суммы с `[0x09F6]`/`[0x09F5]`, итог в `[0x09F8]` |
| `0xFABF32` | вычисление контрольных сумм по блокам |
| `0xFBD1A4` | нижний слой доступа к энергонезависимой памяти |

### 0xFABE0C — собственно применение

```
desc = 0xF8379A + индекс*12          ; FABE1F CALLP умножение, FABE23 + база
RAM[0x09E4] = desc                   ; FABE28
если (тип >> 4) == 1:                ; FABE2F ASRW A,#4
    src = CALLP [desc+0x06]          ; FABE43 — вызвать обработчик
иначе:
    src = указатель из desc+0x06     ; FABE4E — статические значения во flash
i = (тип & 0x0F) ? 1 : 0             ; FABE5D — пропуск байта контрольной суммы
пока i < word[desc+0x02]:            ; FABE83/88
    RAM[ word[desc+0x04] + i ] = src[i]   ; FABE6A..FABE7A
    i++
```

Ключевая команда записи — `FABE7A: MOV @RW4+0x00,A`, где `RW4` собран как
«адрес блока из дескриптора + i». Именно поэтому ни один поиск по
адресу-операнду ничего не находил: адрес назначения нигде не зашит в
команду.

### Замыкание на 0x09FB

Для блока `Ausstattung_1` (запись 4: длина 2, адрес ОЗУ `0x09FA`, тип 0x01):
- `тип & 0x0F` = 1, значит `i` стартует с **1** (байт 0 — контрольная сумма)
- цикл идёт пока `2 > i`, то есть выполняется **ровно одна итерация**
- записывается `RAM[0x09FA + 1]` = **`RAM[0x09FB]`**

Это тот самый байт с `GETRIEBE_ART` (биты 6-7) и `MOTORSPORT` (бит 3).
Цепочка от EEPROM до используемой прошивкой ячейки прослежена полностью.

### Значения по умолчанию во flash

Указатель `+0x06` у записи 4 = `0xF83955`, содержимое `00 08`. То есть
заводская заготовка: MOTORSPORT установлен, `GETRIEBE_ART` = 0
(handschalter). Реально закодировано `0x4C` = automatik + MOTORSPORT.

### Разделение по типу подтвердилось

- тип `0x01` (старший полубайт 0) -> `+0x06` указывает на **данные** во
  flash `0xF8xxxx` (значения по умолчанию);
- тип `0x11` (старший полубайт 1) -> `+0x06` указывает на **код**
  (`0xFAxxxx`/`0xFBxxxx`/`0xFCxxxx`, начинается с `CALLP`), который
  вычисляет содержимое. Логично для `CBS_01` и `CHECKCONTROL_ALIVE` —
  там счётчики, а не константы.

### Что это даёт для побочной цели проекта

Полная карта «кодирование -> ОЗУ» плюс найденная процедура заливки: видно,
какие области ОЗУ заняты кодированием, откуда берутся значения и где стоят
обработчики. Это база для понимания, куда можно вклиниться при добавлении
показаний напряжения и температуры ОЖ.


## ★ DIR[0x71] = счётчик состояния, а не конфигурация (2026-08-04)

Ответ найден: `0x0171` нигде не **присваивается** — он только
**инкрементируется и декрементируется**. Поэтому все поиски записи по
значению были обречены.

Код (`0xFC8A82`, достижим только через таблицы диспетчеризации, поэтому не
находился по прологам):

```
FC8A82: MOVW RW0, 0x0171          ; RW0 = адрес переменной
FC8A85: MOV  A, @DTB:RW0          ; RW2 = старое значение
FC8A88: если [0x2AB6] != 0 -> выход
FC8A8F: цикл:
          если [0x0171] >= цель -> FC8AAD
FC8A95:   idx = [0x0171]
FC8A9C:   ADDL A, 0xF840EE ; MOVW A,@RL2 ; CALL RW4   ; обработчик «шаг вверх»
FC8AA9:   INC @DTB:RW0                                 ; <<<< увеличить
          BRA FC8AC3
FC8AAD:   DEC @DTB:RW0                                 ; <<<< уменьшить
FC8AB6:   ADDL A, 0xF840E4 ; MOVW A,@RL2 ; CALL RW4   ; обработчик «шаг вниз»
FC8AC3: цель = CALL 0xFC882C
FC8AC7: если [0x0171] != цель -> цикл
FC8ACD: если [0x0171] != RW2:
FC8AD4:    MOV DIR[0x70], RW2      ; сохранить предыдущее состояние в 0x0170
```

**Это конечный автомат перехода состояний.** Переменная пошагово движется к
целевому значению (его даёт `0xFC882C`), и на каждом шаге вызывается
обработчик из таблицы: `0xF840EE` при увеличении, `0xF840E4` при
уменьшении. Соседний `DIR[0x70]` = предыдущее состояние.

Это объясняет всё разом:
- почему нет ни одной записи значения — только `INC`/`DEC`;
- почему индексируются таблицы ровно по 6 записей — 6 состояний, у каждого
  свои обработчики входа/выхода (найдено уже 7 таких таблиц:
  `0xF8406C`, `0xF84078`, `0xF84084`, `0xF840CC`, `0xF840D8`, `0xF840E4`,
  `0xF840EE`);
- почему его нет среди 36 дескрипторов кодирования — это рантайм-состояние.

### ⚠️ Поправка к прежней трактовке

Я предполагал, что `DIR[0x71]` «похоже на число передач» и что условие
`DIR[0x71] < 4` в геттере рамки связано с числом ступеней коробки.
**Это неверно.** Переменная — индекс текущего состояния/экрана приборки.
Условие в геттере означает «показывать рамку только начиная с состояния 4»,
то есть привязано к режиму отображения, а не к трансмиссии.

Совпадение с наблюдением владельца (6-ступенчатая коробка -> рамка есть)
сохраняется, но объясняется иначе: в рабочем режиме приборка находится в
состоянии >= 4, а не «потому что 6 передач >= 4».

### Что осталось невыясненным

Что именно возвращает `0xFC882C` как целевое состояние (он вызывает
`CALLP [0xFC8DDC]` и по умолчанию подставляет 6). Смысл шести состояний не
расшифрован — для этого надо разобрать обработчики из семи таблиц.


## ★ Обработчики семи таблиц разобраны: DIR[0x71] — уровень инициализации (2026-08-04)

### Структура оказалась матрицей переходов 10x6

Не семь отдельных таблиц, а регулярная сетка: базы идут с шагом `-0x10`
(`0xF8406C`, `0xF84078`, `0xF84084`, `0xF84090` ... `0xF840CC`), в каждой
6 записей. Записи ведут в ряд коротких заглушек в банке `0xFC`, ряды с
шагом `0x10`, внутри ряда смещения `+0, +1, +4, +7, +10, +13`:

```
FC894D: RET                      ; первая запись каждого ряда — пустой переход
FC894E: JMP 0xFC7E8A
FC8951: JMP 0xFC7E9F
FC8954: JMP 0xFC7FAA
FC8957: JMP 0xFC80B5
FC895A: JMP 0xFC81C0
FC895D: RET                      ; следующий ряд
...
```

Автомат `DIR[0x71]` использует две из них: **`0xF840E4` — шаг вниз**,
**`0xF840EE` — шаг вверх**.

| | Обработчики |
|---|---|
| вверх | `FC885B`, `FC887A`, `FC88D2`, `FC88D5`, `FC88D8` |
| вниз | `FC88DB`, `FC88F2`, `FC890B`, `FC890E`, `FC8911` |

### Симметрия обработчиков раскрывает смысл

```
вверх[0] FC885B:  MOVN A,#4 ; CALLP [0xFEC4AB]     ; ВКЛЮЧИТЬ периферию (маска 4)
вниз[0]  FC88DB:  MOVN A,#4 ; CALLP [0xFEC638]     ; ВЫКЛЮЧИТЬ периферию (маска 4)
```

`0xFEC638` — это функция, разобранная ещё в начале расследования: по битам
маски гасит периферийные регистры (`CLRB IO[0x2D]:4`, `IO[0x5E]:2`,
`IO[0x50]:3`, `IO[0x52]:3`, `MOVW IO[0x7E],0` ...). Значит `0xFEC4AB` —
её парная, включающая ту же периферию.

Остальные обработчики того же характера: `вниз[4]` заканчивается
`CLRB IO[0xA0]:4` (сброс аппаратного выхода), `вверх[1]` последовательно
инициализирует подсистемы с таймингами `0x14`, `0x07`, `0x0A` в
`[0x25E6]`/`[0x25E4]` и вызовами `CALLP [0xFECD8D]` с номерами 5, 6, ...

**Вывод: `DIR[0x71]` — уровень включения/инициализации приборки (0..5).**
Движение вверх поэтапно включает подсистемы, вниз — поэтапно выключает.
`DIR[0x70]` хранит предыдущий уровень.

### Что это значит для рамки

Условие в геттере `DIR[0x71] < 4 -> вернуть 0` означает:
**не рисовать рамку, пока приборка не поднялась до уровня инициализации 4.**
Это защита от отрисовки на непрогретой/недоинициализированной панели, а не
что-либо связанное с трансмиссией.

### Поправка к раннему выводу

В разделе про 62 уникальные функции я разобрал `0xFEC638` и записал, что
это «процедура отключения периферии, к дисплею отношения не имеет».
**Отношение имеет**: это шаг выключения того самого секвенсора питания
дисплея, который гейтит отрисовку рамки. Тогда связь не была видна, потому
что функция достижима только через матрицу переходов.


## ★ Что делает каждый уровень DIR[0x71] (2026-08-04)

Обработчик берётся по **текущему** состоянию: `вверх[i]` выполняется при
переходе `i -> i+1`, `вниз[i]` — при переходе `i+1 -> i` (значение
декрементируется до чтения индекса).

| Переход | Обработчик | Что делает |
|---|---|---|
| **0 -> 1** | `FC885B` | обнуляет `DIR[0x78/79/7A]`, `CALL 0xFC7571`, **включает периферию** `CALLP [0xFEC4AB]` с маской 4 |
| **1 -> 2** | `FC887A` | тайминги `[0x25E6]`/`[0x25E4]` = 0x14, 0x07, 0x0A; последовательность `CALLP [0xFECD8D]` с номерами 5, 6 — поэтапный подъём подсистем с проверками |
| **2 -> 3** | `FC77F2` | самый крупный шаг: 131 инструкция, работа с `IO[0x31]`, вызовы ~8 модулей |
| **3 -> 4** | `FC7964` | 63 инструкции; **единственный, кто трогает модуль индикатора передачи** (`0xFAFDC6`) |
| **4 -> 5** | `FC7A4E` | **`RET` — не делает ничего** |
| 1 -> 0 | `FC88DB` | **выключает периферию** `CALLP [0xFEC638]` с маской 4 (парная к 0xFEC4AB) |
| 2 -> 1 | `FC7AD6` | 75 инструкций; трогает модуль индикатора (`0xFAFDC4`) |
| 3 -> 2 | `FC7BD2` | 92 инструкции, `IO[0x31]` |
| 4 -> 3 | `FC7CD9` | 45 инструкций |
| 5 -> 4 | `FC8911` | `CLRB IO[0xA0]:4` (сам `0xFC7D8B` = `RET`) |

### Почему рамка требует уровень >= 4

`0xFAFDC6` — сброс модуля индикатора передачи, вызываемый **только** на
переходе 3 -> 4:

```
FAFDC6: A = [0x09FB] >> 6         ; GETRIEBE_ART
FAFDCF: BZ -> выход               ; если == ssg (2), ничего не делать
FAFDD1: MOV  [0x0D04], 0x20       ; символ = пробел
FAFDD6: MOV  [0x0D05], 0x20       ; символ = пробел
FAFDDB: MOVW [0x0CF6], 0          ; СБРОС АТРИБУТА РАМКИ
FAFDEA: MOV  [0x0CFC], 0
FAFDEE: RETP
```

То есть модуль индикатора приводится в исходное состояние именно на входе
в уровень 4. Ниже уровня 4 он не инициализирован, поэтому геттер и
возвращает 0 — рисовать нечего. Условие `DIR[0x71] < 4` в геттере и этот
сброс — две стороны одного и того же: **индикатор передачи живёт начиная
с уровня 4**.

Отдельно любопытно: сброс **пропускается при `GETRIEBE_ART == ssg`**. Та же
проверка «тип коробки == секвентальная», что и в геттере рамки: у ssg
модуль ведёт себя иначе и не гасится в пробелы.

### Уровень 5 практически пуст

`вверх[4]` = `RET`. Ничего не включается. Только на обратном пути
(`вниз[4]`) сбрасывается `IO[0xA0]:4`. Похоже, 5 — это «рабочий» уровень,
отличающийся от 4 одним аппаратным сигналом.

### Оговорка

Уровни 2 -> 3 и 3 -> 4 вызывают по 8+ модулей каждый; я охарактеризовал их
структурно (объём, задействованная периферия, наличие вызова модуля
индикатора), но не именовал все подсистемы поимённо — для этого нужно
разбирать каждый вызываемый модуль отдельно. На вопрос про рамку это уже
не влияет.


## ★ Модули переходов 2->3 и 3->4 (2026-08-04)

### Архитектура: у каждого модуля своя точка входа на каждый уровень

Переход 2->3 вызывает **38** функций, переход 3->4 — **28**. Их адреса идут
парами: `0xFC9129`/`0xFC9135`, `0xFCA1CE`/`0xFCA1FC`, `0xFD2ED6`/`0xFD2F6F`
и так далее. **19 модулей спарено** (близкие адреса = один модуль),
19 встречаются только в 2->3, 9 только в 3->4.

То есть приборка построена как набор подсистем, у каждой из которых
**отдельная точка входа под каждый уровень инициализации**, а автомат
`DIR[0x71]` на каждом шаге обходит их все.

### Спаренные модули (вход для уровня 3 / для уровня 4)

| Уровень 3 | Уровень 4 | Инстр. | Характерные адреса | Что это |
|---|---|---|---|---|
| `F9CEC9` | `F9CEC3` | 4/1 | `0x2A2A` | **Наружная температура** (внутри блока Aussentemperatur `0x2A1B..0x2A2E`) |
| `FCEDC0` | `FCEE3C` | 30/6 | `0x0ED2`, `0x0ED4` | **Пробег/путь (WEG)** (внутри блока `0x0ED1..0x0ED9`) |
| `FB6DAA` | `FB6DE7` | 34/**151** | `0x09FB`, `0x2632` | **Группа индикатора**: читает GETRIEBE_ART и флаг обновления `0x2632`, тот же, что в распаковщике `0x1D2` |
| `FD2ED6` | `FD2F6F` | 27/13 | `0x13A5..0x13A8` | рядом с блоком Steuerung_Anzeige_1 (`0x13AA`) |
| `FC55B8` | `FC55BB` | 25/11 | `0x1060`, `0x117E` | не опознан |
| `FCA875` | `FCA89F` | 9/9 | `0x126C`, `0x2FD1` | не опознан |
| `FDAB41` | `FDAB71` | 5/17 | `0x15E6`, `0x2AE8` | не опознан |
| `FD5CD/D2` | `F9D5E0/695` | | `0x032B..0x033A` | прямая страница, не опознан |
| `FA00A6` | `FA0095` | 14/3 | `0x036A`, `0x037F` | не опознан |
| `FAB644` | `FAB666` | 8/7 | `0x09BA`, `0x262C` | не опознан |
| `FC8DA3` | `FC8DA3` | 27/27 | `0x1172`, `0x25FA` | общий для обоих уровней |
| остальные | | | | без характерных признаков |

### Модули только в 2->3

Самые содержательные:
- `FC7686` (108 инстр.) — **управление отображением**: блок
  `Steuerung_Anzeige_1` + `IO[0x32]`
- `FC7571` (99 инстр.) — блок `Ausstattung_1` + `IO[0x31]`
- `FEC638` (196 инстр.) — **гашение периферии** (`IO[0x29]`, `0x2D`, `0x30`,
  `0x35`, `0x50`)

### Модули только в 3->4 — здесь ключ к рамке

- **`FAFDC6`** — сброс модуля индикатора передачи (символы в пробелы,
  атрибут рамки `[0x0CF6]` в ноль). **Вызывается только на этом переходе**
  — вот почему рамка требует уровня >= 4.
- `FB6DE7` — 151 инструкция, самый крупный модуль перехода, работает с
  `0x09FB` (GETRIEBE_ART)
- `FC8D9F` — `CLRB IO[0xA8]:2`

### Оговорка о границах разбора

Уверенно опознаны по карте ОЗУ из дескрипторов кодирования только те модули,
что обращаются **внутрь** известных блоков: наружная температура, пробег,
группа индикатора, управление отображением. Остальные работают со своими
рабочими переменными, часто расположенными рядом с блоком, но вне его, —
по одним адресам их назвать нельзя. Для них в таблице приведены точки входа
и характерные адреса, чтобы можно было продолжить позже.


## ★ Модуль FB6DE7 разобран (2026-08-04)

Самый крупный модуль перехода 3->4 (151 инструкция). Оказался
**инициализатором состояния элементов отображения уровня 4**.

### Часть 1: очистка таблицы состояний

17 повторяющихся вызовов `CALLP [0xFCF61B]` с аргументами (адрес, 0, 3).
Сам `0xFCF61B` проверен — внутри `FILSI`, то есть это **заполнение памяти**
(memset). Очищаются 17 областей по 3 байта:

```
0BC0 0BC3 0BC6 0BC9 0BCC 0BCF | 0BD8 | 0BDE | 0BE7 | 0BED 0BF0 0BF3 |
0BF9 0BFC 0BFF 0C02 | 0C08
```

Шаг в основном 3 байта, но местами 6 и 9 — часть записей пропускается, то
есть таблица разрежённая: обнуляются не все элементы, а выборочно.

### Часть 2: включение двух элементов с проверкой типа коробки

```
FB6ED5: A = [0x09FB] >> 6      ; GETRIEBE_ART
FB6EDE: BZ -> пропустить       ; если == ssg, блок ниже НЕ выполняется
FB6EE0: SETB [0x0BB8]:6        ; включить элемент A
FB6EE4: CLRB [0x0BB8]:4        ; сбросить его признак «завершён»
FB6EE8: MOV  [0x0BA8], 0       ; обнулить счётчик A
FB6EEC: SETB [0x0BB8]:7        ; включить элемент B — ВСЕГДА
FB6EF0: CLRB [0x0BB8]:5
FB6EF4: MOV  [0x0BA9], 0       ; обнулить счётчик B
```

### Что это за элементы: одноразовые таймеры

Потребитель — `0xFB6F38`:

```
если не «завершён» и включён:
    [0x0BA8] += 1 ; если > 0x20 (32)  -> пометить завершённым, выключить
    [0x0BA9] += 1 ; если > 0x3C (60)  -> пометить завершённым, выключить
```

То есть `[0x0BB8]` — битовая маска: биты 6/7 «элемент активен», биты 4/5
«отработал». `[0x0BA8]`/`[0x0BA9]` — счётчики с порогами **32** и **60**
тиков. Оба самовыключаются по достижении порога — классические таймауты
показа.

### Зеркальная точка для ssg

По `0xFB6D4D` стоит та же проверка, но **с обратным условием**:

```
FB6D4D: A = [0x09FB] >> 6
FB6D56: BNZ -> пропустить      ; если != ssg, НЕ выполнять
FB6D58: SETB [0x0BB8]:6 ; CLRB [0x0BB8]:4 ; MOV [0x0BA8],0
```

То есть таймер A запускается **в обоих случаях, но из разных мест**: при
обычной коробке — на переходе в уровень 4, при ssg — из другой точки.
Таймер B (60 тиков) стартует всегда на уровне 4.

Это уже **третье** место в прошивке, где отдельно выделяется
`GETRIEBE_ART == ssg` (первые два: геттер атрибута рамки `0xFAFEB3` и
сброс модуля индикатора `0xFAFDC6`).

### Оговорка

Назначение самих таймаутов (что именно показывается 32 и 60 тиков) не
установлено — для этого надо проследить, кто читает признаки «завершён»
(биты 4/5 маски `0x0BB8`). Структура при этом ясна полностью.


## ★ Читатели битов 4/5 маски 0x0BB8 (2026-08-04)

Всего обращений к `0x0BB8` — 19. Установка/сброс внутри уже разобранных
`0xFB6DE7` и `0xFB6F38`; **внешних читателя два**.

### Бит 4 (таймер A, 32 тика) -> ТОЛЬКО для ssg

`0xFB7986`, и решающее — условия перед ним:

```
FB7970: A = [0x09FB] >> 6      ; GETRIEBE_ART
FB7979: BZ  -> продолжить      ; ТОЛЬКО если == ssg (2)
FB797B: JMP -> выход           ; иначе блок пропускается целиком
FB797E: BBS [0x0C31]:0 -> продолжить
FB7986: BBS [0x0BB8]:4 -> продолжить    ; только если таймер A отработал
FB798E: ... собственно работа
```

То есть таймер A (32 тика) — это **задержка перед включением ветки
отображения, специфичной для секвентальной коробки**. Обычные коробки сюда
не заходят вообще.

Это **четвёртое** место, где прошивка отдельно выделяет
`GETRIEBE_ART == ssg`. Полный список:
1. геттер атрибута рамки `0xFAFEB3`;
2. сброс модуля индикатора `0xFAFDC6`;
3. запуск таймера A в `0xFB6DE7` / зеркальная точка `0xFB6D4D`;
4. эта ветка `0xFB7970`.

### Бит 5 (таймер B, 60 тиков) -> показ элемента 0x1E

`0xFB7642`:

```
FB763B: A = [0x410E] & 0x0C ; BZ -> пропустить   ; байт CAN-буфера
FB7642: BBC [0x0BB8]:5      -> пропустить        ; таймер B не отработал
FB7647: BBC [0x0C39]:4      -> пропустить
FB764C: PUSHW 0x20 ; PUSHW 1 ; PUSHW 0x1E
FB7654: CALL 0xFB65C7                            ; показать элемент 0x1E
```

`0xFB65C7` — функция показа элемента по идентификатору (рядом, на
`0xFB7630`, тот же вызов с идентификатором `0x1F`). `0x410E` лежит в
области приёмных буферов CAN (напомню, `0x1D2` разбирается из `0x4140`).

Смысл: элемент `0x1E` разрешается показывать только после того, как с
момента выхода на уровень 4 прошло 60 тиков, и при этом пришло
подтверждение по шине и установлен флаг `[0x0C39]:4`. Классическая
защита от показа на непрогретой системе.

### Итог по таймерам

| Таймер | Порог | Что гейтит |
|---|---|---|
| A (`0x0BA8`, бит 4) | 32 тика | ветка отображения **только для ssg** |
| B (`0x0BA9`, бит 5) | 60 тиков | показ элемента `0x1E` (плюс условия по CAN и флагу) |


## ★ 0xFB65C7 — показ элемента по номеру (2026-08-04)

### Сигнатура и логика

`show_element(id, flag, cond)` — три слова через стек, последний `PUSHW`
перед `CALL` это первый аргумент (номер элемента).

```
FB65CB: id = @RW3+0x04
FB65CF: если id == 8 -> выход
FB65D6: MOVN A,#3 ; MULUW A,RW1        ; id * 3
FB65DA: MOVEA RW4, @RW0+0x0BBA         ; &таблица[id]   <<< база 0x0BBA, шаг 3
FB65DE: MOV A, @RW4+0x02               ; поле +2 записи
FB65E1: извлечь бит 4; если != 1 -> выход      ; элемент не зарегистрирован
FB65F0: cond = @RW3+0x08
FB65F3: ADDW A, 0x2888 ; MOV A,@A ; & 1        ; бит из таблицы 0x2888
FB65FC: если 0 -> выход                         ; условие не выполнено
FB660B: особые случаи для id 5, 0x16, 0x20
...     CALL 0xFB628B
```

**Таблица элементов: `0x0BBA`, по 3 байта на элемент, индекс — номер.**
Сходится с модулем `0xFB6DE7`: он чистил `0x0BC0`, `0x0BC3`, `0x0BC6`... а
`0x0BBA + 3*2 = 0x0BC0`, то есть обнулял элементы с номерами 2, 3, 4 и далее.
Бит 4 байта `+0x02` записи = «элемент зарегистрирован», без него показ не
происходит.

Второй фильтр — **битовая таблица условий по `0x2888`**, индексируемая
третьим аргументом.

### Каталог вызовов

| Вызов | Элемент | Флаг | cond | Условие показа |
|---|---|---|---|---|
| `FB7654` | `0x1E` (30) | 1 | `0x20` | `BBC [0x0C39]:4` + таймер B |
| `FB76A9` | `0x0D` (13) | 0 | `0x1D` | `BBC [0x0C31]:4` |
| `FB76C0` | `0x19` (25) | 1 | `0x3B` | `BBC [0x0C39]:1` |
| `FB76D7` | `0x0A` (10) | 0 | `0x27` | — |
| `FB76E8` | `0x18` (24) | 1 | `0x0F` | `BBS [0x0BE6]:2` |
| `FB76F9` | `0x08` (8) | 0 | `0x2E` | `BBC [0x0C31]:4` |
| `FB771D` | `0x15` (21) | 1 | `0x11` | `BBC [0x13AF]:5` |
| `FB7734` | `0x17` (23) | 1 | `0x10` | `BBC [0x13AF]:5` |
| `FB774B` | `0x12` (18) | 1 | `0x13` | `BBS [0x0BE6]:2` |
| `FB7762` | `0x1A` (26) | 1 | `0x15` | `BBS [0x0BE6]:2` |
| `FB7774` | `0x23` (35) | 1 | `0x19` | `BBC [0x0C3C]:0` |

Номера элементов, реально используемые: `0x08, 0x0A, 0x0D, 0x12, 0x15,
0x17, 0x18, 0x19, 0x1A, 0x1E, 0x23`. Пересекаются со списком очищаемых в
`0xFB6DE7` (10, 18, 21, 23, 24, 26) — одна и та же таблица.

### ⚠️ Поправка к моей формулировке

Я написал «элементы 0x1E/0x1F/0x20». **Это было неточно**: `0x1E` —
действительно номер элемента, а `0x20` в том же вызове — третий аргумент
(индекс условия), а не элемент. `0x1F` — номер элемента в вызове по
`0xFB7633`, который не попал в мой набор достижимых адресов.

### Чего НЕ установлено

Что каждый номер отображает визуально. Для этого нужно разбирать `0xFB628B`
и то, как формируется содержимое элемента. Механизм при этом ясен целиком.

### Ценность для побочной цели проекта

Это и есть искомый механизм «показать произвольный элемент по номеру»:
реестр элементов `0x0BBA` (3 байта на элемент, бит 4 поля +2 = включён),
таблица условий `0x2888`, единая точка входа `0xFB65C7(id, flag, cond)`.
Именно сюда имеет смысл смотреть при попытке вывести напряжение бортсети и
температуру ОЖ в штатный слот.


## ★ Как формируется содержимое элемента: очередь сообщений (2026-08-04)

### 0xFB628B — диспетчер содержимого

391 инструкция, вызывает **35** функций-отрисовщиков из семейства
`0xFAE924 ... 0xFAF2D8` (тот же модуль, где живёт индикатор передачи).
Большая цепочка проверок по номеру элемента и флагам состояния
(`[0x0BB1]`, `[0x0C78]`, `[0x0C79]`, `[0x410E]`), каждая ветка вызывает
свой отрисовщик.

### 0xFAF5A5 — упаковка дескриптора

Принимает 4 аргумента и **пакует их в битовые поля** структуры на стеке:

```
FAF5A9: если arg1 == 0 -> выход
FAF5AD: local[-5] = (local[-5] & 0xCF) | 0x10
FAF5CF: local[-5] = (local[-5] & 0xF0) | (arg2 & 0x0F)
FAF5DF: local[-4] = (local[-4] & 0xFC) | (arg3 & 0x03)
FAF5EF: arg4 << 14 ...
        -> CALLP [0xF9EDEE]
```

То есть `0xFAF5A5(content_id, style4, mode2, flag)` собирает компактный
дескриптор и отдаёт его дальше.

### 0xF9EDEE — постановка в кольцевой буфер

```
F9EDF2: AND CCR,0xBF          ; критическая секция
F9EDF4: RW0 = [0x06CF]        ; голова
F9EDF8: RW1 = голова + 1
F9EDFB: RW4 = 0x2A (42)       ; размер кольца
F9EE02: DIVW A,RW1            ; (голова+1) mod 42
F9EE04: A = [0x06D0]          ; хвост
F9EE09: BZ -> выход           ; кольцо заполнено — сообщение теряется
F9EE19: [0x06CF] = новая голова
F9EE1C: OR CCR,0x40           ; конец критической секции
F9EE1E: голова << 3           ; смещение записи = индекс * 8
```

**Кольцевой буфер на 42 записи по 8 байт**, голова `0x06CF`, хвост `0x06D0`.
Потребитель — около `0xF9EAB0` (читает и продвигает хвост), сброс очереди —
`0xF9EEE0`/`0xF9EEE3` (обнуляет оба индекса).

### Полная цепочка формирования содержимого

```
show_element(id, flag, cond)                     0xFB65C7
  реестр 0x0BBA[id], бит 4 поля +2 = зарегистрирован
  таблица условий 0x2888[cond], бит 0
    -> диспетчер                                 0xFB628B
       -> один из ~35 отрисовщиков               0xFAE9xx..0xFAF2xx
          -> упаковка дескриптора                0xFAF5A5(id, style, mode, flag)
             -> постановка в очередь             0xF9EDEE
                кольцо 42 x 8 байт, голова 0x06CF / хвост 0x06D0
                   -> потребитель ~0xF9EAB0 -> собственно вывод
```

### Ценность для побочной цели

Архитектура оказалась **очередью сообщений**, а не прямой записью в
видеопамять. Это принципиально: чтобы вывести своё значение, не нужно
трогать растр — достаточно поставить дескриптор в кольцо. Точки входа:
`0xFAF5A5` (упаковка) и `0xF9EDEE` (постановка). Ограничение — кольцо
на 42 записи, при переполнении сообщение молча теряется.

### Чего НЕ установлено

Смысл конкретных `content_id` (например `0xCF` из вызова по `0xFB62D0`) и
формат 8-байтовой записи очереди. Для этого надо разбирать потребителя
около `0xF9EAB0`.


## ★ Формат 8-байтовой записи очереди и потребитель (2026-08-04)

### Кольцевой буфер

| Что | Адрес |
|---|---|
| база буфера | **`0x057C`** (`ADDW A, 0x057C` в `0xF9EE22`) |
| размер | 42 записи x 8 байт = 336 байт (`0x057C..0x06CB`) |
| голова (производитель) | `0x06CF` |
| хвост (потребитель) | `0x06D0` |

Производитель копирует запись целиком: `RW0=8 ; MOVSI` из структуры,
собранной вызывающим. То есть **формат записи = структура, которую строит
`0xFAF5A5`**.

### Формат записи (8 байт)

| Смещение | Размер | Содержимое |
|---|---|---|
| +0 | 2 | **`content_id`** (16 бит, arg1) |
| +2 | 1 | 0 |
| +3 | 1 | биты 7-6 = arg4, биты 5-4 = `01`, биты 3-0 = arg2 (стиль) |
| +4 | 1 | биты 1-0 = arg3 (режим) |
| +5..+7 | 3 | 0 |

Как собирается байт +3 (`0xFAF5A5`):
```
FAF5AD: (x & 0xCF) | 0x10          ; биты 5-4 := 01
FAF5CF: (x & 0xF0) | (arg2 & 0x0F) ; биты 3-0 := arg2
FAF5EF: arg4 << 14, SWAP, ZEXT     ; (arg4 & 3) << 6
FAF5FC: (x & 0x3F) | ...           ; биты 7-6 := arg4
```

Байт +4: `FAF5DF: (x & 0xFC) | (arg3 & 0x03)`.
Байты +2, +5..+7 обнуляются (`FAF5B8`, `FAF5C1`).

### Потребитель

Читает запись по указателю `RW1` и раздаёт в отрисовщики:

```
F9EA9D: MOVW A, @DTB:RW1       ; +0 = content_id
F9EA95: MOV  A, @RW1+0x04 ; &3 ; +4 = режим (2 бита)
F9EAA0: CALLP [0xFD7530]       ; отрисовщик, вариант 1
   или
F9EAAB: CALLP [0xFD75B0]       ; отрисовщик, вариант 2
F9EAB0: [0x06D0] = ([0x06D0]+1) mod 42   ; продвинуть хвост
```

Конечные отрисовщики — **`0xFD7530`** и **`0xFD75B0`**.

### Итог: полный путь от «показать элемент» до пикселей

```
show_element(id, flag, cond)               0xFB65C7
  реестр 0x0BBA[id] (бит 4 поля +2), условия 0x2888[cond]
    -> диспетчер                           0xFB628B  (35 отрисовщиков)
       -> упаковка дескриптора             0xFAF5A5(content_id, style, mode, flag)
          -> постановка в кольцо           0xF9EDEE
             буфер 0x057C, 42 x 8 байт, голова 0x06CF / хвост 0x06D0
                -> потребитель             ~0xF9EAB0
                   -> отрисовщики          0xFD7530 / 0xFD75B0
```

### Чего НЕ установлено

Смысл конкретных значений `content_id` (что именно рисует, например, `0xCF`)
и как отрисовщики `0xFD7530`/`0xFD75B0` превращают его в изображение —
это следующий уровень, отдельная работа.


## Изучены 11 статей drive2.ru "Кодирование со смыслом" (2026-08-04)

Последовательная серия (части 1-11) про кодирование BMW E60/E63/E89.
Большая часть — общая теория (структура FA/VO, идентификаторы, SSD-файлы
для виртуальной симуляции), напрямую про KOMBI E90/E9x или рамку почти
ничего. Но три части дают конкретные, применимые к проекту техники.

### Часть 6 (l/9267919) — ПРЯМОЙ ПРЕЦЕДЕНТ для побочной цели проекта

Автор перепрошивает **индикатор расхода топлива (KVA) под температуру
масла** правкой NETTODAT — то есть ровно тот приём, который нужен для
вольтметра и температуры ОЖ.

- Блок по адресу `0x3105`, 18 (0x18) байт: байт 0 — контрольная сумма,
  байт 1 — начальное положение стрелки, байт 2 — коэффициент торможения,
  байты 3-12 — пять 16-битных точек диапазона входа, байты 13-22 — точки
  управления шаговым мотором, байт 23 — конфигурационные биты.
- **Бит 0 байта 23 — переключатель функции стрелки**: `0` = экономайзер
  (расход), `1` = температура масла. Смена байта `0x6E` → `0x6F`
  переключает назначение стрелки целиком.
- Точки диапазона в little-endian, с offset: `76 00 94 00 A8 00 BC 00 DA 00`
  → 118/148/168/188/218, минус смещение 48 → 70-170°C.
- Инструмент: Tool32 + `codierdaten_lesen` + `KOMB60.PRG` (E60/E63; у нас
  для E89 — `KOMB87.PRG`, тот же класс инструментов).

**Вывод: у BMW есть штатный механизм «одна и та же стрелка/индикатор,
разное физическое значение», управляемый одним конфигурационным битом.**
Прямая аналогия для проекта: не обязательно City рисовать новый элемент —
можно поискать, нет ли уже готового переключателя назначения у одной из
существующих стрелок/цифровых полей.

### Часть 7 (l/9423788) — карта блоков адресного семейства 0x31xx

```
0x3100  спидометр
0x3101  слайдер круиз-контроля
0x3102  указатель топлива
0x3103  тахометр
0x3105  KVA / температура масла (см. часть 6)
```

**Совпадает с семейством адресов в наших собственных трассах** —
`00300000`, `00300100` и т.д. в блоке `Steuerung_Anzeige_1`/`Check-Control`
это другой SGBD (KOMBI PL2, не KOMB60), но общий принцип адресации
«стрелка/элемент = блок по фиксированному смещению» подтверждён на другом
семействе кластеров.

### Часть 11 (l/487094372416880761) — КЛЮЧЕВАЯ ТЕХНИКА: раскрытие скрытых параметров

Автор находит **недокументированный, но реально используемый байт**
(`00380017h`, значение `9Dh`) в разделе, помеченном как `UNBELEGT`
(«не занято»), и **добавляет для него собственное имя параметра**
(`AC_EC_SPANNUNG`) в словари FSW/PSW плюс запись в `.Cxx`-индекс — после
чего NCS Expert начинает показывать и позволяет менять его как обычный
параметр кодирования.

Критерий отличия «действительно неиспользуемое» от «скрытое, но реальное»:
**«действительно неиспользуемые участки как правило содержат значения
типа FFh»**. Ненулевой/неFF байт в области `UNBELEGT` — кандидат на
скрытый параметр.

**Прямая применимость к проекту:**
1. Наше найденное недокументированное поле — `0x1D2` байт 1 биты 0-1
   (читают только приборки DKG) — можно **формально зарегистрировать**
   этой же техникой: дать имя в SWTFSW/SWTPSW и добавить запись в
   `KMBI_PL2.C08`, после чего оно станет видимым и редактируемым в
   NCS Expert как обычный параметр, а не только как байт в NETTODAT.
2. Тот же приём годится для поиска **других** скрытых параметров в блоках
   KOMBI PL2 — искать в областях `UNBELEGT`/зарезервированных байты,
   отличные от `FF`, по той же эвристике.
3. Подтверждает независимо формат `PARZUWEISUNG_FSW`
   (`BLOCKNR×100h + WORTADR`, `MASKE`), который мы уже вывели ранее через
   BimmerDaten — совпадение двух независимых источников.

### Прочие части (1-5, 8-10) — общая теория, напрямую не применимо

Части 1-3: структура FA/VO, идентификаторы, редактирование NETTODAT
вручную (общие принципы, уже применённые в проекте).
Часть 4: правка кодирования KOMBI E60 напрямую через Tool32 (адрес
`00310100h`) в обход стандартных ограничений NCS — тот же класс приёма,
что мы использовали для чтения `KMBI_PL2`, но для E60/E63, не для нашего
E89-семейства.
Часть 5: автоматизация контрольных сумм при кодировании через NETTODAT —
полезно знать при практической правке (не нужно вручную считать XOR).
Часть 8-10: SSD-файлы для симуляции без машины, идентификаторы
кодировочных индексов (CI), структура SWT-словарей — фоновая теория,
подтверждает уже сделанный разбор, но нового практического пути не даёт.

### Итог

Самое ценное — часть 6 (прецедент переключения назначения стрелки) и
часть 11 (техника раскрытия/регистрации скрытых параметров). Обе прямо
применимы к следующему шагу проекта: искать в области `KMBI_PL2`
недокументированные ненулевые байты как кандидатов на скрытые параметры
(в том числе, возможно, уже существующий переключатель «показывать
напряжение бортсети» или «температуру ОЖ» на одном из цифровых полей,
а не только на стрелках).


## Поиск не-FF байт в непокрытых областях KMBI_PL2.C08 (2026-08-04)

Прямой список записей `UNBELEGT1`/`UNBELEGT2` в бинарнике не найден — эти
имена встречаются один раз, как часть общего шаблона-схемы формата `.Cxx`
(вместе с `CODIERDATENBLOCK`, `KENNUNG_K` и т.д.), присутствующего в каждом
индексе KOMBI PL2, а не как список реально зарезервированных адресов для
конкретно этого. Реальных записей такого типа для нашего индекса нет.

Пошёл практическим путём той же сути: нашёл байты блоков трассы, **не
покрытые ни одним именованным параметром** из `KMBI_PL2.C08` (329
параметров всего), и проверил их на не-`FF`. 76 позиций из 297 байт
оказались непокрытыми и ненулевыми/не-FF. **Большинство — не скрытые
параметры**, и это важно не перепутать:

### Категория 1: вероятно табличные/массивные данные, а не отдельные параметры

`WEG` (байты 2,4,6,8), `Tank_Prozess` (байты 10-18), `Tank_Input` (байты
10-28) имеют параметры в C08 (5, 11, 7 соответственно), но те покрывают
только часть блока — остальное выглядит как непрерывные осмысленные числа
(`2C 3A 40 46 18 29 31 37` в Tank_Prozess), похожие на массив точек
диапазона из статьи drive2 (часть 6/7 — пять 16-битных точек стрелки
топлива). Простой построчный парсер BimmerDaten разбирает только
однобайтовые битовые параметры, а такие массивы как единый именованный
параметр не извлекает. **Это не значит, что параметра нет** — скорее всего
он есть, просто типа "массив", который наш парсер не декодирует.
`CHECKCONTROL_ALIVE` байты 9,10 (`0x00` в обеих трассах) — похоже на
настоящий отступ/резерв.

### Категория 2: настоящие кандидаты — изолированные непомеченные биты внутри иначе закодированных байт

| Блок | Байт | Покрыто маской | Свободно | Значение (box=nobox) |
|---|---|---|---|---|
| **Steuerung_Anzeige_1** | **17** | ничем (0 параметров) | весь байт | **`0x0F`** — целый неименованный байт в блоке "управление отображением" |
| Ausstattung_PL2 | 10 | `0x3F` (FLA_VERBAUT и др.) | `0xC0` (биты 6-7) | `0b11` |
| ACC | 5 | `0x4F` (TEMPOMAT_SETZ_ANZ_DAUER + ещё один) | `0xB0` (биты 4,5,7) | `0b1011` в старшем ниббле |
| Check-Control | 63 | `0x01` | `0xFE` (биты 1-7) | `0x00` |

**Самый сильный кандидат — `Steuerung_Anzeige_1` байт 17.** Это блок
"управление отображением" (35 именованных параметров в остальных 17
байтах), но байт 17 не покрыт вообще ни одним из них, при этом содержит
не-FF значение `0x0F`, одинаковое на обеих приборках. По критерию из
статьи drive2 (часть 11): «действительно неиспользуемые участки как
правило содержат FF» — этот байт под критерий не подходит, значит это
кандидат на нераскрытый параметр именно в том смысле, что описан в статье.

### ⚠️ Важная оговорка

Ни один из кандидатов не выглядит по названию блока связанным с
напряжением бортсети или температурой ОЖ — среди имён нет ничего похожего.
Значения `0x0F`/`0b11`/`0b1011` могут быть чем угодно: технологическим
полем производителя, версией, зарезервированным под будущее применение, а
не «включателем нужной функции». Оба кандидата дают **одинаковое** значение
на обеих приборках — значит проверить гипотезу о смысле байта переключением
значения (как в статье, часть 11: добавить имя в SWTFSW и в C08, задать
`wert_02`, перекодировать и посмотреть, что изменится) можно только на
практике, экспериментально, на своей машине.

### Как это использовать дальше (если решите пробовать)

Техника из статьи drive2 часть 11 применяется так:
1. Добавить в `SWTFSW03.dat` новую пару KEYID→имя (например
   `SA_TEST_BYTE17`).
2. Добавить в `KMBI_PL2.C08` запись `PARZUWEISUNG_FSW` с адресом
   `Steuerung_Anzeige_1` байт 17, маска `0xFF`, и в `SWTPSW03.dat` —
   значения `wert_01`(0x0F, текущее)/`wert_02`(другое, для теста).
3. Перекодировать через NCS Expert на **своей** приборке (не на боевой
   без бэкапа) и посмотреть, что изменится на экране/в поведении.

Это первый шаг проверки для эксперимента, а не гарантия, что байт 17 как-то
связан с целью проекта (вольтметр/температура ОЖ). Значимость подтвердится
только опытным путём.


## ★ 0xFD7530 и 0xFD75B0 разобраны: два разных механизма отрисовки (2026-08-04)

Оба принимают `content_id` (первое поле записи очереди, `@RW3+0x06`) и
представляют собой **два независимых пути** от `content_id` до вызова
конечного «покрасочного» примитива. Общая деталь: и там, и там встречается
идиома `LSLW,#0x0E; LSRW,#0x0F` — выделение **бита 1** байта.

### 0xFD7530 — путь через прямую таблицу дескрипторов

```
FD7534: id = запись+0x06
FD7537: если [0x4642]==0 -> выход              ; общий флаг "подсистема готова"
FD753C: если id==0 -> выход
FD7540: RL2 = CALLP [0xF9EF7C](id)             ; дескриптор = &0xF825B2 + id*8
FD754D: flag = @RL2+0x07, бит 1
FD7559: CALL 0xFD421A(flag)                    ; если flag==1: проверить
                                                ;   IO[0xD5] бит1 (банк ADB) —
                                                ;   похоже на "готовность
                                                ;   периферии/шрифта"
FD755E: если проверка не прошла -> выход
FD7562: limit = CALLP [0xF9E892](id)           ; таблица 0xF81A72[id]:
                                                ;   0xFFFF если id>=0x2D0
                                                ;   или запись в таблице != 0
FD7568: если limit >= 0x1E0 (480) -> A=1, иначе бит-тест по
FD757C:   битовой карте 0x464F[limit>>3], бит (limit&7)
FD7599: если условие не выполнено -> выход
FD75A7: CALL 0xFD4DDF(id, arg+0x08, arg+0x0C, arg+0x0A)   ; <<< ФИНАЛЬНЫЙ ВЫЗОВ
```

**`0xF825B2`** — статическая таблица дескрипторов «на каждый `content_id`
своя запись 8 байт» (индекс `id*8`), похоже, ресурсы/шрифт/метаданные типа
содержимого. **`0x464F`** — битовая карта разрешённых `content_id` (или их
производных, `limit`), до 480 позиций (60 байт).

### 0xFD75B0 — путь через пул слотов отображения

Другая архитектура: не статическая таблица по `id`, а **пул из активных
"слотов"** — таблица `0x43BC`, запись 10 байт, слово `+0x00` = какой
`content_id` сейчас занимает слот, байт `+0x09` бит 1 = флаг "активен".

```
FD6042: линейный перебор слотов через итератор FD49CD/FD4B26(1,4,1),
        сравнение table[слот].content_id == искомый id -> вернуть индекс
        слота или 0xFF, если не найден
FD75B0: слот = FD6042(id)
  если слот не найден (0xFF):
    CALL 0xFD49CD(2,4,1)        ; попытка занять новый слот итератором
  иначе:
    подтвердить, что table[слот].id == id (могли переиспользовать)
    очистить флаг активности (AND ...,0xFD -- сброс бита 1)
    CALL 0xFD514C(слот, id)     ; <<< ФИНАЛЬНЫЙ ВЫЗОВ — отрисовать в слот
    если слот занят другим id -> освободить старый (0xFD4B26) и
    попробовать снова, до 0xFF
```

Это классический **менеджер пула отображаемых элементов**: у экрана
ограниченное число одновременно активных "слотов" (похоже, строк/ячеек
дисплея), `content_id` привязывается к слоту динамически, старые
вытесняются при нехватке места.

### Итог: два стиля рендеринга

| | `0xFD7530` | `0xFD75B0` |
|---|---|---|
| Таблица | `0xF825B2`, статическая, 8 Б/запись, индекс = `id` напрямую | `0x43BC`, пул слотов, 10 Б/запись, `id` ищется/назначается динамически |
| Проверка допустимости | битовая карта `0x464F` + готовность IO | занятость слота |
| Финальный вызов | `0xFD4DDF(id, x, y, ...)` | `0xFD514C(слот, id)` |

Вероятная причина разделения: `0xFD7530` — для содержимого с фиксированной
позицией на экране (id однозначно определяет место, таблица статична);
`0xFD75B0` — для содержимого, которое конкурирует за ограниченное число
одинаковых по формату мест (например, строк списка/очереди сообщений
Check-Control, а не постоянных полей типа спидометра).

### Граница разбора — намеренно остановлено здесь

`0xFD4DDF`, `0xFD514C`, `0xFD49CD`, `0xFD4B26` (сами примитивы отрисовки и
итератор пула) **не дизассемблированы**. Это следующий уровень — переход
от «диспетчеризации содержимого» к собственно записи пикселей/сегментов.
На данный момент установлено достаточно для практической цели: чтобы
вывести число на экран, нужно либо (а) получить `content_id`, для которого
уже существует запись в `0xF825B2` и бит разрешён в `0x464F`, либо
(б) пройти через менеджер слотов `0x43BC`. Оба пути гарантированно
проверены на не-мусорность: цепочка проверок (готовность, битовые карты,
занятость слота) — это защита от рисования несуществующего контента, а не
что-то, что можно обойти без понимания.


## ★ 0xFD4DDF и 0xFD514C разобраны: дошли до генерик-слоя (2026-08-04)

### 0xFD4DDF — диспетчер двухстрочного содержимого

400+ инструкций. Работает с тем же пулом слотов `0x43BC`, что и `0xFD75B0`,
но **резервирует/использует ДВА слота на один `content_id`** — характерная
пара вызовов в хвосте:

```
FD4F3D: CALL 0xFD514C(слот, 1)     ; строка 1
FD4F46: CALL 0xFD514C(слот, 2)     ; строка 2
```

Это подходит для содержимого из двух строк (например, заголовок+текст
сообщения Check-Control), в отличие от `0xFD75B0`, который занимает один
слот.

В самом конце, после операций со слотами, вызывается финальная тройка:

```
FD5129: RW0 = CALLP [0xF9F400](id, arg2)   ; заглушка -- ТОЛЬКО RETP, ничего не делает
FD5135: CALLP [0xF9F322](RW0, id, 0)
FD5141: CALLP [0xF9F471](RW0, id, 0)
```

**`0xF9F400` оказался пустой заглушкой** (`LINK; RETP` без единой
содержательной инструкции) — в этом конкретном пути конвейера значение не
вычисляется здесь, оно уже подготовлено выше по стеку вызовов (в
не разобранных `FD4578`/`FD4888`/`FD4994`/`FD4814`/`FD48B6`/`FD492D`/
`FD4C98`).

### 0xF9F322 / 0xF9F471 — не форматтеры, а буферы с кэшированием

Оба устроены одинаково: пара «ключ/буфер» в ОЗУ (`[0x073C]`/`[0x073F]` у
первого, `[0x0706]`/`[0x0709]` у второго). Если новый ключ совпадает с
предыдущим — работа пропускается (значение уже в буфере с прошлого раза).
Если отличается — вызывается `0xFCF66E(буфer, источник)`.

**`0xFCF66E` — это `strcpy`**: копирует байты из источника в приёмник
до нулевого байта. Чистая утилита работы со строками, ничего
специфичного для отображения.

```
FCF670: dest = arg1 ; src = arg2
FCF676: цикл: dest[i] = src[i] ; if src[i]!=0 continue
```

### Итог вертикального разбора

Прошёл цепочку на 9 уровней вниз — от CAN-сообщения до этой точки:
```
CAN 0x1D2 -> RAM 0x09FB -> геттер атрибута -> show_element ->
диспетчер -> упаковка дескриптора -> кольцевая очередь -> потребитель ->
FD4DDF/FD75B0 (менеджер слотов) -> F9F322/F9F471 (буфер+кэш) -> strcpy
```

**Здесь код стал полностью общим (generic) слоем буферизации строк**,
не относящимся конкретно ни к передаче, ни к какому-либо одному типу
содержимого — это инфраструктура, используемая всеми `content_id`
одинаково. Собственно вычисление значения (чтение датчика/счётчика,
превращение числа в текст) происходит **до** этой точки, в функциях,
специфичных для каждого типа контента, которые ещё не разобраны:
`FD4578`, `FD4888`, `FD4994`, `FD4814`, `FD48B6`, `FD492D`, `FD4C98`.
Ни в одной из них не нашлось деления (`DIVUW`/`DIVU`) — то есть
форматирование чисел, если оно тут, использует не арифметику "цифра за
цифрой", а что-то другое (таблицу, BCD, или лежит ещё глубже).

### Рекомендация для продолжения (если решите)

Дальнейший вертикальный спуск по `FD4DDF`/`FD514C` малопродуктивен — это
общая инфраструктура. **Более быстрый путь к цели с вольтметром/ОЖ**:
взять готовый числовой `content_id`, который уже показывает похожее
значение (например, наружная температура — известно, что она обслуживается
`F9CEC9`/`F9CEC3` из перехода уровня 3->4, привязана к блоку
`Aussentemperatur`), найти его запись в дескрипторной таблице `0xF825B2`
(по формуле `id*8`), и проследить путь его собственного форматирования —
это покажет конкретный, работающий пример «сенсор -> число -> текст на
экране» короче, чем продолжать разбор общей инфраструктуры слотов.


## ★★ Найден цифровой блок BC (Bordcomputer): скорость/расход/дальность/средний расход (2026-08-04)

По просьбе владельца сместил фокус с наружной температуры (другой дисплей)
на цифровой блок бортового компьютера — и нашёл именно то семейство
режимов, которое нужно.

### 0xF9EF7C — подтверждено: дескриптор по content_id

```
F9EF7C: id = @RW3+0x06
        если id < 0 -> вернуть NULL (0)
        иначе: адрес = 0x00F825B2 + id*8   (LSLL,#3 = *8)
```

Статическая таблица дескрипторов, 8 байт на запись, индекс = `content_id`
напрямую. Подтверждает разбор из прошлого шага.

### Найден переключатель режимов цифрового BC-дисплея

**`0xFE9AB6` — `next_bc_mode(текущий)`**: `режим = (текущий+1) mod 6`,
с пропуском режимов, не разрешённых кодированием:

```
если [0x1610]==0 и режим==2: проверить валидность через указатель [0x544C]
если режим==4: если НЕ включён DIGITAL_KVA (Ausstattung_PL2 байт8 бит7,
               RAM 0x0A9C:7) -> пропустить, взять следующий
если режим==5: если НЕ включён BC_DIGITAL_V (Steuerung_Anzeige_1 байт1
               бит1, RAM 0x13AB:1) -> пропустить
если [0x1610]==0 и GETRIEBE_ART в {automatik,ssg} (не механика):
    остановиться на любом режиме
иначе (механика): режим==0 пропускается, если не разрешён предикат FAD862
```

**Диспетчер режимов — `0xFE979E`**, ветвление по `RW1` (0-5):

| Режим | Обработчик | Источник значения | Форматтер | Что это, скорее всего |
|---|---|---|---|---|
| 0 | `0xFE996C` | — | — | не установлено |
| 1 | `0xFE9819` | `0xFCB739` | `0xFE9BDD` (свой) | **вероятно ЗАПАС ХОДА** (свой формат, без общих констант с расходом) |
| 2 | `0xFE9856` | через указатель `[0x5448]` | — | не установлено (подключаемый обработчик) |
| 3 | `0xFE97DE` | `0xFCAFC5` | `0xFE9B60` (тот же, что режим 4!) | **вероятно СРЕДНИЙ РАСХОД** (тот же класс величины, что и режим 4) |
| **4** | `0xFE9909` | `0xFE9A4E` | `0xFE9B60` | **ЦИФРОВОЙ РАСХОД (DIGITAL_KVA)** — подтверждено кодировочным гейтом |
| **5** | `0xFE98A9` | `0xFCB7F6` | `0xFE9C06` (свой) | **ЦИФРОВАЯ СКОРОСТЬ (BC_DIGITAL_V)** — подтверждено кодировочным гейтом |

**Режимы 4 и 5 доказаны** — привязаны к конкретным именованным параметрам
кодирования (`DIGITAL_KVA`, `BC_DIGITAL_V` из `KMBI_PL2.C08`). Режимы 1 и 3
— **гипотеза** по структурному сходству (общий форматтер с расходом для
режима 3, собственный для режима 1), не подтверждено именами.

### Сглаживание расхода — 0xFE9909 (режим 4)

```
FE990D: сырое = CALL [0xFE9A4E]
FE9913: если сырое == 0xFFFE (нет данных) -> взять предыдущее фильтрованное
        иначе: если F9FF7E([0x2CFE],[0x2D00]) не прошло:
                  [0x2D02] = сырое ; [0x2D00] = CALLP F9FF7A(...)
               иначе: использовать [0x2D02]
```

Классическая фильтрация мгновенного расхода — сглаживание против
скачков показаний, типичное поведение "instantaneous consumption" во
всех бортовых компьютерах.

### Источник сырого значения расхода — 0xFE9A4E

Не работает с CAN-буфером напрямую (в отличие от `0x1D2`) — вызывает
`0xFBEC36` (получить raw + признак единиц измерения через `0xFC1ACD`),
затем пересчитывает по одной из трёх констант в зависимости от единиц:
`0x2710`(10000), `0x6E58`(28248), `0x5BE1`(23521) — это коэффициенты
конверсии л/100км ↔ миль/галлон (imperial/US). Сентинель отсутствия
данных — `0x03E7` (999).

### Источник скорости — 0xFCB7F6

Не единый источник, а цепочка кандидатов с проверкой валидности:
`CALLP [0xFAE649]` → если не годится и не установлен флаг `[0x0C50]:2` →
`CALLP [0xFAE63C]` → если не годится → `CALLP [0xFAE5A3]`. Похоже на выбор
между несколькими источниками скорости (колёсный датчик / ABS / резерв).

### Граница разбора

Не дошёл до конкретных CAN-адресов/сообщений, откуда `0xFBEC36` и цепочка
`FAE649/FAE63C/FAE5A3` берут сырые данные — это следующий уровень, по духу
аналогичный тому, как был найден буфер `0x4140` для `0x1D2`. Также не
разобраны обработчики режимов 0, 2 и сами форматтеры чисел
(`0xFE9B60`,`0xFE9BDD`,`0xFE9C06`,`0xFE9C06`) — именно там, скорее всего,
живёт настоящее превращение числа в текст (деление/остаток на 10 и т.п.,
не найденное на предыдущем уровне).

### Практическая ценность для цели проекта

Это самый близкий из всех найденных путей к нужному для вольтметра и
температуры ОЖ: **готовая, кодированием управляемая, циклическая
инфраструктура BC-дисплея** с чётким паттерном
`raw_fetch -> (опционально сглаживание) -> formatter -> show_element`.
Если добавлять новое значение, естественный путь — не городить отдельный
элемент с нуля, а либо расширить этот цикл `next_bc_mode` седьмым режимом,
либо переиспользовать один из уже существующих (0,2 — не идентифицированы,
возможный кандидат на замену/расширение).


## ⚠️ Поправка: 0xFE9B60/0xFE9C06 — НЕ форматтеры, а санитизация диапазона (2026-08-04)

Разбор показал: то, что в прошлой записи было названо "форматтер", на
самом деле — функции **ограничения диапазона значения по единице
измерения**, вызываемые ПЕРЕД настоящим форматированием, а не вместо него.

### 0xFE9C06 (режим 5, скорость) — 12 инструкций, без вызовов

```
если значение != 0xFFFE (нет данных):
    если значение > 0x270F (9999) -> обрезать до 9999
```

### 0xFE9B60 (режимы 3 и 4, расход) — диспетчер по единице измерения

`0xFC1ACD` возвращает код единицы (0-3), для каждой — свой диапазон:

| Код единицы | Мин | Макс |
|---|---|---|
| 0 (по умолчанию) | — | `0x18B` (395) |
| 1 | `0x46` (70) | `0x3E7` (999) |
| 2 | `0x3C` (60) | `0x3E7` (999) |
| 3 | `0x19` (25) | `0x3E7` (999) |

Правдоподобно: единица 0 — л/100км×10 (макс 39.5), единицы 1-3 —
разные варианты миль/галлон (UK/US) и км/л, с не пересекающимися
допустимыми диапазонами разумных значений расхода.

### Значение находки

**Настоящее превращение числа в текст ещё не найдено.** Оно происходит
либо (а) в коде, который получает уже клэмпнутое значение из этих функций
и вызывается ПОСЛЕ них (не проверено — вызывающий код мы разобрали раньше
этих функций, нужно вернуться на уровень выше и посмотреть, что делается
с результатом после вызова клэмпа), либо (б) через табличный метод
(precomputed lookup вместо деления), что объясняет, почему ни в одной из
проверенных ранее функций (`FD4578` и др.) не нашлось `DIVUW`.

Обновление статуса: практическая цепочка для BC-дисплея теперь выглядит
так:

```
raw_fetch -> (сглаживание, только для расхода) -> клэмп диапазона по
единице измерения (FE9B60/FE9C06) -> ??? число-в-текст (не найдено) ->
show_element/очередь -> отрисовка
```


## ★★★ Найдено число-в-текст: 0xFDC80D — универсальный itoa() (2026-08-04)

Вернулся к вызывающему коду сразу после клэмпа `0xFE9C06` в обработчике
режима 5 (`0xFE98A9`) и нашёл настоящее форматирование.

### Хвост 0xFE98A9 — сборка строки "ЦЕЛОЕ.ДРОБНОЕ"

```
FE9A00: DIVUW значение/10             ; частное = целая часть/10... (см. ниже)
FE9A0C: RW1 = CALLP [0xFDC80D](частное)   ; <<< форматирует ЦЕЛУЮ часть в ASCII
FE9A22: buf[RW1] = 0x2E               ; '.' десятичная точка
FE9A2B: DIVUW значение/10 -> остаток  ; последняя цифра (десятые)
FE9A2E: цифра = остаток + 0x30        ; '0'..'9' ASCII
FE9A3C: buf[RW1+1] = цифра
FE9A44: buf[конец] = 0                ; завершающий ноль
```

Формат вывода — **`ЦЕЛОЕ.Д`** (целая часть плюс один знак после запятой).

### 0xFDC80D — универсальный конвертер 32-битного числа в десятичную строку

```
итог = FDC80D(value, output_buffer)
```

Алгоритм классический (без стека переменной длины):
1. **Цикл 1** (`FDC81F-FDC839`): делит `value` на 10 через `FCF48C`,
   одновременно копит в `@RW3-0x04` делитель `10^(N-1)`, умножая его на 10
   через `FCF5A0` на каждой итерации, пока частное не станет 0 — то есть
   **сначала считает, сколько всего цифр** в числе.
2. **Цикл 2** (`FDC83D-FDC874`): извлекает цифры от старшей к младшей:
   частное = `value / делитель` (`FCF48C`), цифра = `частное % 10`
   (`FCF52F`), `цифра + 0x30` → ASCII, пишет в `output_buffer[позиция]`,
   затем `делитель /= 10` и повтор.
3. Возвращает `RW0` = число записанных цифр.

Строит-помощники — реализация 32-битных операций программно (чип не имеет
аппаратного 32-битного делителя):
- **`0xFCF48C`** — беззнаковое деление 32/32 (с быстрым путём через
  аппаратный `DIVUW`, когда делитель помещается в 16 бит; иначе —
  классический алгоритм сдвиг-вычитание с нормализацией через `NRML`)
- **`0xFCF52F`** — тот же алгоритм, но возвращает остаток вместо частного
- **`0xFCF5A0`** — 32-битное умножение через комбинацию `MULUW`

### Итог: полная и подтверждённая цепочка BC-дисплея

```
CAN/сенсор -> raw_fetch -> (сглаживание, для расхода) ->
  клэмп диапазона по единице измерения (0xFE9B60/0xFE9C06) ->
  0xFDC80D(value, buf) -> "ЦЕЛОЕ" (32-битный itoa, FCF48C/FCF52F/FCF5A0) ->
  дописать '.' и одну дробную цифру ->
  show_element / кольцевая очередь -> менеджер слотов -> отрисовка
```

**`0xFDC80D` — это готовый, универсальный, проверенный на 32-битных
значениях преобразователь "число → ASCII-строка", не привязанный к
скорости или расходу конкретно.** Это ключевая находка для практической
цели проекта: чтобы вывести напряжение бортсети или температуру ОЖ как
число на экран, не нужно писать свой numeral-to-text — можно напрямую
вызвать `0xFDC80D(значение, буфер)` и получить готовую десятичную строку,
как это делает вся остальная прошивка.

### Что дальше, если продолжать в практическую сторону

1. Проверить аналогичный хвост в обработчике режима 4 (расход,
   `0xFE9909`, после его собственного клэмпа `0xFE9B60`) — весьма вероятно,
   что там та же схема "0xFDC80D + точка + дробная цифра", но не
   подтверждено чтением кода.
2. Понять формат вывода буфера в `show_element`/дескриптор `0xF825B2` —
   как строка ASCII попадает в `content_id`-запись (это последнее
   недостающее звено между "у меня есть готовая строка" и "она появилась
   на экране").
3. Найти источник сырых значений напряжения/температуры на шине (эта часть
   не относится к KOMBI-прошивке напрямую — physical DME/PT-CAN, отдельная
   ECU, недоступная в имеющихся дампах).


## ★★★ Три вопроса закрыты: путь отрисовки BC, и источники напряжения/ОЖ (2026-08-04)

### 1. Режим 4 (расход) подтверждён — буквально тот же код

`0xFE9909` (mode4) переходит `JMP` (не `CALL`, то есть без нового кадра
стека) в общий хвост `0xFE99A5`, идентичный байт в байт хвосту `0xFE98A9`
(mode5, скорость). Это не "похожий код" — это **один и тот же код**,
общий для режимов 3/4/5. Формула `0xFDC80D + '.' + одна дробная цифра`
подтверждена для расхода так же строго, как для скорости.

### 2. Как строка попадает на экран — ОБНАРУЖЕН ВТОРОЙ, ОТДЕЛЬНЫЙ ПУТЬ ОТРИСОВКИ

Важное уточнение к прежней картине. Прослеживая, откуда берётся буфер
вывода (`0xFE930E`, вызывающая диспетчер режимов `0xFE979E`), выяснилось:
**цифровой BC-дисплей НЕ проходит через систему `content_id` / кольцевую
очередь / пул слотов** (`FB65C7`/`FD4DDF`/`FD75B0`/`0xF825B2`), которую мы
разбирали раньше. У него **свой, более прямой путь**:

```
0xFE930E: буфер = локальная переменная на стеке (LINK 0x1E, ~26 байт)
  -> CALL 0xFE979E(режим, ..., &буфер)   ; получить готовую строку
  -> CALLP [0xFDB9E0] / [0xFDBB85]        ; измерить ширину текста
  -> CALLP [0xFDBC25]                     ; закрасить фон (тот же примитив
                                           ;   заливки, что и в рамке!)
  -> CALLP [0xFDB9F0]                     ; измерить строку для центрирования
  -> CALLP [0xFDC0D1]                     ; НАРИСОВАТЬ ТЕКСТ
```

**`0xFDB9F0` и `0xFDC0D1` — это ТЕ ЖЕ САМЫЕ функции измерения и отрисовки
текста**, что использовались в самой первой разобранной функции проекта —
`0xFE616F`, которая рисует букву передачи и квадратик вокруг неё!
`0xFDBC25` (заливка) — из того же семейства, что и `0xFDBA65`
(дизер-заливка контура рамки).

**Вывод: в прошивке минимум два независимых механизма вывода на экран.**
Система `content_id`/очередь/слоты — вероятно, для Check-Control-сообщений
и иконок. Прямой путь `format -> measure -> center -> fill -> draw text` —
для цифровых показометров (скорость, расход) И для индикатора передачи.
**Это хорошая новость: механизм, нужный для цели проекта, — тот же самый,
что уже полностью разобран с самого начала расследования.**

### 3. Нужен ли дамп DME — НЕТ, подтверждено по двум независимым основаниям

Интуиция владельца верна. Проверил по community DBC-проекту (уже
локально, не нужен новый источник):

| Сигнал | CAN ID | Байт/биты | Формула | Получатель |
|---|---|---|---|---|
| **Температура ОЖ** | `0x1D0` `EngineData` | байт 0, `TEMP_ENG` | raw−48 = °C | **Kombi, CIC** |
| **Напряжение борта** | `0x3B4` `PowerBatteryVoltage` | биты 0-11, `BatteryVoltage` | raw×0.015 = В | **Kombi, CIC** |

**Оба сообщения уже перечисляют `Kombi` как получателя** — то есть
приборка их и так штатно принимает (иначе откуда доступны диагностические
пункты `09.00 UB` и `07.00 KTMP-MOM` из ранней разведки KOMB87.PRG —
теперь понятно, откуда они это читают).

Прошивку DME разбирать не нужно по трём причинам:
1. Нам не важно, **как** DME вычисляет значения внутри себя — важно, что
   уже лежит на шине, а это community-DBC уже документирует с проверенной
   формулой.
2. KOMBI уже официально числится получателем обоих сообщений — значит
   в прошивке KOMBI, скорее всего, уже есть распаковщик (буфер вроде
   `0x4140` для `0x1D2`), просто сейчас не используемый для отображения на
   основном циферблате.
3. Прошивка DME — это engine management, совсем другой уровень риска и
   объёма работы, выходящий далеко за рамки уже начатого разбора KOMBI.

**Следующий практический шаг**, если продолжать: искать в прошивке KOMBI
распаковщики `0x1D0` и `0x3B4` той же техникой, что нашла буфер `0x4140`
для `0x1D2` — по идиоме "чтение буфера, маска/сдвиг, запись в RAM с гейтом
на флаг обновления". Если найдутся — это будет готовый источник живых
данных, который останется только подключить к уже понятному пути
`format(0xFDC80D) -> measure -> draw`.


## Поиск распаковщиков 0x1D0 и 0x3B4 (2026-08-04): не завершён, причина методическая

### Что проверено

1. **Обобщил идиому `CLRB флаг ... BBS флаг,→назад`** (нашла `0x1D2`) на весь
   образ. Нашла ровно 7 таких пар. Кроме уже известной (`[0x2632]`/`0x1D2`)
   и второй, тоже транспортной (`[0x2630]`, буфер `0x4170-0x4171` —
   похоже на **распаковщик `0x304 GearDisplay`**, собирает символ через те
   же таблицы `0xF83C64/0xF83C74`, что и индикатор передачи), остальные 5
   пар оказались обычными флагами состояния разных подсистем, не
   CAN-идиомой.
2. **Картировал диапазон `0x4000-0x4400`** по признаку «только чтение, без
   записи» (сигнатура CAN-буфера). Нашёл несколько плотных 6-8-байтных
   кластеров-кандидатов.
3. **Искал "пачки" обращений** — несколько разных адресов буфера, читаемых
   подряд в узком окне инструкций (сигнатура настоящего распаковщика).
   Нашёл 5 таких мест:
   - `0xFAA3BB`, буфер `0x41B4-0x41BA`: **отклонён** — проверки диапазона
     `<=0x3B(59)` и `<=0x17(23)` выдают в нём часы:минуты:секунды
     (вероятно, `GPS_UHR`), не температуру/напряжение.
   - `0xFCCDE0` (и два его двойника `0xFCCE53`/`0xFCCED0`), буфер
     `0x425C-0x4262`: детектор изменения содержимого (сравнение с кэшем
     `0x2F9C..0x2FA2`, флаг `[0x2FD6]:4`) — структурно похож на настоящий
     распаковщик CAN-сообщения, используется из **трёх независимо
     скомпилированных мест**, но рядом не нашлось кода преобразования
     значения (умножения/вычитания под формулы `raw−48` или `raw×0.015`
     из DBC), поэтому подтвердить принадлежность **не удалось**.
4. **Прямой поиск `SUB A, 0x30`** (смещение −48 из формулы температуры) —
   **ноль совпадений** во всём образе.

### Почему не получилось (в отличие от 0x1D2)

Для `0x1D2` поиск сработал, потому что был **известный потребитель**:
`RAM 0x0CFD`, найденный через цепочку рамки, и от него удалось пройти
назад до распаковщика. Для `0x1D0`/`0x3B4` такого потребителя нет —
KOMBI сейчас **не отображает** ни температуру ОЖ, ни напряжение борта на
основном циферблате, значит нет кода, который их *использует*, от
которого можно было бы оттолкнуться поиском назад. А поиск вперёд
(угадывание буфера по эвристикам "только чтение", "пачка обращений")
даёт кандидатов, но не умеет однозначно подтвердить, какому CAN ID
какой буфер соответствует — потому что таблица фильтров CAN-контроллера
(связка "ID сообщения -> адрес буфера") так и не найдена (см. более
раннюю запись об этом же тупике при поиске инициализации `0x09FB`).

### Более многообещающий путь для следующей попытки

Диагностические пункты `09.00 (UB)` и `07.00 (KTMP-MOM)`, упомянутые в
самом начале расследования (список заданий EDIABAS из `KOMB87.PRG`),
почти наверняка обращаются к твёрдо заданному **идентификатору службы
диагностики** (аналог UDS "Read Data By Local Identifier"), который
обработчик диагностики в прошивке резолвит в конкретный адрес ОЗУ. Если
найти диспетчер этих идентификаторов (по духу похожий на найденную ранее
таблицу дескрипторов кодирования `0xF8379A` — вероятно, тоже таблица
"идентификатор -> адрес, длина"), можно выйти на нужные адреса напрямую,
не гадая по эвристикам буфера. Это не то же самое, что искать сам CAN
unpacker — это, возможно, более короткий путь, поскольку диагностический
обработчик обязан явно знать, откуда брать данные для ответа на конкретный
идентификатор.


## ★★★ КЛЮЧЕВОЕ ДЛЯ ПРАКТИКИ: диагностический протокол уже умеет то, что нужно (2026-08-04)

### Инструмент: decoderPrg.py из BimmerDaten расшифровывает .prg (XOR 0xF7)

`KOMB87.prg` оказался зашифрован простым XOR (`0xF7`), поэтому строки не
находились. `BimmerDaten/decoderPrg.py` — готовый декодер формата
EDIABAS BEST/1/BIP, даёт полный список из 140 заданий с байт-кодом.

### Карта идентификаторов службы KWP2000 $21 (ReadDataByLocalIdentifier)

Извлечена из собираемого в каждом задании телеграмма
`82 FF F1 21 <ID>`:

| ID | Задание | Значение |
|---|---|---|
| 0x05 | STATUS_TACHO_LESEN | скорость |
| 0x06 | STATUS_DREHZAHL_LESEN | обороты |
| 0x09 | STATUS_CHECKCONTROL_LESEN | Check-Control |
| 0x0A | STATUS_TANKINHALT | уровень топлива |
| 0x0B | STATUS_GLOBAL_KM | пробег |
| 0x0E | STATUS_KLEMMEN | состояние клемм |
| **0x21** | **STATUS_KLEMMENSPANNUNG** | **напряжение борта** |
| 0x22 | STATUS_A_TEMP_LESEN | наружная температура |

**Задания на температуру ОЖ у KOMBI нет вообще** — ни в списке из 140
заданий, ни под этой службой. Подтверждает вывод: температуру ОЖ меряет
DME, KOMBI её не публикует как собственный диагностический параметр (даже
если и принимает по CAN для внутреннего использования, например для
Check-Control «перегрев»).

### Диспетчер по этим ID в прошивке — НЕ найден в этой сессии

Проверил все места `CMP A, 0x21` в коде — оказались **ложным
срабатыванием**: это сравнение с диапазоном `0x20-0x25`, похоже на коды
диагностической **сессии** (`StartDiagnosticSession`), не на диспетчер
идентификаторов данных. Настоящий диспетчер для `$21`-запросов не
локализован. Открытая задача, если возвращаться к этому вопросу.

### ★ Более важная находка: штатный механизм подмены значения на стрелке

```
STEUERN_TACHO: "Tacho auf beliebige Geschwindigkeit (0..300) setzen"
               KWP2000: $30 InputOutputControlByLocalIdentifier

STEUERN_KVA:   "Momentanverbrauch in L/100km vorgeben...
               In gleicher Weise ist die Ansteuerung der
               Oeltemperaturanzeige möglich - gleiches Argument
               für gleiche Zeigerstellung übergeben"
               KWP2000: $30 InputOutputControlByLocalIdentifier
```

BMW сама документирует в заводском диагностическом задании: **стрелку
KVA можно подменить произвольным значением через штатный диагностический
сервис `$30`, и та же стрелка управляет отображением температуры масла**
— это ровно приём из статьи drive2 (часть 6), но подтверждённый
официальной документацией задания, а не только реверсом статьи.

Такие задания есть для: `STEUERN_TACHO`, `STEUERN_DREHZAHL`,
`STEUERN_KVA`, `STEUERN_TANK`, `STEUERN_ACC_ZEIGER`, `STEUERN_VWF`.
Служба `$30 InputOutputControlByLocalIdentifier` по стандарту KWP2000
обычно действует, пока диагностическая сессия удерживается открытой
(`shortTermAdjustment`) — то есть внешнее устройство, поддерживающее
K-CAN/KWP2000 и удерживающее сессию, может **непрерывно перезаписывать
показания существующей стрелки в реальном времени**, без единой правки
прошивки и без обхода `AUTHENTISIERUNG`/`FLASH_SIGNATUR_PRUEFEN`.

**Ограничение: подтверждено только для аналоговых стрелок**, не для
цифрового BC-дисплея (нашей основной находки этой сессии). Заданий
`STEUERN_SPANNUNG`/`STEUERN_TEMP`, нацеленных на цифровое поле, в списке
из 140 не нашлось.

### Побочная, отложенная находка: задания аутентификации теперь читаемы

`AUTHENTISIERUNG_ZUFALLSZAHL_LESEN` (@0x4390A) и `AUTHENTISIERUNG_START`
(@0x446AD) теперь доступны для дизассемблирования через `decoderPrg.py` —
то есть путь B (перепрошивка) стал на шаг более исследуемым, если решите
им заниматься отдельно. Не разбирался в этой сессии — не входило в
задачу, и это отдельный, больший по объёму риск.


## ★★★ НАЙДЕНА подсистема АЦП: источник напряжения бортсети (2026-08-04)

Прошлая попытка искать распаковщики CAN `0x1D0`/`0x3B4` провалилась. В этот
раз зашёл иначе и нашёл **правильный источник**: напряжение приборка меряет
**собственным АЦП**, а не берёт с шины. Это следует из самого названия
диагностического задания — `STATUS_KLEMMENSPANNUNG` = «Klemmenspannung»,
напряжение на клемме **самой приборки**, и подтверждается кодом.

### Обработчик результата АЦП (0xF9C4B7)

```
F9C4B9: MOV  A, IO[0x35] ; AND 0x40 ; BZ выход   ; флаг завершения преобразования
F9C4D8: MOVW A, IO[0x36] ; ANDW A, 0x03FF        ; 10-битный результат
F9C4FD: A = канал ; LSLW (x2) ; ADDW 0x02A0
F9C504: MOVW @RW4+0x00, A                        ; результаты[канал] = значение
F9C507: MOV  @RW1+0x02B0, 1                      ; флаг готовности[канал] = 1
```

| Что | Адрес |
|---|---|
| **массив результатов АЦП** | **`0x02A0`**, 2 байта на канал, 10 бит (0-1023) |
| флаги готовности | `0x02B0`, 1 байт на канал |
| регистры АЦП | `IO[0x34]/[0x35]` управление, `IO[0x36]` результат |

### API чтения

| Функция | Что делает |
|---|---|
| **`0xF9C607`** | `read_adc(логич_канал)` -> значение |
| `0xF9C647` | то же, но возвращает **адрес** ячейки |
| `0xF9C58E` | альтернативный вариант (используется чаще) |

Все три работают одинаково: логический номер канала -> таблица
соответствия по **`0x29DA`** (8 байт на запись, в ОЗУ, заполняется при
инициализации) -> физический канал -> `0x02A0 + 2*канал`.

### Каналов семь (0-6)

Подтверждено диагностическим обработчиком `0xFB07A4`, который в цикле
`RW1 = 0..6` читает все каналы и складывает в ответ. Там же рядом
(`0xFB07ED`) — вариант с чтением одного канала по номеру из подпараметра
телеграммы, с проверкой `<= 6`.

Реально используемые в коде каналы: **1, 3, 4, 5, 6**.

| Канал | Кто читает |
|---|---|
| 1 | `0xFC36BC`, `0xFC36C8`, `0xFC3755` |
| 3 | `0xFAB4B0`, `0xFBD3B0` |
| 4 | `0xFAB2B4` (в диагностическом слое) |
| 5 | `0xF9D42A`, `0xF9D434`, `0xF9D4E0`, `0xF9D4EF` |
| 6 | `0xFBE03A` |

### ⚠️ Какой именно канал — напряжение, НЕ установлено

Просмотрел контекст каждого — ни в одном не нашёл однозначного признака
(например, пересчёта в милливольты, который должен быть, раз
`STATUS_KLEMMENSPANNUNG` возвращает мВ). Кандидаты по косвенным признакам:
канал 4 (читается прямо в диагностическом слое `0xFAB2xx`, там же, где
кодирование и контрольные суммы) и канал 5 (больше всего обращений).
**Требуется дальнейшая проверка** — либо найти пересчёт в мВ, либо
эмпирически: подать на приборку разное напряжение и посмотреть, какая
ячейка `0x02A0+2n` меняется.

### Почему это важнее, чем поиск CAN-распаковщика

Для цели проекта это **лучше**, чем данные с шины:
1. Значение уже лежит в ОЗУ приборки в известном месте (`0x02A0+2n`),
   обновляется аппаратно, без всякой зависимости от CAN.
2. Есть готовый API (`0xF9C607`) — при патче прошивки его можно вызвать
   ровно так же, как это делает штатный код.
3. Не нужно ничего распаковывать и синхронизировать с флагами обновления
   сообщений.

Для температуры ОЖ это **не работает** — её приборка своим АЦП не меряет
(нет ни задания, ни, судя по названиям, подходящего канала), она приходит
по CAN `0x1D0` от DME. Так что для ОЖ вопрос с распаковщиком остаётся
открытым, а для **напряжения источник найден**.


## ★★★ ОТВЕТ: канал АЦП 1 = напряжение бортсети, значение в мВ по 0x0FA0 (2026-08-04)

### Доказательство

**1. Линейный пересчёт в милливольты** (`0xFC36E9`):
```
FC36E9: MOV A, 0x13         ; 19
FC36EB: MULUW A,RW0         ; 19 * АЦП
FC36EE: MOVW A, 0x026C      ; 620
FC36F1: ADDW RW0,A          ; + 620
```
**`мВ = 19 x АЦП + 620`**. При 10-битном АЦП (0-1023) даёт диапазон
620 мВ ... 20 057 мВ — ровно то, что нужно для измерения бортсети через
резистивный делитель.

**2. Автомобильные пороги с гистерезисом** (`0xFC38E9-0xFC3924`) —
решающее подтверждение:

| Условие | Порог | Сброс | Флаг |
|---|---|---|---|
| Пониженное напряжение | < `0x1D4C` = **7500 мВ** | > `0x1F40` = 8000 мВ | `[0x0FA4]:3` |
| Повышенное напряжение | > `0x4074` = **16500 мВ** | < `0x3E80` = 16000 мВ | `[0x0FA4]:4` |

Классические пороги 7,5/8,0 и 16,5/16,0 В с гистерезисом 0,5 В для
12-вольтовой сети. Никакая другая измеряемая величина такие пороги иметь
не может.

### Итоговая карта: где лежит напряжение

| Что | Адрес | Формат |
|---|---|---|
| сырой отсчёт АЦП | `0x02A0 + 2*физ_канал` | 10 бит (0-1023) |
| **напряжение, милливольты** | **`0x0FA0`** | **16 бит, готовое значение** |
| то же, 32-битная версия | `0x0F9C` | 32 бита |
| состояние конечного автомата | `0x0FA6` | 1..3 |
| флаг пониженного напряжения | `[0x0FA4]:3` | бит |
| флаг повышенного напряжения | `[0x0FA4]:4` | бит |
| логический канал АЦП | **1** | для `read_adc(1)` = `0xF9C607`/`0xF9C58E` |

Читатели `[0x0FA0]`: `0xFC376D`, `0xFC38E9`, `0xFC38FA`, `0xFC390B`,
`0xFC391C`, `0xFCE6AB`.

### Заодно опознан канал 5 = наружная температура (NTC)

Канал 5 (`0xF9D4E0`) прогоняется через таблицы линеаризации
`0xF8199A` (отсчёты АЦП: 207, 275, 358, 452, 551, 599, 644, 685, 721, 779,
818, 843) и `0xF819B2` (значения: 1440, 1280, 1120, 960, 800, 720, 640,
560, 480, 320, 160, 0). Обратная зависимость (значение падает с ростом
отсчёта) — характерная кривая термистора NTC. Это датчик наружной
температуры, а не ОЖ.

### Что это даёт практически

Для вывода напряжения на дисплей **больше ничего искать не нужно**:
готовое значение в милливольтах уже лежит по фиксированному адресу
`0x0FA0`, обновляется само. При патче прошивки достаточно прочитать это
слово и передать в уже разобранный конвейер
(`0xFDC80D` -> число в текст -> отрисовка), ровно как это делает штатный
код для скорости.

Температура ОЖ по-прежнему недоступна изнутри приборки — её нет ни среди
каналов АЦП (канал 5 это наружная), ни среди диагностических заданий.
Она приходит только по CAN `0x1D0` от DME, и её распаковщик в прошивке
пока не найден.


## ★★★ НАЙДЕНА температура ОЖ: сырое значение по адресу 0x413A (2026-08-04)

Прошлые попытки искали распаковщик CAN вслепую. В этот раз искал **формулу
из DBC** (`raw - 48 = degC`) во всех вариантах кодирования, а не только
`SUB A,0x30` — и нашёл через `SUBW A, 0x0030`.

### Место применения формулы (0xF9D1BE)

```
F9D1B9: BBC [0x28B9]:0, F9D1E1   ; флаг валидности сигнала
F9D1BE: MOV  A, [0x413A]         ; <<< СЫРОЕ ЗНАЧЕНИЕ
F9D1C1: SUBW A, 0x0030           ; -48 -> градусы Цельсия
F9D1C4: MOVW @RW3-0x04, A
F9D1CD: MOV  A, [0x413A]
F9D1D0: CBNE A, 0xFF, ...        ; 0xFF = сигнал недоступен
F9D1D3: RW2 = 1                  ; флаг "нет данных"
F9D1DB: CALLP [0xF9CF7E](темп, флаг)
```

**Точное совпадение с DBC**: `TEMP_ENG : 0|8@1+ (1,-48)` формула
`raw - 48 = degC`, и примечание про `0xFF` = «signal not available».
Это байт 0 сообщения `0x1D0 EngineData` от DME.

### Карта: где лежит температура ОЖ

| Что | Адрес | Формат |
|---|---|---|
| **сырое значение** | **`0x413A`** | 1 байт, `значение - 48 = °C`, `0xFF` = нет данных |
| флаг валидности | `[0x28B9]:0` | бит |
| копия для диагностики | `0x12B8` | через обработчик `0xFCDB14` |
| сброс по таймауту | `0xFB6C45` | пишет 0 при потере сигнала |

Читатели: `0xF9D1BE`, `0xF9D1CD` (основной путь), `0xFCDB14`
(диагностический блок измеряемых величин).

### Потребитель 0xF9CF7E — масштабирование под стрелку

```
F9CF80: A = температура
F9CF82: ADDW A, 0x0028    ; +40
F9CF85: LSLW A            ; x2
F9CF86: MOVW [0x02F4], A
```
`(°C + 40) x 2` — типичное преобразование в положение стрелки/шкалы
(-40°C -> 0, +100°C -> 280). То есть приборка **уже использует**
температуру ОЖ внутри себя.

### Заодно подтверждён канал 5 АЦП

Обработчик `0xFCDB14` — диспетчер измеряемых величин для диагностики:
`RW1 == 1` -> читает `[0x413A]` (температура ОЖ),
`RW1 == 2` -> вызывает `read_adc(5)`.
Это независимо подтверждает, что **канал 5 АЦП** — отдельная величина
(наружная температура), а ОЖ приходит по CAN, а не с АЦП.

### Что осталось не найдено

Сам код, который **пишет** `0x413A` из приёмного буфера CAN. Прямых записей
нет (единственная — обнуление по таймауту), значит запись идёт через
указатель, как и у остальных сигналов и как у применителя кодирования.
**Для практической цели это не важно**: значение лежит по фиксированному
адресу, обновляется само, формула известна и совпадает с DBC.

### ИТОГ: обе величины найдены

| Величина | Адрес | Формула | Источник |
|---|---|---|---|
| **Напряжение бортсети** | `0x0FA0` | уже в милливольтах | собственный АЦП, канал 1 |
| **Температура ОЖ** | `0x413A` | `значение - 48 = °C` | CAN `0x1D0` от DME |

Обе доступны из прошивки по фиксированным адресам. Вместе с ранее
разобранным конвейером вывода (`0xFDC80D` число-в-текст -> измерение ->
отрисовка) это полный набор для патча, выводящего любую из них на
цифровое поле.

## Concrete next tasks, in priority order

1. ~~Finish the addressing-mode decode for `0x70-0x7F`~~ — **done**.
   ~~`0x6C`~~ — **done**. `tools/F2MC-16LX/` has the full spec cloned locally.
2. ~~Build a recursive-descent disassembler~~ — **done**, `tools/f2mc_cfg.py`,
   validated at 94.7%/97.6% clean function recovery (see above).
3. ~~Dump and disassemble both firmwares~~ — **done** for `9213308A` (DKOML2)
   vs `9168320A` (HKOML2) over the code region `0xF9C000-0xFF0000`.
4. ~~Compare structurally~~ — **done**, `tools/f2mc_compare.py`. Results:

   ```
   DKOML2:  5269 raw -> 1562 call-confirmed functions
   HKOML2:  4425 raw -> 1547 call-confirmed functions

   exact mnemonic-signature match: 1101/1562 (70.5%) DK, 1078/1547 (69.7%) HK
   unmatched: 461 DK-only, 469 HK-only
     of the DK-only, 96 have a same-shape HK counterpart (same function,
        small edit -- the most interesting candidate class)
     and 365 have no shape counterpart at all
   ```

   Byte diffing gave ~80% difference and zero signal; structural comparison
   aligns 70% of the code and narrows the search from half a megabyte to
   ~460 functions, with the most likely class down to 96.

   Reproduce with:
   ```
   python3 tools/f2mc_cfg.py DKOML2/9213308A.0pa --range 0xF9C000,0xFF0000 --json dk.json
   python3 tools/f2mc_cfg.py HKOML2/9168320A.0pa --range 0xF9C000,0xFF0000 --json hk.json
   python3 tools/f2mc_compare.py dk.json hk.json
   ```

5. ~~Work through the 96 "same shape" functions~~ — **done, negative
   result**, see the section above. Not the answer.
6. ~~Search the data region, not just code~~ — **done, and this is what
   found the prime candidate**, see above.
7. **NEXT: trace `RAM[0x0CF6]` to the actual drawing.** This is the one
   missing link. It has exactly one reader, the getter at `0xFAFEFD`; find
   who calls that getter and what it does with the value, then follow it to
   the code that puts pixels/segments on the display.
8. ~~Work out what the index `RAM[0x0CFD]` means~~ - **done**, see above.
   It is `0x1D2` byte 1 bits 0-1, NOT `ShiftLeverMode`. What remains is to
   learn what the EGS/DKG actually puts there: log a real DKG car and watch
   whether that field changes with D/S/M mode.
8b. **Confirm the buffer at `0x4140` really carries `0x1D2`** by finding the
   CAN controller init code (message-ID registers in the I/O area). The
   field-layout match is strong (5 independent fields + DLC) but is still
   structural inference, not a read of the ID register.
9. **Generalize the table comparison.** The lookup-site scan
   (`ZEXTW; ADDL A,#imm32; MOVL RL2,A`) was written inline; it deserves its
   own script so ALL tables of both families can be paired, not just the
   gear group. The "every table should have a counterpart" trick may expose
   other feature differences, including ones useful for the owner's side
   goal (board voltage / coolant temp readouts).
10. **Cross-reference against what's already known from the diagnostic
    layer**: the hidden service menu items 09.00 (`UB`, board voltage) and
   07.00 (`KTMP-MOM`, coolant temp) are known to exist in both clusters
   (confirmed via the KOMB87.PRG EDIABAS job list from earlier analysis,
   and via the owner's own hidden-menu documentation). Any rendering
   routine that draws a bordered/boxed indicator for those or for the gear
   letter is a good anchor to search for by *shape* (e.g. a function that
   draws a rectangle outline + text, likely called from a small table of
   "which slots get a box" flags) rather than by trying to diff everything.
11. **Do not attempt to flash a patched image back via the official job
    sequence** without first resolving the `AUTHENTISIERUNG`/
   `FLASH_SIGNATUR_PRUEFEN` challenge-response + signature check (see fact
   #the .ipo files above) — that's a separate, harder problem from
   understanding the code, and getting it wrong risks bricking a real
   cluster. Treat this whole effort as read-only reverse engineering until
   that's separately solved.

## Useful external references gathered during the investigation

- Fujitsu F2MC-16LX Programming Manual (CM44-00201-3E):
  https://bitsavers.trailing-edge.com/components/fujitsu/f2mc-16/F2MC-16LX/CM44-00201-3E_F2MC-LX_Programming_Manual.pdf
- Ghidra F2MC-16LX processor module (source of truth for opcode table):
  https://github.com/mehmooda/F2MC-16LX
- MB90F395HA datasheet: alldatasheet.com / alldatasheet.net (search
  "MB90F395HA")
- Community BMW K-CAN reverse engineering, relevant precedent for the
  "redirect a display slot" trick this whole project is ultimately in
  service of:
  - https://github.com/veikkos/e90-can-cluster (documents coolant-temp as
    "debug menu only" and oil-temp as "high trim only" -- matches this
    project's context closely)
  - https://github.com/ilicmiljan/open-can-controller (redirects an
    existing gauge slot to show coolant temp via KWP2000/K-CAN, for a
    stand-alone cluster -- same trick, different implementation)
  - "Arduino-Tacho Gang" Discord community mentioned in veikkos's README --
    worth asking there if stuck, they may already know the box/no-box
    mechanism.

---

## 2026-10-08: графический движок — 4 бита/пиксель подтверждено, ширина строки — только верхняя граница

Копали вопрос "можно ли вычислить разрешение экрана из прошивки" (не
просто оценить на глаз LOW/HIGH). Нашли и прошли цепочку вызовов от рамки
передачи (`0xFDBE94`) вглубь до низкоуровневого блиттера `0xFED9D3`.

**Подтверждено дизассемблером:**
* Экран **4 бита на пиксель** (16 уровней яркости) — функция `0xFEE3F9`
  безусловно возвращает константу `4`, используется как bpp в блиттере.
  Объясняет "гладкие" на вид цифры на реальных фото щитка — это настоящее
  аппаратное сглаживание яркостью, не артефакт камеры.
* Ширина строки клиппится константой **80 байт/строку = 160 адресуемых
  4-битных пикселей** (`0x50 * (8/4bpp)`) перед вызовом блиттера.

**НЕ подтверждено:** 160 — это потолок адресации, не обязательно видимая
ширина экрана; высота тем же способом не нашлась; самый внешний
"весь экран" clip-rect задаётся безразмерным (`0..0xFFFF`) в найденном
коде инициализации — реальный размер экрана ставится позже, в коде
инициализации LCD-контроллера, который ещё не локализован.

Полный разбор с адресами: `docs/research/ANALYSIS_NOTES.md`, раздел
«2026-10-08: разведка графического движка».
