"""Model2VecEmbedder, without the real model (tests never download it)."""

from unittest.mock import patch

from fullstack_pokedex.infrastructure.embeddings import Model2VecEmbedder


def test_loads_the_model_from_the_local_cache_first() -> None:
    """model2vec's default (force_download=True) contacts the Hub on every load."""
    with patch(
        "fullstack_pokedex.infrastructure.embeddings.StaticModel.from_pretrained"
    ) as from_pretrained:
        Model2VecEmbedder("some/model")

    from_pretrained.assert_called_once_with("some/model", force_download=False)


def test_embed_returns_plain_python_lists() -> None:
    """The domain never sees numpy."""
    with patch(
        "fullstack_pokedex.infrastructure.embeddings.StaticModel.from_pretrained"
    ) as from_pretrained:
        from_pretrained.return_value.encode.return_value.tolist.return_value = [[0.5]]
        embedder = Model2VecEmbedder("some/model")

    assert embedder.embed(("yellow mouse",)) == [[0.5]]
    from_pretrained.return_value.encode.assert_called_once_with(["yellow mouse"])
