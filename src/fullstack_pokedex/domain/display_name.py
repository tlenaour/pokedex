"""How a Pokémon name is written for people, from its dataset slug.

    "bulbasaur" -> "Bulbasaur"      "mr-mime"   -> "Mr. Mime"
    "nidoran-f" -> "Nidoran♀"       "farfetchd" -> "Farfetch'd"

Invariant: normalize_name(display_name(slug)) == normalize_name(slug), so a
match span on the slug also highlights the display name (see split_by_span).
"""

# Names no rule can guess (official spellings). The only ones among #1-151.
_SPECIAL_CASES = {
    "mr-mime": "Mr. Mime",
    "nidoran-f": "Nidoran♀",
    "nidoran-m": "Nidoran♂",
    "farfetchd": "Farfetch'd",
}


def display_name(slug: str) -> str:
    """Official spelling of a Pokémon name.

    Special cases first, then each hyphen-separated part capitalized, which
    also fits later generations ("ho-oh" -> "Ho-Oh", "porygon-z" -> "Porygon-Z").
    """
    if slug in _SPECIAL_CASES:
        return _SPECIAL_CASES[slug]
    return "-".join(part[:1].upper() + part[1:] for part in slug.split("-"))
