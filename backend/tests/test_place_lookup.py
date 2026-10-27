import json

from services.candidates import choose_candidate
from services.place_lookup import (PlaceLookup, load_localities, locality_to_candidate,
                                   main, resolve_mention)

# A tiny version of the official place list (same shape as the real localities.xml).
LOCALITIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><standOff><listPlace type="localities">
  <place xml:id="l587"><settlement>Zürich</settlement><district>Zürich</district><country>Schweiz</country>
    <location><geo>47.36667 8.55</geo></location></place>
  <place xml:id="l28"><settlement>Basel</settlement><district>Basel-Stadt</district><country>Schweiz</country>
    <location><geo>47.55839 7.57327</geo></location></place>
  <place xml:id="l832"><country>Frankreich</country><location><geo>46 2</geo></location></place>
  <place xml:id="l124"><settlement>Dublin</settlement></place>
  <place xml:id="l900"><settlement>Frankfurt</settlement><district>Hessen</district><country>Deutschland</country>
    <location><geo>50.11 8.68</geo></location></place>
  <place xml:id="l901"><settlement>Frankfurt</settlement><district>Brandenburg</district><country>Deutschland</country>
    <location><geo>52.34 14.55</geo></location></place>
  <place xml:id="l999"><settlement>Nowhere</settlement><country>Schweiz</country>
    <location><geo>999 8</geo></location></place>
  <place xml:id="l998"><location><geo>1 1</geo></location></place>
</listPlace></standOff></TEI>"""


def variants(**ids):
    """variants(tigurum={"l587": 5}) -> the dictionary shape place_variants.py writes."""
    return {word: {"ids": counts, "forms": [word]} for word, counts in ids.items()}


def make_lookup(tmp_path, **ids):
    path = tmp_path / "localities.xml"
    path.write_text(LOCALITIES_XML, encoding="utf-8")
    return PlaceLookup(variants(**ids), load_localities(path))


# ------------------------------------------------------------- the place list
def test_place_list_is_read(tmp_path):
    path = tmp_path / "l.xml"
    path.write_text(LOCALITIES_XML, encoding="utf-8")
    places = load_localities(path)
    assert places["l587"] == {"id": "l587", "settlement": "Zürich", "district": "Zürich",
                              "country": "Schweiz", "latitude": 47.36667, "longitude": 8.55}
    assert places["l832"]["latitude"] == 46.0 and places["l832"]["longitude"] == 2.0   # "46 2"


def test_missing_or_impossible_coordinates_become_none(tmp_path):
    path = tmp_path / "l.xml"
    path.write_text(LOCALITIES_XML, encoding="utf-8")
    places = load_localities(path)
    assert places["l124"]["latitude"] is None            # no <geo>
    assert places["l999"]["latitude"] is None            # latitude 999 is impossible


def test_entry_without_any_name_gives_no_candidate(tmp_path):
    path = tmp_path / "l.xml"
    path.write_text(LOCALITIES_XML, encoding="utf-8")
    assert locality_to_candidate(load_localities(path)["l998"]) is None


# ------------------------------------------------------------------- the lookup
def test_tigurum_becomes_zurich_in_switzerland(tmp_path):
    lookup = make_lookup(tmp_path, tigurum={"l587": 5})
    choice = choose_candidate(lookup.candidates_for("Tigurum"))
    assert (choice.status, choice.name, choice.country_code) == ("resolved", "Zürich", "CH")
    assert choice.official_place_id == "l587"


def test_spelling_differences_do_not_matter(tmp_path):
    lookup = make_lookup(tmp_path, basileae={"l28": 2})
    assert choose_candidate(lookup.candidates_for("Basileę")).name == "Basel"
    assert choose_candidate(lookup.candidates_for("BASILEAE")).name == "Basel"


def test_unknown_word_has_no_candidates(tmp_path):
    lookup = make_lookup(tmp_path, tigurum={"l587": 5})
    assert lookup.candidates_for("Edingburgum") == []
    assert choose_candidate(lookup.candidates_for("")).status == "no_candidates"


def test_one_editor_slip_is_ignored(tmp_path):
    lookup = make_lookup(tmp_path, x={"l587": 19, "l28": 1})        # 5 % points to Basel
    assert [c["official_place_id"] for c in lookup.candidates_for("x")] == ["l587"]


def test_a_real_split_makes_the_word_ambiguous(tmp_path):
    lookup = make_lookup(tmp_path, franckfurt={"l900": 10, "l901": 8})
    choice = choose_candidate(lookup.candidates_for("Franckfurt"))
    assert choice.status == "ambiguous" and len(choice.alternatives) == 2


def test_id_missing_from_our_place_list_is_skipped(tmp_path):
    lookup = make_lookup(tmp_path, y={"l77777": 3})
    assert lookup.candidates_for("y") == []


def test_evidence_is_attached_for_a_later_confidence_step(tmp_path):
    lookup = make_lookup(tmp_path, tigurum={"l587": 5})
    assert lookup.candidates_for("Tigurum")[0]["variant_evidence"] == {"times_tagged": 5, "share": 1.0}


def test_a_country_entry_resolves_to_the_country_and_is_marked(tmp_path):
    lookup = make_lookup(tmp_path, gallis={"l832": 4})               # like "Gallis" -> France
    candidate = lookup.candidates_for("Gallis")[0]
    assert candidate["place_level"] == "country" and candidate["canonical_name"] == "Frankreich"
    assert choose_candidate([candidate]).country_code == "FR"


def test_a_place_without_coordinates_cannot_be_resolved_yet(tmp_path):
    lookup = make_lookup(tmp_path, dublinum={"l124": 2})
    assert choose_candidate(lookup.candidates_for("Dublinum")).status == "no_candidates"


# ---------------------------------------------------------------- resolve_mention
HER_TIGURUM = [
    {"id": "zurich", "canonical_name": "Zürich", "latitude": 47.3769, "longitude": 8.5417,
     "official_name_fields": {}},
    {"id": "bullinger:l587", "canonical_name": "Zürich", "latitude": 47.36667, "longitude": 8.55,
     "official_place_id": "l587",
     "official_name_fields": {"settlement": "Zürich", "country": "Schweiz"}},
]


def test_her_candidates_and_ours_are_merged_not_doubled(tmp_path):
    lookup = make_lookup(tmp_path, tigurum={"l587": 5})
    choice = resolve_mention({"observed_text": "Tigurum", "place_candidates": HER_TIGURUM}, lookup)
    assert (choice.status, choice.country_code) == ("resolved", "CH")


def test_her_candidates_alone_still_work(tmp_path):
    lookup = make_lookup(tmp_path)
    choice = resolve_mention({"observed_text": "Tigurum", "place_candidates": HER_TIGURUM}, lookup)
    assert choice.status == "resolved"


def test_our_lookup_helps_when_she_has_no_candidates(tmp_path):
    lookup = make_lookup(tmp_path, tigurum={"l587": 5})
    choice = resolve_mention({"observed_text": "Tigurum", "place_candidates": []}, lookup)
    assert (choice.status, choice.name) == ("resolved", "Zürich")


def test_mention_without_anything_is_no_candidates(tmp_path):
    lookup = make_lookup(tmp_path)
    assert resolve_mention({"observed_text": "domino"}, lookup).status == "no_candidates"


# --------------------------------------------------------------------- the files
def test_from_files_and_command_line(tmp_path, capsys):
    (tmp_path / "localities.xml").write_text(LOCALITIES_XML, encoding="utf-8")
    (tmp_path / "variants.json").write_text(
        json.dumps({"meta": {}, "variants": variants(tigurum={"l587": 5})}), encoding="utf-8")
    mentions = tmp_path / "m.jsonl"
    mentions.write_text(
        json.dumps({"observed_text": "Tigurum", "place_candidates": []}) + "\n"
        + json.dumps({"observed_text": "domino", "place_candidates": []}) + "\n", encoding="utf-8")

    assert main(["prog", str(tmp_path / "variants.json"), str(tmp_path / "localities.xml"),
                 str(mentions)]) == 0
    out = capsys.readouterr().out
    assert "Tigurum" in out and "resolved" in out and "CH" in out
    assert "{'resolved': 1, 'no_candidates': 1}" in out
    assert main(["prog"]) == 2