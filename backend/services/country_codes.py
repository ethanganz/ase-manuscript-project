"""Turns the country words used in the Bullinger place list into 2-letter codes.


What it does: changes a country word into a short code.
“Schweiz” becomes “CH”, “Italien” becomes “IT”.

Why this exists
---------------
The place list writes countries as words, in several languages and spellings:
"Schweiz", "Italien", "Italia", "Italy", "Grossbritannien", "United Kingdom" ...
The map needs ONE short code per country (ISO 3166-1 alpha-2): "CH", "IT", "GB".

Rules we follow
---------------
1. We always answer with TODAY's country that contains the place.
2. England, Scotland and Great Britain all become "GB" (the map draws one country).
3. If a value is not a single modern country (a continent, an old empire, a
   region that spans several countries) we do NOT guess. We return None and the
   place goes to a person for review. Those values are listed in NOT_MAPPED,
   each with the reason.
   The 83 comes from your place list, localities.xml
   localities.xml is the only list we have that knows 3,077 towns of that period.
   https://github.com/stazh/bullinger-korpus-tei/blob/main/data/index/localities.xml



Decisions I made that
These are judgment calls, and anyone can disagree with them:

England, Scotland and Great Britain all become GB. The map has one United Kingdom shape.
Slavonia becomes HR, Persia becomes IR. Each lies inside one modern country.
Continents, old empires and regions spanning several countries return None.
That includes Europa, Preussen, Judäa, Makedonien and Podolien.
They go to a person for review and are never guessed.
"""

# word in the place list -> code. Keys are written naturally; matching ignores
# upper/lower case (so "österreich" and "Österreich" are the same).
COUNTRY_CODES: dict[str, str] = {
    # --- Germany, Switzerland, Austria, Liechtenstein
    "Deutschland": "DE",
    "Germany": "DE",
    "Schweiz": "CH",
    "Österreich": "AT",
    "Liechtenstein": "LI",
    # --- France, Italy, Spain, Portugal
    "Frankreich": "FR",
    "France": "FR",
    "Italien": "IT",
    "Italia": "IT",
    "Italy": "IT",
    "Spanien": "ES",
    "España": "ES",
    "Portugal": "PT",
    # --- United Kingdom and Ireland
    "England": "GB",
    "Schottland": "GB",
    "Grossbritannien": "GB",
    "United Kingdom": "GB",
    "Irland": "IE",
    # --- Benelux
    "Niederlande": "NL",
    "Nederland": "NL",
    "Holland": "NL",
    "Belgien": "BE",
    "Luxemburg": "LU",
    # --- North and Baltic
    "Dänemark": "DK",
    "Danmark": "DK",
    "Schweden": "SE",
    "Norwegen": "NO",
    "Estland": "EE",
    "Lettland": "LV",
    "Litauen": "LT",
    # --- Central and Eastern Europe
    "Polen": "PL",
    "Polska": "PL",
    "Tschechien": "CZ",
    "Slowakei": "SK",
    "Slovensko": "SK",
    "Ungarn": "HU",
    "Magyarország": "HU",
    "Rumänien": "RO",
    "Bulgarien": "BG",
    "Russland": "RU",
    "Ukraine": "UA",
    "Belarus": "BY",
    "Weißrussland": "BY",
    # --- Balkans, Mediterranean
    "Kroatien": "HR",
    "Slawonien": "HR",  # Slavonia lies in Croatia today
    "Slowenien": "SI",
    "Serbien": "RS",
    "Montenegro": "ME",
    "Albanien": "AL",
    "Bosnia and Herzegovina": "BA",
    "Griechenland": "GR",
    "Malta": "MT",
    "Zypern": "CY",
    # --- Middle East, Asia, Africa, Americas
    "Türkei": "TR",
    "Turkey": "TR",
    "Syrien": "SY",
    "Libanon": "LB",
    "Israel": "IL",
    "Irak": "IQ",
    "Persien": "IR",  # Persia = Iran
    "Armenien": "AM",
    "Indien": "IN",
    "Ägypten": "EG",
    "Libyien": "LY",  # typo for "Libyen" in the source list
    "Tunesien": "TN",
    "Tunesische Republik": "TN",
    "Algerien": "DZ",
    "Äthiopien": "ET",
    "Peru": "PE",
}

# Values we deliberately do NOT turn into a code, with the reason.
NOT_MAPPED: dict[str, str] = {
    "Europa": "continent",
    "Asien": "continent",
    "Afrika": "continent",
    "Nordafrika": "part of a continent",
    "Südamerika": "part of a continent",
    "Mittlerer Osten": "region spanning many countries",
    "Mesopotamien": "old region spanning several countries",
    "Judäa": "old region, modern ownership is disputed",
    "Oströmisches Reich": "old empire",
    "Preussen": "old state spanning several modern countries",
    "Podolien": "region spanning Ukraine and Moldova",
    "Makedonien": "region spanning several countries",
    "Mazendonien": "typo for Macedonia, a region spanning several countries",
}

# Lookup table with lower-case keys. casefold() is the strict version of lower():
# it also treats "ß" as "ss", so "Weißrussland" matches however it is typed.
_LOOKUP = {name.casefold(): code for name, code in COUNTRY_CODES.items()}


def country_code(name: str | None) -> str | None:
    """ "Schweiz" -> "CH". Returns None for empty values, unknown words, and
    everything listed in NOT_MAPPED (never guesses)."""
    if not name:
        return None
    return _LOOKUP.get(name.strip().casefold())
