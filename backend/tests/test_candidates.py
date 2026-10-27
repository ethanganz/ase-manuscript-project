import copy

from services.candidates import choose_candidate, group_candidates


def cand(name, lat, lng, country=None, official_id=None, cid="x"):
    """Builds a candidate shaped like the ones in place_candidates."""
    fields = {"settlement": name, "country": country} if country else {}
    out = {
        "id": cid,
        "canonical_name": name,
        "latitude": lat,
        "longitude": lng,
        "official_name_fields": fields,
    }
    if official_id:
        out["official_place_id"] = official_id
    return out


# --- the REAL candidates from shaotong file ;)) --------------------------------
TIGURUM = [
    cand("Zürich", 47.3769, 8.5417, cid="zurich"),  # diary PDF, no country
    cand("Zürich", 47.36667, 8.55, "Schweiz", "l587", "bullinger:l587"),  # official list
]
BASILEE = [
    cand("Basel", 47.5596, 7.5886, cid="basel"),
    cand("Basel", 47.55839, 7.57327, "Schweiz", "l28", "bullinger:l28"),
]
ARGENTINA = [cand("Straßburg", 48.58392, 7.74553, "Frankreich", "l491", "bullinger:l491")]


def test_tigurum_two_candidates_become_one_zurich_in_switzerland():
    r = choose_candidate(TIGURUM)
    assert (r.status, r.name, r.country_code) == ("resolved", "Zürich", "CH")
    assert r.official_place_id == "l587"
    assert (r.latitude, r.longitude) == (47.36667, 8.55)  # the official one wins


def test_basel():
    r = choose_candidate(BASILEE)
    assert (r.status, r.country_code, r.official_place_id) == ("resolved", "CH", "l28")


def test_argentina_is_strasbourg_in_france_not_the_country():
    r = choose_candidate(ARGENTINA)
    assert (r.status, r.name, r.country_code) == ("resolved", "Straßburg", "FR")


def test_order_of_candidates_does_not_change_the_answer():
    assert choose_candidate(TIGURUM) == choose_candidate(list(reversed(TIGURUM)))


def test_input_is_not_modified():
    before = copy.deepcopy(TIGURUM)
    choose_candidate(TIGURUM)
    assert TIGURUM == before


def test_no_candidates():
    for empty in ([], None):
        assert choose_candidate(empty).status == "no_candidates"


def test_candidates_without_coordinates_are_ignored():
    broken = {
        "id": "y",
        "canonical_name": "Nowhere",
        "latitude": None,
        "longitude": None,
    }
    assert choose_candidate([broken]).status == "no_candidates"
    assert choose_candidate([broken, *ARGENTINA]).status == "resolved"


def test_same_name_far_apart_is_ambiguous_and_never_guessed():
    frankfurt = [
        cand("Frankfurt", 50.11, 8.68, "Deutschland"),  # am Main
        cand("Frankfurt", 52.34, 14.55, "Deutschland"),
    ]  # an der Oder
    r = choose_candidate(frankfurt)
    assert r.status == "ambiguous" and r.country_code is None and r.latitude is None
    assert len(r.alternatives) == 2


def test_different_names_close_together_are_different_places():
    # Zürich and Küsnacht are about 8 km apart but are different towns.
    assert len(group_candidates([cand("Zürich", 47.37, 8.54), cand("Küsnacht", 47.32, 8.58)])) == 2


def test_accents_and_capitals_do_not_split_a_place():
    r = choose_candidate(
        [
            cand("Zurich", 47.3769, 8.5417),
            cand("ZÜRICH", 47.36667, 8.55, "Schweiz", "l587"),
        ]
    )
    assert r.status == "resolved" and r.country_code == "CH"


def test_place_without_any_country():
    r = choose_candidate([cand("Dublin", 53.34, -6.26)])
    assert r.status == "no_country" and r.latitude == 53.34 and "no country" in r.reason


def test_country_that_is_not_a_single_country():
    r = choose_candidate([cand("Königsberg", 54.71, 20.51, "Preussen")])
    assert r.status == "no_country" and "Preussen" in r.reason and r.country_code is None
