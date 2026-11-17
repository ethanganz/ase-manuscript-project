"""Tests for importing transcript lines. No database or network is used."""

import json
import unicodedata

import pytest

from database.repository import InMemoryRepository
from services.transcript_import import import_transcript, main, parse_transcript


def _line(**fields) -> str:
    return json.dumps(fields, ensure_ascii=False)


GOOD = _line(
    document_id="485",
    page_id="485_01",
    line_id="485_01_r1l5",
    language="de",
    text="geben uff den sommet.",
    image_path="/some/local/path.png",
)


def test_valid_line_becomes_a_row_without_the_local_image_path():
    report = parse_transcript([GOOD])
    assert report.skipped == []
    assert report.rows == [
        {
            "source_line_id": "485_01_r1l5",
            "text": "geben uff den sommet.",
            "source_document_id": "485",
            "source_page_id": "485_01",
            "language": "de",
        }
    ]


def test_only_line_id_and_text_are_required():
    report = parse_transcript([_line(line_id="a", text="Rex")])
    assert report.rows == [{"source_line_id": "a", "text": "Rex"}]


def test_bad_lines_are_skipped_with_a_reason_and_do_not_stop_the_import():
    report = parse_transcript(
        [
            "{not json",
            "[1, 2]",
            _line(text="no id"),
            _line(line_id="x", text="   "),
            "",
            _line(line_id="ok", text="fine"),
        ]
    )
    assert [r["source_line_id"] for r in report.rows] == ["ok"]
    assert report.skipped == [
        (1, "not valid JSON"),
        (2, "not a JSON object"),
        (3, "missing line_id"),
        (4, "empty text"),
    ]


def test_duplicate_line_id_in_one_file_keeps_the_later_line():
    report = parse_transcript([_line(line_id="a", text="old"), _line(line_id="a", text="new")])
    assert [r["text"] for r in report.rows] == ["new"]
    assert len(report.skipped) == 1 and "duplicate" in report.skipped[0][1]


def test_text_is_stored_in_nfc_form():
    decomposed = unicodedata.normalize("NFD", "Zürich")
    assert decomposed != "Zürich"
    report = parse_transcript([_line(line_id="a", text=decomposed)])
    assert report.rows[0]["text"] == "Zürich"


def test_numeric_ids_are_stored_as_text():
    report = parse_transcript([_line(line_id=7, text="x", document_id=485)])
    assert report.rows[0]["source_line_id"] == "7"
    assert report.rows[0]["source_document_id"] == "485"


def test_import_twice_does_not_duplicate_and_keeps_a_page_link():
    repo = InMemoryRepository()
    import_transcript(repo, [GOOD])
    repo.text_lines["485_01_r1l5"]["page_id"] = "page-uuid"  # linked to a page later
    import_transcript(repo, [_line(line_id="485_01_r1l5", text="geben uff den sommer.")])
    assert len(repo.text_lines) == 1
    row = repo.text_lines["485_01_r1l5"]
    assert row["text"] == "geben uff den sommer." and row["page_id"] == "page-uuid"


def test_dry_run_writes_nothing():
    repo = InMemoryRepository()
    report = import_transcript(repo, [GOOD], dry_run=True)
    assert report.imported == 1 and repo.text_lines == {}


def test_real_import_without_a_repository_is_rejected():
    with pytest.raises(ValueError):
        import_transcript(None, [GOOD])


def test_cli_dry_run_on_a_file(tmp_path, capsys):
    path = tmp_path / "t.jsonl"
    path.write_text(GOOD + "\n{broken\n", encoding="utf-8")
    assert main([str(path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "would import 1 lines, skipped 1" in out and "line 2: not valid JSON" in out


def test_cli_returns_error_code_when_nothing_is_usable(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text("{broken\n", encoding="utf-8")
    assert main([str(path), "--dry-run"]) == 1


# pytest tests/test_transcript_import.py -v
