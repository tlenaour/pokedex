# Instructions for AI coding agents

Read this before changing anything. Details: [`docs/architecture.md`](docs/architecture.md) (how it works) and [`docs/development.md`](docs/development.md) (how to work on it).

## Project in one paragraph

Pokédex web app (151 Pokémon). FastAPI backend in `src/fullstack_pokedex/` (layered: `domain/`, `use_cases/`, `infrastructure/`, `api/`), read-only SQLite `pokedex.db` built by `pokedex-import`, writable `feedback.db` for user reports. React frontend in `frontend/` with two screens: home (search by name or description over the catalog) and Pokémon page (`#/pokemon/<name>`). In production, one process serves the API under `/api` and the built frontend at `/` (`create_server` in `api/app.py`).

## Before saying "done"

All three must pass (skip the frontend line only if you did not touch `frontend/` and did not change the API). CI (`.github/workflows/ci.yml`) runs exactly these, plus a build and test of the Docker image. Report failures as they are:

```bash
uv run pytest                                          # fails below 95 % coverage
uv run ruff check . && uv run ruff format --check .   # rules: pyproject.toml [tool.ruff.lint]
cd frontend && pnpm test:coverage && pnpm lint && pnpm build   # coverage ≥ 95 % too
```

## Rules

- **English everywhere**: interface, data, code, comments, docs. Do not propose other languages.
- **No authentication**, no accounts: out of scope.
- **Simplest deterministic option first.** No new dependency, library or service without a stated reason; prefer a few lines of code.
- **Dependencies point to the domain.** `domain/` imports nothing from the other layers or from third-party I/O libraries; it defines ports (`Protocol`), `infrastructure/` implements them, `api/routes.py` wires them.
- **Routes call a use case** (`use_cases/`), not repositories. A route only parses the request (`_parse_ref` turns `25` / `pikachu` into an id or a name) and shapes the response; the lookup by reference is `find_by_ref` (`use_cases/lookup.py`). Only the plain lists `/moves` and `/abilities` still read repositories directly (`/types` returns the type list itself).
- **No business logic in the frontend.** It shows what the API returns, in the API's order: no sorting, filtering, ranking or game rules. Wording of API codes is allowed (`features/matchup/labels.ts`).
- **The API's contract is `frontend/openapi.json`**, versioned. After any API change: `uv run pokedex-openapi` (writes it from the code, no server needed), then `cd frontend && pnpm build` (regenerates `src/api/schema.d.ts` from it and type-checks), and fix what fails. A pytest test fails while the contract is stale. Never edit `openapi.json` or `schema.d.ts` by hand; commit both with the API change.
- **After changing `data/`**, run `uv run pokedex-import` (vectors and tags are computed at import).
- **`feedback.db` holds user data**: never drop, recreate or migrate it destructively. `pokedex.db` can always be rebuilt.
- **Do not commit** `pokedex.json`, `*.db`, `.coverage`, or anything from `.venv`, `node_modules`, `dist`.
- **The frontend must stay explainable by a backend developer.** The maintainer is a backend developer who has to defend every frontend choice. Prefer plain React, HTML and Tailwind; no new frontend library (router, UI kit, state manager, form library, animation…) without a stated reason and the user's agreement; no clever abstractions. When you make a frontend choice, write its reason in [`docs/frontend.md`](docs/frontend.md).
- Comments explain **why**, not what. Keep the existing tone: short, plain sentences.

## Where to put what

| Change | Place |
|---|---|
| business rule, validation, ranking, game rule | `src/fullstack_pokedex/domain/` |
| orchestration of a request (validate → fetch → rank → assemble) | `src/fullstack_pokedex/use_cases/` |
| SQL, files, third-party libraries | `src/fullstack_pokedex/infrastructure/` |
| HTTP route, response schema, dependency wiring | `src/fullstack_pokedex/api/routes.py`, `schemas.py` |
| new business error | a `DomainError` subclass in `domain/errors.py`: 422 automatically; another status goes in `_DOMAIN_ERROR_STATUS` (`api/app.py`) |
| UI of a feature | `frontend/src/features/<feature>/` (component, `useX.ts` hook); its user-level test goes in the test file of the screen that shows it (`Home.test.tsx`, `PokemonPage.test.tsx`) |
| hash route | `frontend/src/navigation.ts` |
| reference data | `data/` (see `data/README.md`) |
