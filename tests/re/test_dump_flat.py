from dump_flat import dump_flat, parse_addr


def test_dump_flat_fills_gaps_with_ff(tmp_path):
    src = tmp_path / "in.0pa"
    src.write_text(":02000000AABB00\n:0200100011220C\n", encoding="ascii")
    out = tmp_path / "out.bin"

    lo, hi = dump_flat(src, out)

    assert (lo, hi) == (0, 0x12)
    data = out.read_bytes()
    assert data[0:2] == b"\xAA\xBB"
    assert data[0x10:0x12] == b"\x11\x22"
    # промежуток между записями заполнен 0xFF (конвенция "стёртого" флеша)
    assert data[2] == 0xFF
    assert data[0x0F] == 0xFF


def test_dump_flat_respects_explicit_range(tmp_path):
    src = tmp_path / "in.0pa"
    src.write_text(":02000000AABB00\n", encoding="ascii")
    out = tmp_path / "out.bin"

    lo, hi = dump_flat(src, out, lo=0, hi=4, fill=0x00)

    assert (lo, hi) == (0, 4)
    assert out.read_bytes() == b"\xAA\xBB\x00\x00"


def test_parse_addr_hex_and_decimal():
    assert parse_addr("0xFF") == 255
    assert parse_addr("0XAB") == 0xAB
    assert parse_addr("10") == 10
