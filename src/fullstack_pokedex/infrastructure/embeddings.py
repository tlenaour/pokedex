"""TextEmbedder implementation with model2vec (static embeddings, no PyTorch).

The only module importing model2vec. Model choice measured in
benchmarks/appearance_embeddings.py (potion-base-32M: same quality as
sentence-transformers models, 131 MB, no PyTorch, ~0.01 ms per query).

The model is downloaded from Hugging Face on first use and cached locally. To
run offline (e.g. in a container), download it once and point
POKEDEX_EMBEDDING_MODEL to the local folder.
"""

import os
from collections.abc import Sequence

from model2vec import StaticModel

DEFAULT_MODEL = "minishlab/potion-base-32M"


def configured_model() -> str:
    """Model name or local path, from POKEDEX_EMBEDDING_MODEL if set."""
    return os.environ.get("POKEDEX_EMBEDDING_MODEL", DEFAULT_MODEL)


class Model2VecEmbedder:
    def __init__(self, model: str | None = None) -> None:
        self.model_name = model or configured_model()
        # force_download=False: use the cached model when it is there. model2vec's
        # default (True) contacts the Hugging Face Hub on every load, so the first
        # search would wait on the network, or hang if the Hub is unreachable.
        self._model = StaticModel.from_pretrained(self.model_name, force_download=False)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return self._model.encode(list(texts)).tolist()
