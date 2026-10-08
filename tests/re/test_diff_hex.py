from diff_hex import diff, parse_addr


def test_diff_finds_single_contiguous_run(tmp_path):
    a = tmp_path / "a.0pa"
    b = tmp_path / "b.0pa"
    a.write_text(":04000000AABBCCDD00\n", encoding="ascii")  # 0xAA 0xBB 0xCC 0xDD
    b.write_text(":04000000AABBCEDD00\n", encoding="ascii")  # byte at +2 differs (CC->CE)

    runs = diff(a, b, verbose=False)

    assert runs == [(2, 2, [(0xCC, 0xCE)])]


def test_diff_identical_files_has_no_runs(tmp_path):
    a = tmp_path / "a.0pa"
    b = tmp_path / "b.0pa"
    content = ":02000000AABB00\n"
    a.write_text(content, encoding="ascii")
    b.write_text(content, encoding="ascii")

    assert diff(a, b, verbose=False) == []


def test_parse_addr_hex_and_decimal():
    assert parse_addr("0x10") == 16
    assert parse_addr("16") == 16
