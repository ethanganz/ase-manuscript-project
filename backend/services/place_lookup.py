"""
What it does: takes a word, finds it in our dictionary, then finds the place in the official place list (name, country, position) 
and passes it to candidates.py.

Input : a word our model found, e.g. "Tigurum"
Output: candidate places in the same shape as our `place_candidates`, which
        `choose_candidate`.

The three pieces
----------------
1. place_variants.json  spelling -> place id(s), made by place_variants.py
2. localities.xml       place id -> name, country, coordinates (the official list)
3. PlaceLookup          joins them:  "Tigurum" -> l587 -> Zürich, Schweiz, 47.36667 8.55

Run on a file of mentions (prints one line per mention and a summary):
    python -m services.place_lookup resources/place_variants.json \
        resources/localities.xml  place_mentions.jsonl
        
Note for the team:
Later, inside the app (every time). 
When a user uploads a manuscript and our model finds place words, 
our backend calls this file automatically, once for each word. 
It is the next feature, together with saving into the database.
"""

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from services.candidates import Choice, choose_candidate
from services.place_variants import normalize_word

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# A place id is only used if at least this share of the taggings of a word
# points to it. Example: "x" tagged 19 times as l1 and once as l2 -> l2 is
# treated as an editor's slip (5 % < 20 %) and ignored. 10 against 8 -> both
# kept, and the word becomes "ambiguous". Change here if it is too strict/loose.
MIN_SHARE = 0.2


def _text_of(place: ET.Element, tag: str) -> str:
    return (place.findtext(f"{TEI}{tag}") or "").strip()


def _parse_geo(geo_text: str | None) -> tuple[float | None, float | None]:
    """ "47.36667 8.55" -> (47.36667, 8.55). Anything odd -> (None, None)."""
    parts = (geo_text or "").split()
    if len(parts) != 2:
        return None, None
    try:
        lat, lng = float(parts[0]), float(parts[1])
    except ValueError:
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):  # impossible on a globe
        return None, None
    return lat, lng


def load_localities(path: Path) -> dict[str, dict]:
    """The official place list as {"l587": {settlement, district, country, latitude, longitude}}."""
    result = {}
    for place in ET.parse(path).getroot().iter(f"{TEI}place"):
        place_id = place.get(XML_ID)
        if not place_id:
            continue
        geo = place.find(f".//{TEI}geo")
        lat, lng = _parse_geo(geo.text if geo is not None else None)
        result[place_id] = {
            "id": place_id,
            "settlement": _text_of(place, "settlement"),
            "district": _text_of(place, "district"),
            "country": _text_of(place, "country"),
            "latitude": lat,
            "longitude": lng,
        }
    return result


def locality_to_candidate(entry: dict) -> dict | None:
    """One place-list entry -> a candidate shaped like the ones in her file."""
    # Some entries are whole countries or regions (e.g. l832 = France) and have
    # no settlement name. We then use the country as the name and say so in
    # place_level, so a later step can avoid drawing a pin in the middle of France.
    name = entry["settlement"] or entry["country"]
    if not name:
        return None
    return {
        "id": f"bullinger:{entry['id']}",
        "canonical_name": name,
        "latitude": entry["latitude"],
        "longitude": entry["longitude"],
        "official_place_id": entry["id"],
        "official_name_fields": {
            "settlement": entry["settlement"],
            "district": entry["district"],
            "region": "",
            "country": entry["country"],
        },
        "place_level": "settlement" if entry["settlement"] else "country",
    }


class PlaceLookup:
    def __init__(self, variants: dict, localities: dict):
        self._variants = variants  # normalized word -> {"ids": {id: count}, "forms": [...]}
        self._localities = localities

    @classmethod
    def from_files(cls, variants_path: Path, localities_path: Path) -> "PlaceLookup":
        data = json.loads(Path(variants_path).read_text(encoding="utf-8"))
        return cls(data["variants"], load_localities(Path(localities_path)))

    def place_ids_for(self, word: str) -> list[tuple[str, int, float]]:
        """[(place id, times tagged, share of all taggings)], most frequent first."""
        entry = self._variants.get(normalize_word(word))
        if not entry:
            return []
        total = sum(entry["ids"].values())
        found = [(pid, n, n / total) for pid, n in entry["ids"].items()]
        return [(pid, n, share) for pid, n, share in found if share >= MIN_SHARE]

    def candidates_for(self, word: str) -> list[dict]:
        candidates = []
        for place_id, times, share in self.place_ids_for(word):
            entry = self._localities.get(place_id)
            candidate = locality_to_candidate(entry) if entry else None
            if candidate is None:
                continue  # id not in our copy of the place list
            # Evidence stays attached, so a later step can turn it into a confidence.
            candidate["variant_evidence"] = {
                "times_tagged": times,
                "share": round(share, 2),
            }
            candidates.append(candidate)
        return candidates


def resolve_mention(mention: dict, lookup: PlaceLookup) -> Choice:
    """Her candidates (if any) + ours, then step 4 decides.
    Duplicates between the two lists are merged by choose_candidate."""
    candidates = list(mention.get("place_candidates") or [])
    candidates += lookup.candidates_for(mention.get("observed_text", ""))
    return choose_candidate(candidates)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage: python -m services.place_lookup <place_variants.json> "
            "<localities.xml> <place_mentions.jsonl>"
        )
        return 2
    lookup = PlaceLookup.from_files(Path(argv[1]), Path(argv[2]))
    counts: Counter = Counter()
    for line in Path(argv[3]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        mention = json.loads(line)
        choice = resolve_mention(mention, lookup)
        counts[choice.status] += 1
        print(
            f"{mention['observed_text']:<24} {choice.status:<14} "
            f"{choice.name or '-':<14} {choice.country_code or '-'}"
        )
    print()
    print(dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


# TEST
# python -m services.place_lookup \
#   resources/place_variants.json \
#   resources/localities.xml \
#   path/to/json/place_mentions.jsonl
