# Pokédex

A web Pokédex for the 151 Pokémon of the first generation, built for a player in the middle of a battle: find a Pokémon in a couple of taps, then read how to beat it.

- **Home**: one search field above the catalog. Search **by name** (tolerates typos, results while typing) or **by description** of what the Pokémon looks like ("small yellow mouse with red cheeks").
- **Pokémon page**: **How to beat it** first (what to use, what to avoid, what to watch out for), then the encyclopedia (stats, abilities, evolution family).
- **"Didn't find your Pokémon? Report"** under every search: failed searches are saved to improve the search later.

Everything is in English: interface, data, code and docs.

## Stack

| | |
|---|---|
| Backend | Python (3.15 pinned, ≥ 3.12 supported), FastAPI, SQLite, rapidfuzz (typo tolerance), model2vec (embeddings for the search by description), uv |
| Frontend | React 19, TypeScript, Vite, TanStack Query, openapi-fetch (types generated from the API), Tailwind CSS, pnpm |
| Tests | pytest, Vitest + Testing Library + MSW |
| Deployment | one Docker image: the backend serves the API under `/api` and the built frontend at `/` |

## Quick start

Prerequisites: Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/), Node 24 with pnpm (`corepack enable pnpm`), and **`pokedex.json` at the repository root** (the raw data, not versioned):

```bash
curl -fsSL -o pokedex.json https://biolevatestatics.blob.core.windows.net/biolevate-tech-assessments/pokedex/pokedex.json
```

```bash
# Backend (repository root)
uv sync
uv run pokedex-import          # builds pokedex.db; downloads the embedding model the first time (~130 MB)
uv run fullstack-pokedex       # http://127.0.0.1:8000/api (API docs: /api/docs)

# Frontend (another terminal)
cd frontend
pnpm install
pnpm dev                       # http://localhost:5173 (calls to /api go to the backend)
```

With Docker, nothing to install but Docker: `docker compose up -d`, then open http://localhost:8000. See [`DOCKER.md`](DOCKER.md).

## Checks

```bash
uv run pytest                                          # backend tests + coverage
uv run ruff check . && uv run ruff format --check .    # backend lint and format
cd frontend && pnpm test:coverage && pnpm lint && pnpm build
```

CI (`.github/workflows/ci.yml`) runs the same checks on every push and pull request, then builds and tests the Docker image. It publishes nothing.

## Repository map

| Path | Content |
|---|---|
| `src/fullstack_pokedex/` | backend: `domain/`, `use_cases/`, `infrastructure/`, `api/` |
| `tests/` | backend tests (one file per backend module, mini dataset in `fixtures/`) |
| `frontend/` | React app (`src/features/<feature>/`) |
| `data/` | versioned reference data: appearance descriptions, effect tags ([`data/README.md`](data/README.md)) |
| `benchmarks/` | scripts and results behind the search choices |
| `scripts/` | data build script, Docker image test |
| `docs/` | documentation ([index](docs/README.md)) |
| `.github/workflows/` | CI |
| `Dockerfile`, `compose.yaml` | the deployable image |

## Read next

- [`docs/architecture.md`](docs/architecture.md): how the project works today.
- [`docs/development.md`](docs/development.md): setup details, tests, conventions, recipes.
- [`docs/frontend.md`](docs/frontend.md): the frontend explained to a backend developer, with the reasons behind each choice.
- [`AGENTS.md`](AGENTS.md): the rules for AI coding agents (useful to humans too). `CLAUDE.md` only imports it, for Claude Code.
- [`WRITEUP.md`](WRITEUP.md): the product, the persona, the choices and the next steps, in one page.
- [`AI_USAGE.md`](AI_USAGE.md): where AI is used, in the product and to build it, and how it is checked.
- [`docs/README.md`](docs/README.md): every document, and who it is for.
