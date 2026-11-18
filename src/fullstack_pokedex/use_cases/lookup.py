"""Finding one entity from a reference: an id or a name.

`/pokemon/25` and `/pokemon/pikachu` name the same Pokémon. The API decides
which one a reference is (`_parse_ref`); the use cases look it up here, the
same way for Pokémon, moves and abilities.
"""

from typing import Protocol

from fullstack_pokedex.domain.errors import NotFoundError


class FindsByRef[T](Protocol):
    def get_by_id(self, entity_id: int, /) -> T | None: ...
    def get_by_name(self, name: str, /) -> T | None: ...


def find_by_ref[T](repository: FindsByRef[T], ref: int | str, entity: str) -> T:
    """The entity with this id (int) or name (str); NotFoundError otherwise."""
    found = (
        repository.get_by_id(ref)
        if isinstance(ref, int)
        else repository.get_by_name(ref)
    )
    if found is None:
        raise NotFoundError(entity, ref)
    return found
