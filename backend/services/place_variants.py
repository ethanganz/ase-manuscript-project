"""
What it does: builds a dictionary of old spellings.
For example “Tigurum” means place number l587, which is Zürich.

Why it exists: the place list only knows modern names like “Zürich”.
The editors of the letters already marked old spellings inside the letters, and this file collects all of them.
How you use it: we run it once on our computer, and it saves a data file.

The problem
-----------
Our model finds the word "Tigurum". The place list only knows "Zürich".
Nothing connects the two, so we need a dictionary of old spellings.

Where the dictionary comes from
-------------------------------
The editors of the Bullinger letters already tagged place words in every
letter, and gave each one the id of the place in the official place list:

    <placeName ref="l587">Tigurum</placeName>      l587 = Zürich

If we collect all such pairs from all letters, we get a dictionary:

    "tigurum"  -> {"l587": 5}        (tagged 5 times, always as l587)
    "tigurini" -> {"l587": 2}

We keep a COUNT per place id, because the editors make mistakes (a Latin verb
tagged as a city once). A word that is almost always tagged as one place is
trustworthy; the counts let the next step see that.

We only read the <text> of each letter (the original text and its notes),
NOT the German summary at the top, because the summary uses modern German
spellings that are not what the manuscripts contain.

1. place_variants.json (the dictionary) gives only a place number.
For example, “Tigurum” gives l587. It has no country, no coordinates, and not even the name “Zürich”.
It only says which place the editors meant.

2. localities.xml (the place list) gives the details for that number.
For l587 it gives the name (Zürich), the coordinates, and the country as a word, which is “Schweiz” if the editors filled it in.

git clone https://github.com/stazh/bullinger-korpus-tei

3. country_codes.py changes that word into a code. “Schweiz” becomes “CH”. This is the only mapping that happens in our backend.

How to run
---------------------------------


    cd backend
    python -m services.place_variants  <folder with the letters>  resources/place_variants.json
    from Dunya: I already did this, if there is any new update you can do it again.
"""

import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

TEI = "{http://www.tei-c.org/ns/1.0}"

# http://www.tei-c.org/ns/1.0 is the XML namespace identifier for TEI (Text Encoding Initiative).
# It identifies a set of rules used to structure and describe digital texts, especially historical documents, literature, manuscripts, and scholarly publications.
# - tei-c.org — The official website of the Text Encoding Initiative.
# - /ns/1.0 — Indicates the namespace identifier.
# - XML namespace — A way to identify which vocabulary XML elements belong to, helping software distinguish elements with the same name but different meanings.

PLACE_ID = re.compile(r"^l\d+$")  # ids of the place list look like "l587"
# It is used to remove punctuation or whitespace from the beginning and end of a piece of text.
_EDGE_PUNCTUATION = " \t\r\n.,;:!?()[]{}«»\"'“”‘’"


def normalize_word(word: str | None) -> str:
    """Makes spellings comparable. Used for BOTH the dictionary and the lookup.

      "Basileę" and "Basileae"        -> "basileae"   (ę is how handwriting writes "ae")
      "Zürich" and "ZURICH"           -> "zurich"     (capitals and accents ignored)
      "Vindelicorum" / "Uindelicorum" -> "uindelicorum"  (u/v and i/j were one letter)
      "Baſel"                         -> "basel"      (old long s)

    It only makes spellings comparable. It does NOT remove Latin endings:
    "Constantiam" and "Constantiensis" stay different (a later step).
    """
    text = (word or "").casefold()
    text = text.replace("ę", "ae").replace("æ", "ae").replace("œ", "oe")
    text = unicodedata.normalize("NFKD", text)  # split letters from accents
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("j", "i").replace("v", "u")
    return " ".join(text.split())


def extract_pairs(xml_path: Path) -> list[tuple[str, str]] | None:
    """All (word as written, place id) pairs of ONE letter.

    Returns None if the file is not a letter (it has no <text> part),
    for example the place list itself.
    Raises xml.etree.ElementTree.ParseError if the file is broken.
    """
    root = ET.parse(xml_path).getroot()
    text = root.find(f"{TEI}text")
    if text is None:
        return None

    pairs = []
    for element in text.iter(f"{TEI}placeName"):
        refs = (element.get("ref") or "").split()
        # Exactly one id of the form l123. Person ids (p495), missing refs and
        # tags with several ids are skipped: we cannot tell which one is meant.
        if len(refs) != 1 or not PLACE_ID.match(refs[0]):
            continue
        # itertext() also reads words split by inner tags: "Augu<hi>sta</hi>m"
        written = " ".join("".join(element.itertext()).split()).strip(_EDGE_PUNCTUATION)
        if written:
            pairs.append((written, refs[0]))
    return pairs


def build_variants(corpus_dir: Path) -> dict:
    """Reads every .xml file below corpus_dir and builds the dictionary."""
    ids: dict[str, Counter] = defaultdict(Counter)  # normalized word -> {place id: times}
    written_forms: dict[str, Counter] = defaultdict(Counter)  # ... -> {spelling as written: times}
    stats: Counter = Counter()

    for path in sorted(Path(corpus_dir).rglob("*.xml")):
        if ".git" in path.parts:
            continue
        stats["xml_files"] += 1
        try:
            pairs = extract_pairs(path)
        except ET.ParseError:
            stats["unreadable_files"] += 1
            continue
        if pairs is None:
            stats["files_without_text"] += 1
            continue
        stats["letters"] += 1
        for written, place_id in pairs:
            key = normalize_word(written)
            if not key:
                continue
            ids[key][place_id] += 1
            written_forms[key][written] += 1
            stats["tagged_words"] += 1

    variants = {
        key: {
            "ids": dict(counter.most_common()),  # most frequent first
            "forms": [
                f for f, _ in written_forms[key].most_common(5)
            ],  # for humans reading the file
        }
        for key, counter in sorted(ids.items())
    }
    return {"meta": {**stats, "distinct_forms": len(variants)}, "variants": variants}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python -m services.place_variants <folder with letters> <output.json>")
        return 2
    corpus_dir, output = Path(argv[1]), Path(argv[2])
    if not corpus_dir.is_dir():
        print(f"Not a folder: {corpus_dir}")
        return 2

    result = build_variants(corpus_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    meta = result["meta"]
    print(f"Letters read:        {meta.get('letters', 0)}")
    print(f"Tagged place words:  {meta.get('tagged_words', 0)}")
    print(f"Distinct spellings:  {meta['distinct_forms']}")
    print(f"Other XML files:     {meta.get('files_without_text', 0)} (no <text>, skipped)")
    print(f"Broken XML files:    {meta.get('unreadable_files', 0)}")
    print(f"Saved to:            {output}")
    if meta.get("letters", 0) == 0:
        print("WARNING: no letters found. Is this the right folder?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
