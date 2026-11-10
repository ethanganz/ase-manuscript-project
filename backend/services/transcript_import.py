"""Import transcribed text lines (JSON Lines format) into the ``text_lines`` table.

Input: one JSON object per line, for example::

    {"document_id": "485", "page_id": "485_01", "line_id": "485_01_r1l5",
     "language": "de", "text": "geben uff den sommet."}

Only ``line_id`` and ``text`` are required. ``line_id`` is the natural key, so
running the import twice updates existing lines instead of duplicating them.
A bad line never stops the import; it is skipped and reported.

Command line (run from the ``backend`` folder)::

    python -m services.transcript_import path/to/file.jsonl --dry-run
    python -m services.transcript_import path/to/file.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from database.repository import Repository

_OPTIONAL_FIELDS = {
    "document_id": "source_document_id",
    "page_id": "source_page_id",
    "language": "language",
}


@dataclass
class ImportReport:
    """What happened during an import."""

    rows: list[dict] = field(default_factory=list)       # valid, de-duplicated rows
    skipped: list[tuple[int, str]] = field(default_factory=list)  # (line number, reason)

    @property
    def imported(self) -> int:
        return len(self.rows)


def _clean(value: object) -> str | None:
    """Return a stripped string, or None when the value is missing or blank."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_transcript(lines: Iterable[str]) -> ImportReport:
    """Turn raw JSON Lines text into table rows. Never raises on bad input."""
    report = ImportReport()
    by_line_id: dict[str, dict] = {}

    for number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue  # blank lines are harmless

        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            report.skipped.append((number, "not valid JSON"))
            continue
        if not isinstance(record, dict):
            report.skipped.append((number, "not a JSON object"))
            continue

        line_id = _clean(record.get("line_id"))
        if line_id is None:
            report.skipped.append((number, "missing line_id"))
            continue

        # NFC keeps letters such as "ę" or "ü" in one canonical form, so the
        # same word is always stored (and searched) the same way.
        text = _clean(record.get("text"))
        if text is None:
            report.skipped.append((number, "empty text"))
            continue

        row = {"source_line_id": line_id, "text": unicodedata.normalize("NFC", text)}
        for source_key, column in _OPTIONAL_FIELDS.items():
            value = _clean(record.get(source_key))
            if value is not None:
                row[column] = value

        if line_id in by_line_id:
            report.skipped.append((number, f"duplicate line_id {line_id}; later line wins"))
        by_line_id[line_id] = row

    report.rows = list(by_line_id.values())
    return report


def import_transcript(repo: Repository | None, lines: Iterable[str],
                      dry_run: bool = False) -> ImportReport:
    """Parse ``lines`` and store the valid rows.

    With ``dry_run`` nothing is written and ``repo`` may be None.
    """
    report = parse_transcript(lines)
    if report.rows and not dry_run:
        if repo is None:
            raise ValueError("a repository is required unless dry_run is set")
        repo.upsert_text_lines(report.rows)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import transcript lines into text_lines.")
    parser.add_argument("path", help="JSON Lines file")
    parser.add_argument("--dry-run", action="store_true",
                        help="check the file and print the result without writing")
    args = parser.parse_args(argv)

    repo = None
    if not args.dry_run:
        from deps import get_repo  # imported here so a dry run needs no credentials

        repo = get_repo()

    with open(args.path, encoding="utf-8") as handle:
        report = import_transcript(repo, handle, dry_run=args.dry_run)

    verb = "would import" if args.dry_run else "imported"
    print(f"{verb} {report.imported} lines, skipped {len(report.skipped)}")
    for number, reason in report.skipped[:20]:
        print(f"  line {number}: {reason}")
    if len(report.skipped) > 20:
        print(f"  ... and {len(report.skipped) - 20} more")
    return 0 if report.imported else 1


if __name__ == "__main__":
    sys.exit(main())