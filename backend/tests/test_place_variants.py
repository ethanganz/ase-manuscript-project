import json

from services.place_variants import build_variants, extract_pairs, main, normalize_word


def letter(body, summary=""):
    """A tiny letter shaped like the real ones: a German summary in the header
    and the original text in <text>."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="file1">
  <teiHeader><fileDesc><sourceDesc><msDesc><msContents><summary>
    <p>{summary}</p>
  </summary></msContents></msDesc></sourceDesc></fileDesc></teiHeader>
  <text xml:lang="la"><body><div><p>{body}</p></div></body></text>
</TEI>"""


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ------------------------------------------------------------- normalize_word
def test_ae_written_as_e_ogonek_matches_ae():
    assert normalize_word("Basileę") == normalize_word("Basileae") == "basileae"


def test_capitals_and_accents_are_ignored():
    assert normalize_word("Zürich") == normalize_word("ZURICH") == normalize_word("zurich") == "zurich"


def test_u_v_and_i_j_are_the_same_letter():
    assert normalize_word("Vindelicorum") == normalize_word("Uindelicorum")
    assert normalize_word("Iohannes") == normalize_word("Johannes")


def test_long_s_and_double_spaces():
    assert normalize_word("Baſel") == "basel"
    assert normalize_word("  Augustae   Vindelicorum ") == "augustae uindelicorum"


def test_empty_values():
    assert normalize_word("") == "" and normalize_word(None) == ""


def test_endings_are_NOT_removed_yet():
    # This is a later step. The test documents the current limit on purpose.
    assert normalize_word("Constantiam") != normalize_word("Constantiensis")


# --------------------------------------------------------------- extract_pairs
def test_reads_text_but_not_the_german_summary(tmp_path):
    f = write(tmp_path / "a.xml", letter(
        body='Veni <placeName ref="l587">Tigurum</placeName> et <placeName ref="l257">Constantiam</placeName>.',
        summary='<placeName ref="l18">Augsburg</placeName>'))
    assert extract_pairs(f) == [("Tigurum", "l587"), ("Constantiam", "l257")]


def test_skips_tags_we_cannot_use(tmp_path):
    f = write(tmp_path / "a.xml", letter(body=(
        '<placeName>no ref</placeName>'
        '<placeName ref="p495">person id</placeName>'
        '<placeName ref="l1 l2">two ids</placeName>'
        '<placeName ref="l3">   </placeName>'
        '<placeName ref="l5">Basel</placeName>')))
    assert extract_pairs(f) == [("Basel", "l5")]


def test_word_split_by_inner_tags_is_joined(tmp_path):
    f = write(tmp_path / "a.xml", letter(body='<placeName ref="l18">Augu<hi>sta</hi>m</placeName>'))
    assert extract_pairs(f) == [("Augustam", "l18")]


def test_trailing_punctuation_is_removed(tmp_path):
    f = write(tmp_path / "a.xml", letter(body='<placeName ref="l18">Augsburg,</placeName>'))
    assert extract_pairs(f) == [("Augsburg", "l18")]


def test_file_without_text_is_not_a_letter(tmp_path):
    f = write(tmp_path / "localities.xml",
              '<TEI xmlns="http://www.tei-c.org/ns/1.0"><standOff/></TEI>')
    assert extract_pairs(f) is None


# ----------------------------------------------------------------- build_variants
def test_counts_and_merges_over_many_files(tmp_path):
    write(tmp_path / "1" / "a.xml", letter('<placeName ref="l587">Tigurum</placeName> '
                                           '<placeName ref="l587">Tigurum</placeName>'))
    write(tmp_path / "2" / "deep" / "b.xml", letter('<placeName ref="l587">Tigurum</placeName> '
                                                    '<placeName ref="l257">Constantiam</placeName>'))
    write(tmp_path / "notes.txt", "not xml at all")
    result = build_variants(tmp_path)

    assert result["variants"]["tigurum"]["ids"] == {"l587": 3}
    assert result["variants"]["constantiam"]["ids"] == {"l257": 1}
    assert result["meta"]["letters"] == 2 and result["meta"]["tagged_words"] == 4
    assert result["meta"]["distinct_forms"] == 2


def test_different_spellings_share_one_entry_and_keep_both_forms(tmp_path):
    write(tmp_path / "a.xml", letter('<placeName ref="l28">Basileę</placeName> '
                                     '<placeName ref="l28">Basileae</placeName>'))
    entry = build_variants(tmp_path)["variants"]["basileae"]
    assert entry["ids"] == {"l28": 2}
    assert set(entry["forms"]) == {"Basileę", "Basileae"}


def test_editor_slip_is_counted_separately_not_hidden(tmp_path):
    for i in range(3):
        write(tmp_path / f"{i}.xml", letter('<placeName ref="l18">Augusta</placeName>'))
    write(tmp_path / "slip.xml", letter('<placeName ref="l99">Augusta</placeName>'))
    assert build_variants(tmp_path)["variants"]["augusta"]["ids"] == {"l18": 3, "l99": 1}


def test_broken_xml_does_not_stop_the_run(tmp_path):
    write(tmp_path / "broken.xml", "<TEI><unclosed>")
    write(tmp_path / "ok.xml", letter('<placeName ref="l1">Basel</placeName>'))
    result = build_variants(tmp_path)
    assert result["meta"]["unreadable_files"] == 1 and result["meta"]["letters"] == 1


def test_the_git_folder_is_ignored(tmp_path):
    write(tmp_path / ".git" / "x.xml", letter('<placeName ref="l1">Basel</placeName>'))
    assert build_variants(tmp_path)["meta"].get("xml_files", 0) == 0


def test_command_line_writes_the_json_file(tmp_path, capsys):
    write(tmp_path / "in" / "a.xml", letter('<placeName ref="l587">Tigurum</placeName>'))
    out = tmp_path / "out" / "variants.json"
    assert main(["prog", str(tmp_path / "in"), str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["variants"]["tigurum"]["ids"] == {"l587": 1}
    assert "Letters read:        1" in capsys.readouterr().out


def test_command_line_rejects_a_missing_folder(tmp_path, capsys):
    assert main(["prog", str(tmp_path / "nope"), str(tmp_path / "o.json")]) == 2
    assert main(["prog"]) == 2