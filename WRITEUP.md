# Pokédex — write-up (v1)

A web Pokédex for the 151 Pokémon of Kanto, built around one moment: **a trainer facing a Pokémon who needs to know, in a few seconds, what it is and how to beat it.**

## The persona

**Ash, a Pokémon trainer, in a world where Pokémon really exist.** Ash is traveling through **Kanto**, and his goal is to **catch all 151 Pokémon** of the region.

- **He explores the tall grass all day.** Pokémon jump out at him; he observes them, but does not know them all yet.
- **He talks a lot with other trainers**, who tell him about many Pokémon. But he has a poor memory: he only **half-remembers the names** he heard ("Bulba-something?").
- **He keeps running into the same Pokémon**, and still does not always remember their names.
- **To catch a Pokémon, he must first beat it**: weaken it without knocking it out, ideally put it to sleep or paralyze it. He wants to know **before** the fight how to do that.

He has his phone in a pocket and wants an answer in **two taps** (type, tap a result), one-handed, on a small screen, without reading an encyclopedia while the Pokémon is in front of him.

## The product in two screens

1. **Home**: one search field above the full catalog. Search **by name** (tolerates typos, results while typing) or **by description** ("small yellow mouse with red cheeks").
2. **Pokémon page**: **How to beat it** first (what to use, what to avoid, what to watch out for), the encyclopedia below.

## Features, and why

### Browse the catalog
*Ash wants all 151: between two encounters, he checks which ones exist in Kanto, and recognizes the ones he saw from their picture.*

The 151 Pokémon in Pokédex order, as cards (sprite, number, name, category, types). Shown as soon as the page opens, no click needed. No pagination: the whole list is ~30 KB and pictures load as they scroll into view.

### Find a Pokémon from a half-remembered name
*Another trainer told Ash about a Pokémon "that started with bulba…", or was it "pikachoo"? He only half-remembers.*

Results while typing, ranked: exact name, then start of the name, then start of a word, then contained, then **typo-tolerant** matches marked "did you mean?". The matching part is in bold so Ash recognizes it instantly. Enter opens the first result.

**Why this way**: I benchmarked 11 similarity measures on 1,092 realistic typos. Jaro-Winkler alone catches 95 % of them with 1.4 % false positives, in one library call; a combination scored 99.6 % but needed custom code. I chose simple first.

### Identify a Pokémon from its appearance
*A Pokémon Ash has never met jumps out of the tall grass: he does not know its name, only what it looks like.*

Ash describes it in his own words; the app returns the 10 closest Pokémon, the first marked "Best match".

**Why this way**: embeddings compare **meanings**, not words ("mouse" ≈ "rodent"). A small model (model2vec, 131 MB, no GPU, no PyTorch) compares the description with 151 reviewed reference descriptions: 95.6 % right in first position on my evaluation set, deterministic, ~10 ms per search. I ruled out a generative LLM (slow, costly, not deterministic, may invent a name) and keyword filters (no synonyms; the `color` field of the data is wrong for 32 Pokémon).

### How to beat it
*Ash wants to catch it, so he has to beat it first: "what do I use, what do I avoid, can I put it to sleep?"*

Three lines, readable at a glance on a phone:
- **Use**: its weaknesses, with multipliers (×4, ×2);
- **Avoid**: its immunities and resistances, what it cures or ignores (e.g. immune to sleep), and traps (e.g. Synchronize sends poison back);
- **Watch out**: the types it hits hard, and what it can inflict (sleep, paralysis…).

**Why this way**: Ash needs actions, not a table of data. Type rules are computed from the official type chart; move and ability effects come from tags reviewed once, offline. Moves almost every Pokémon learns (Toxic, Rest…) are ignored, otherwise every Pokémon "can poison".

### "Didn't find your Pokémon? Report"
*The search failed, and the Pokémon is still standing in front of Ash.*

One click under any result list saves the search and what was shown. No form: if Ash knew the answer, he would have found it.

**Why this way**: my search thresholds were tuned on cases I wrote myself. Real failed searches are the data I need to improve both searches.

### Recently viewed
*Ash keeps running into the same Pokémon, and keeps forgetting their names: the ones he already looked up are one tap away.*

The last 5 pages opened, under the search field, one tap away. Stored in the browser only (no accounts).

## Technical choices

### Backend: Python, FastAPI, SQLite
- **FastAPI**: typed endpoints and an OpenAPI schema for free; that schema generates the frontend's types.
- **SQLite**: 151 Pokémon of read-only data, rebuilt from the source file in one command. No database server to run. User reports go in a separate file that rebuilds never touch.
- **Layered code** (domain / use cases / infrastructure / API): game rules and search ranking are pure, tested Python, independent of SQLite, FastAPI or the libraries, which can be swapped.
- **Deterministic everywhere**: no AI at request time beyond an embedding model that always gives the same answer.

### Frontend: React, TypeScript, Vite, Tailwind
- **A static app** served by the backend: one process, one Docker image, no Node server in production.
- **Types generated from the API**: if the API changes, the frontend stops compiling instead of breaking for Ash.
- **TanStack Query** for loading, caching and canceling requests while typing.
- **No router, no UI kit, no state library**: two screens do not need them, and the code stays explainable by a backend developer.
- **No business logic in the browser**: ranking and game rules live in one place, the backend.

### Quality and delivery
- 497 backend tests and 75 frontend tests (user journeys through the real app, API faked at the network level); both fail under 95 % coverage.
- Lint, tests, coverage and a build and test of the Docker image
- One Docker image: API under `/api`, site at `/`, model and data embedded, works without Internet.

## Next steps: recommendation and team

Today, How to beat it tells Ash **what types** to use. It does not tell him **which of his Pokémon** to send. Two features answer that, the second building on the first.

### 1. Recommend a Pokémon for this fight

From the opponent's weaknesses and threats, rank the Pokémon best suited to the fight, and show the top few on the page, under **Use**:
- **types first**: the ones whose types hit it hardest while resisting what it throws back (the type rules are already in the domain);
- **then moves**: the ones that can actually learn a super-effective move;
- **then catching**: since Ash wants to **catch** the Pokémon, not knock it out, favor the ones that can put it to sleep or paralyze it, unless it is immune (already known: the **Avoid** line), and that do not hit too hard.

### 2. Ash's team

Ash only carries a few Pokémon. Let him **enter his team** (up to 6 Pokémon) once, then the recommendation answers the real question: **"which Pokémon of my team is best for this fight?"**
- the team is kept on the phone, like the recently viewed Pokémon (no accounts);
- on a Pokémon's page, each team member gets a verdict for this fight (good choice, risky, can put it to sleep…), best first;
- if no team member fits, say so, and suggest which Pokémon to catch next to fill the gap.

### 3. How to beat a gym trainer

Gym battles are different: the gym leader's team is known in advance, and Ash can pick his 6 Pokémon **before** walking in.

- Ash enters the **gym leader's team** (the Pokémon and their order, as other trainers told him).
- The app proposes **a team of 6 chosen from all the Pokémon Ash has caught**, not just the ones he carries: the 6 that together beat every Pokémon of the opposing team, with as few weak spots as possible.
- For each opposing Pokémon, it says **which member of the proposed team to send**, and why (super-effective type, resists its attacks, can put it to sleep…).
- This needs Ash's **collection**: the Pokémon he has caught, ticked in the catalog. It fits his goal of catching all 151, and the catalog could show his progress (e.g. "87 / 151 caught").

It builds on the two steps above: the recommendation scores one Pokémon against one opponent; here, the app picks the best combination of 6 against a whole team.
