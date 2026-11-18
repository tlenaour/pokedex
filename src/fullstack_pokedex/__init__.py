import os

import uvicorn


def main() -> None:
    """Start the server (API docs: http://127.0.0.1:8000/api/docs).

    Listens on localhost only by default. In a container, set
    `POKEDEX_HOST=0.0.0.0` to be reachable from outside it.
    """
    uvicorn.run(
        "fullstack_pokedex.api.app:create_server",
        factory=True,
        host=os.environ.get("POKEDEX_HOST", "127.0.0.1"),
        port=int(os.environ.get("POKEDEX_PORT", "8000")),
    )
