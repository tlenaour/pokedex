import uvicorn


def main() -> None:
    """Start the API (http://127.0.0.1:8000/docs)."""
    uvicorn.run("fullstack_pokedex.api.app:create_app", factory=True)
