from f2mc_disasm import disasm_one, pcrel


def test_nop():
    length, text = disasm_one(bytes([0x00]), 0)
    assert (length, text) == (1, "NOP")


def test_unlink():
    length, text = disasm_one(bytes([0x09]), 0)
    assert (length, text) == (1, "UNLINK")


def test_imm8_operand():
    # 0x08 = LINK imm8
    length, text = disasm_one(bytes([0x08, 0x10]), 0)
    assert length == 2
    assert text.startswith("LINK ")


def test_truncated_instruction_at_buffer_end():
    # LINK needs one more byte that isn't there -- must not raise.
    length, text = disasm_one(bytes([0x08]), 0)
    assert "??" in text


def test_pc_relative_branch():
    # 0x60 = BRA rel8. addr=0xF80100, rel byte=5 -> target = addr + 2 + 5.
    data = bytes([0x60, 0x05])
    length, text = disasm_one(data, 0, addr=0xF80100)
    assert length == 2
    assert text == "BRA 0xF80107"


def test_pcrel_wraps_within_bank_not_across_it():
    # Displacement that would overflow 16 bits must wrap inside the bank,
    # never carry into the next bank -- that's the whole point of pcrel().
    assert pcrel(0xF8FFFE, 4) == 0xF80002


def test_disasm_one_past_end_of_buffer_is_safe():
    length, text = disasm_one(b"", 0)
    assert (length, text) == (1, "??")
