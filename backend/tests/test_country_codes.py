import pytest

from services.country_codes import COUNTRY_CODES, NOT_MAPPED, country_code

# Every non-empty country value found in the Bullinger place list (83 values).
# If the list is updated and a new value appears, we can add it to COUNTRY_CODES or NOT_MAPPED.
VALUES_IN_BULLINGER_LIST = [
    "Deutschland", "Schweiz", "Frankreich", "Italien", "England", "Polen", "Österreich",
    "Niederlande", "Tschechien", "Italia", "Griechenland", "Grossbritannien", "Spanien",
    "Belgien", "Ungarn", "Türkei", "United Kingdom", "Rumänien", "France", "Kroatien",
    "Belarus", "Dänemark", "Russland", "Tunesien", "Ukraine", "Indien", "Israel", "Portugal",
    "Schottland", "Slowakei", "Slowenien", "Ägypten", "Estland", "Litauen", "Luxemburg",
    "Serbien", "Syrien", "Zypern", "Albanien", "Algerien", "Germany", "Irak", "Irland",
    "Lettland", "Libanon", "Montenegro", "Nederland", "Polska", "Schweden", "Slovensko",
    "Tunesische Republik", "Weißrussland", "Afrika", "Armenien", "Asien",
    "Bosnia and Herzegovina", "Bulgarien", "Danmark", "España", "Europa", "Holland", "Italy",
    "Judäa", "Libyien", "Liechtenstein", "Magyarország", "Makedonien", "Malta", "Mazendonien",
    "Mesopotamien", "Mittlerer Osten", "Nordafrika", "Norwegen", "Oströmisches Reich",
    "Persien", "Peru", "Podolien", "Preussen", "Slawonien", "Südamerika", "Turkey",
    "Äthiopien", "österreich",
]


def test_the_common_cases():
    assert country_code("Schweiz") == "CH"
    assert country_code("Deutschland") == "DE"
    assert country_code("Frankreich") == "FR"


def test_several_spellings_give_the_same_code():
    assert {country_code(x) for x in ["Italien", "Italia", "Italy"]} == {"IT"}
    assert {country_code(x) for x in ["Niederlande", "Nederland", "Holland"]} == {"NL"}
    assert {country_code(x) for x in ["Tunesien", "Tunesische Republik"]} == {"TN"}


def test_uk_nations_all_become_gb():
    for name in ["England", "Schottland", "Grossbritannien", "United Kingdom"]:
        assert country_code(name) == "GB"


def test_upper_lower_case_and_spaces_do_not_matter():
    assert country_code("österreich") == "AT"
    assert country_code("  SCHWEIZ ") == "CH"
    assert country_code("Weißrussland") == "BY"


def test_not_a_single_country_returns_none_instead_of_guessing():
    for name in ["Europa", "Afrika", "Preussen", "Oströmisches Reich", "Judäa"]:
        assert country_code(name) is None


def test_empty_and_unknown_return_none():
    assert country_code("") is None
    assert country_code(None) is None
    assert country_code("Atlantis") is None


@pytest.mark.parametrize("value", VALUES_IN_BULLINGER_LIST)
def test_every_value_in_the_real_list_is_handled(value):
    # Either it has a code, or it is deliberately listed with a reason. Never forgotten.
    # (Compared ignoring upper/lower case, because the real list contains "österreich".)
    not_mapped = {name.casefold() for name in NOT_MAPPED}
    assert country_code(value) is not None or value.casefold() in not_mapped


def test_no_value_is_in_both_tables():
    assert not set(COUNTRY_CODES) & set(NOT_MAPPED)


def test_all_codes_are_two_capital_letters():
    for code in COUNTRY_CODES.values():
        assert len(code) == 2 and code.isupper() and code.isalpha()