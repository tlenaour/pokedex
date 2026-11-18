# Use of AI in this project

AI is used in two places: **in the product** (to build reference data, and one model at runtime), and **to build the product** (an AI coding assistant). This page says where, why, and how its output is checked.

## 1. In the product

### At runtime: one embedding model, nothing generative

| What | Model | Where | Why |
|---|---|---|---|
| Search by description | `minishlab/potion-base-32M` (model2vec, static embeddings, 131 MB) | `infrastructure/embeddings.py` | compares the **meaning** of the user's description with 151 reference descriptions |

- **No generative AI at request time.** The model turns a text into a vector; the same text always gives the same vector, so results are **deterministic** and testable.
- **Local**: the model runs in the backend process (no GPU, no PyTorch, ~10 ms per search), from a local cache; the Docker image embeds it and never calls the Internet.
- **Chosen by measurement**: several models and several strategies compared on several evaluation queries; a generative LLM was ruled out (slow, costly, not deterministic, may invent a name).
- **Guard-rails**: the index records the model that built it, and the API refuses (503) to compare vectors from another model; a test with the real model fails if identification quality drops (`tests/test_appearance_quality.py`).

### Offline: two data files written with an LLM, once

Both were generated with **Claude Fable 5.2** (Anthropic, model id `claude-fable-5-2`).

| File | What the LLM wrote | Prompt | Checks |
|---|---|---|---|
| `data/pokemon_descriptions.json` | 3 short appearance descriptions per Pokémon (the references of the search by description) | [`src/fullstack_pokedex/prompts/pokemon_descriptions.md`](src/fullstack_pokedex/prompts/pokemon_descriptions.md) | `tests/test_appearance_descriptions.py`: structure, lengths, no Pokémon names, no game vocabulary, distinct texts |
| `data/tags_llm.json` | effect tags of the 164 moves and 114 abilities (`inflicts:sleep`, `immune:ground`…), used by How to beat it | [`src/fullstack_pokedex/prompts/tag_effects.md`](src/fullstack_pokedex/prompts/tag_effects.md) | `scripts/build_tags.py`: closed vocabulary, and each tag's `evidence` must be an **exact quote** of the move or ability text, so a tag cannot be invented |

- Generated **once** with Claude Fable 5.2, reviewed, **versioned** in `data/`: the application reads files, never an LLM.

**Not finished**:

- the human review is partial: the automatic checks verify the **form**, not visual accuracy; the checklist (Venomoth, look-alike pairs, color mismatches) is still open, as are the 9 tags labeled `confidence: low`.

## 2. To build the product

The code, the tests and the documentation were written with an **AI coding assistant (Claude Code)**, directed by the developer.

### Who decides what

| The developer | The assistant |
|---|---|
| the product (persona, features, scope: English only, no accounts) | proposes options with their trade-offs, and a recommendation |
| every technical choice: larger changes start with a written plan the developer approves, smaller ones are asked for explicitly | implements the approved plan, tests included |
| what is kept, changed or dropped after review | reports what was verified and what was not |

### How its work is checked

- **Tests on everything it writes**: 497 backend and 75 frontend tests, a 95 % coverage threshold on both sides, run by CI on every push.
- **Tests that are proven to catch bugs**: for sensitive fixes, the code was deliberately broken to check that the new test fails, then restored.
- **Measurements, not opinions**: search thresholds and the embedding model were chosen from benchmarks.
- **Independent review passes**: separate agent sessions reviewed the code and the docs (skeptical frontend review, cold read of the docs, audit of doc ↔ code consistency); their findings were checked against the code before being applied.
- **Contract checks**: the API's OpenAPI is versioned, and a test fails if the code and the frontend's types drift apart.

### Rules given to AI agents

[`AGENTS.md`](AGENTS.md) (loaded by Claude Code through [`CLAUDE.md`](CLAUDE.md)) gives every agent session the same rules: the commands to pass before saying "done", the architecture rules, the frontend kept simple enough for a backend developer to defend, no new dependency without a reason, and the pitfalls already met.
