"""parse_ihex не проверяет чексуммы записей (см. сам модуль) — поэтому в
тестовых файлах контрольный байт произвольный, важны только length/addr/type/payload.
"""
from parse_ihex import get_segments, parse_ihex


def write_hex(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_parse_single_data_record(tmp_path):
    f = tmp_path / "simple.0pa"
    write_hex(f, [":02000000AABB00"])  # len=2 addr=0x0000 type=00 data=AA BB

    mem, lo, hi = parse_ihex(f)

    assert mem == {0: 0xAA, 1: 0xBB}
    assert lo == 0
    assert hi == 2


def test_extended_linear_address(tmp_path):
    f = tmp_path / "ext.0pa"
    write_hex(
        f,
        [
            ":0200000400F8FE",  # ext linear addr: upper 16 bits = 0x00F8 -> bank 0xF80000
            ":0200000011220C",  # data at offset 0x0000 within that bank
        ],
    )

    mem, lo, hi = parse_ihex(f)

    assert mem == {0xF80000: 0x11, 0xF80001: 0x22}
    assert lo == 0xF80000
    assert hi == 0xF80002


def test_eof_record_stops_parsing(tmp_path):
    f = tmp_path / "eof.0pa"
    write_hex(
        f,
        [
            ":02000000AABB00",
            ":00000001FF",  # EOF
            ":0200100011220C",  # должна быть проигнорирована
        ],
    )

    mem, _lo, _hi = parse_ihex(f)

    assert mem == {0: 0xAA, 1: 0xBB}


def test_non_record_lines_are_skipped(tmp_path):
    f = tmp_path / "comment.0pa"
    write_hex(
        f,
        [
            ";$VALUE_UNUSED_BYTE 0xFF",
            ":02000000AABB00",
        ],
    )

    mem, _lo, _hi = parse_ihex(f)

    assert mem == {0: 0xAA, 1: 0xBB}


def test_get_segments_merges_contiguous_bytes():
    mem = {0: 1, 1: 2, 2: 3, 10: 9, 11: 9}

    segs = get_segments(mem)

    assert segs == [(0, 2), (10, 11)]


def test_get_segments_empty():
    assert get_segments({}) == []
