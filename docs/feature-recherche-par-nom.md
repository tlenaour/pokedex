# Feature : retrouver un Pokémon à partir d'un nom à moitié retenu

> **Pour qui :** une personne qui arrive sur le projet et veut comprendre **ce qui a été construit, dans quel ordre, et pourquoi**.
>
> **Ce document raconte la démarche.** Pour le détail de l'étude sur la tolérance aux fautes de frappe, voir [`benchmark-fuzzy-name-matching.md`](benchmark-fuzzy-name-matching.md).
>
> **État au 2026-11-11 :** backend et frontend livrés pour cette feature. 291 tests backend et 16 tests frontend passent.

---

## Sommaire

1. [La feature en une page](#1-la-feature-en-une-page)
2. [Démarrer en 5 minutes](#2-démarrer-en-5-minutes)
3. [Architecture d'ensemble](#3-architecture-densemble)
4. [La démarche, étape par étape](#4-la-démarche-étape-par-étape)
5. [Le contrat d'API](#5-le-contrat-dapi)
6. [Les décisions et leurs raisons](#6-les-décisions-et-leurs-raisons)
7. [Stratégie de test](#7-stratégie-de-test)
8. [Limites connues et choix assumés](#8-limites-connues-et-choix-assumés)
9. [Prochaines étapes](#9-prochaines-étapes)
10. [Carte des fichiers](#10-carte-des-fichiers)

---

## 1. La feature en une page

> *A new trainer saw a Pokémon whose name began with "bulba", but cannot remember the full name. They want to find it quickly and confirm that it is the Pokémon they had in mind.*

**Ce que la demande implique :**

| Élément de la demande | Exigence technique | Réponse apportée |
|---|---|---|
| « began with *bulba* » | chercher à partir d'un **début de nom** et le classer en premier | classement par niveaux : exact > début du nom > début d'un mot > contenu dans le nom |
| « cannot remember the full name » | accepter une saisie **incomplète, voire fausse** | normalisation (casse, accents, ponctuation) + tolérance aux fautes (Jaro-Winkler) |
| « find it quickly » | réponse **pendant la frappe** | endpoint léger, 5 résultats, attente de 200 ms après la dernière frappe, cache HTTP |
| « confirm » | assez d'informations pour **reconnaître** le Pokémon | sprite, types, catégorie, partie qui correspond mise en évidence dans la suggestion ; la choisir ouvre la fiche détaillée |

**Le résultat :** `GET /pokemon/suggest?q=bulba`, et une page web où l'on tape un nom, voit les suggestions avec leur image, puis choisit son Pokémon.

---

## 2. Démarrer en 5 minutes

**Prérequis :** Python ≥ 3.12 avec [uv](https://docs.astral.sh/uv/), Node 24 avec pnpm (`corepack enable pnpm`), et le fichier `pokedex.json` à la racine. Ce fichier n'est **pas versionné**.

```bash
# Backend (racine du projet)
uv sync
uv run pokedex-import            # crée pokedex.db à partir de pokedex.json
uv run fullstack-pokedex         # API sur http://127.0.0.1:8000 (docs : /docs)

# Frontend (dans un autre terminal)
cd frontend
pnpm install
pnpm dev                         # http://localhost:5173 ; les appels /api sont redirigés vers :8000
```

| Commande | Rôle |
|---|---|
| `uv run pytest` | tests backend + couverture |
| `uv run ruff check . && uv run ruff format --check .` | lint et formatage backend |
| `cd frontend && pnpm test --run` | tests frontend |
| `pnpm lint` / `pnpm build` | lint (Biome) / vérification TypeScript et build |
| `pnpm gen:api` | régénère les types TS depuis l'OpenAPI (le backend doit tourner) |
| `uv run python benchmarks/fuzzy_name_matching.py` | relance le benchmark de tolérance aux fautes (≈ 4 min) |

---

## 3. Architecture d'ensemble

### Backend : quatre couches, inspirées de la Clean Architecture et de l'architecture hexagonale

```
api/  ──►  use_cases/  ──►  domain/  ◄──  infrastructure/
(HTTP)     (orchestration)  (règles, ports)  (SQLite, JSON, rapidfuzz)
```

| Couche | Contenu | Règle |
|---|---|---|
| **domain/** | entités Pydantic, règles métier (normalisation, classement, nom affiché), **ports** (interfaces `Protocol` : repositories, `SimilarityScorer`), erreurs | ne dépend de **rien** |
| **use_cases/** | `SuggestPokemon` : enchaîne validation → classement → chargement → assemblage | dépend du domaine seulement |
| **infrastructure/** | lecture du JSON, import et repositories SQLite, `JaroWinklerScorer` | implémente les ports du domaine |
| **api/** | routes FastAPI, schémas de réponse, middleware de cache, assemblage des dépendances | **seul endroit** où les implémentations concrètes sont choisies |

**Le principe à retenir : les dépendances pointent vers le domaine.** Le domaine ne connaît ni SQLite, ni FastAPI, ni rapidfuzz.

### Frontend : React minimal

```
frontend/src/
├── api/                  client typé + types générés depuis l'OpenAPI
├── features/suggest/     la recherche (récupération des données + composants)
├── shared/               carte et badge de type, communs aux deux recherches
└── test/                 API simulée (MSW) et configuration des tests
```

**Le front ne contient aucune logique métier.** Il ne trie, ne filtre et ne découpe rien : il affiche ce que l'API renvoie.

### Chemin complet d'une recherche

```
Navigateur : l'utilisateur tape « Bulba »
  └─ attente de 200 ms après la dernière frappe (useDebouncedValue)
  └─ GET /api/pokemon/suggest?q=Bulba&limit=5          (TanStack Query + openapi-fetch)
       └─ Vite redirige vers FastAPI :8000 /pokemon/suggest
            └─ api/routes.py : suggest_pokemon        vérifie les paramètres, appelle le cas d'usage
                 └─ use_cases/suggest_pokemon.py : SuggestPokemon.execute()
                      ├─ domain : normalize_query("Bulba") = "bulba"     (sinon 422)
                      ├─ infra  : repository.list_name_candidates()      (151 noms)
                      ├─ domain : rank_candidates(...)                   (niveaux + Jaro-Winkler)
                      ├─ infra  : repository.get_many([1])               (Pokémon complet)
                      └─ domain : display_name("bulbasaur"), split_by_span(...)
            └─ réponse JSON + Cache-Control: public, max-age=3600   (middleware)
  └─ affichage : sprite, « Bulba » en gras + « saur », types, catégorie
```

---

## 4. La démarche, étape par étape

La feature a été construite par petites étapes. Chacune était testée avant de passer à la suivante.

### Étape 0 : socle (avant la feature)

1. **Analyse de `pokedex.json`** : 151 Pokémon, 164 capacités, 114 talents. Les entités sont liées **par nom**, et chaque relation est écrite deux fois (une fois de chaque côté). Un script a vérifié que les identifiants sont uniques, qu'aucune référence n'est cassée, et que les relations concordent dans les deux sens.
2. **Modèle de données** : entités Pydantic immuables (`domain/entities.py`) et schéma SQLite avec tables de liaison (`pokemon_type` avec un `slot` qui garde l'ordre des types, `pokemon_move`, `pokemon_ability`).
3. **Import** : `infrastructure/pokedex_json.py` convertit le JSON en entités (noms → ids, `special-attack` → `special_attack`, liens en double retirés), puis `infrastructure/sqlite/importer.py` les écrit en base en une seule transaction. Commande : `uv run pokedex-import`.
4. **Repositories SQLite et routes de lecture** : `/pokemon`, `/moves`, `/abilities`, `/types`, en lecture seule. **Sans pagination ni couche de cas d'usage** : volontairement simple au départ.
5. **Tests** : pytest, JSON de test réduit (4 Pokémon), SQLite en mémoire, mocks des repositories pour l'API.

### Étape 1 : analyse de la feature et conception

L'endpoint existant `/pokemon?q=…` faisait une recherche `LIKE '%…%'`. Il ne classait rien, ne tolérait aucune faute, n'avait pas de limite et ne renvoyait pas assez d'informations pour confirmer. **Conclusion : un endpoint dédié, avec sa propre logique de classement.** La conception (normalisation, niveaux, contrat d'API, place dans l'architecture) a été rédigée avant d'écrire du code.

### Étape 2 : normalisation (domaine)

`normalize_name()` et `split_words()` dans `domain/name_search.py`. La saisie et les noms sont rendus comparables :
- symboles de genre : `♀` → « f », `♂` → « m » (comme dans les slugs `nidoran-f` et `nidoran-m`) ;
- décomposition Unicode (NFKD) et suppression des accents (« Bülba » → « Bulba », caractères pleine largeur → caractères normaux) ;
- `casefold()` **après** la suppression des accents (pour que `İ` donne bien « i ») ;
- apostrophes supprimées sans couper le mot (« Farfetch'd » → `farfetchd`) ;
- tout ce qui n'est pas une lettre ou un chiffre sert de séparateur (« Mr. Mime » → `mrmime`).

Invariant testé : `normalize_name(x) == "".join(split_words(x))`, et les 151 noms restent distincts une fois normalisés.

### Étape 3 : classement (domaine)

`rank_candidates()` attribue à chaque nom un niveau de correspondance (`MatchKind`) :

| Niveau | Exemple |
|---|---|
| `exact` | « bulbasaur » → bulbasaur |
| `prefix` (début du nom) | « bulba » → bulbasaur |
| `word_prefix` (début d'un autre mot) | « mime » → mr-mime |
| `substring` (contenu dans le nom) | « saur » → ivysaur |
| `fuzzy` (faute de frappe) | « bulbsaur » → bulbasaur |

Tri : niveau, puis score, puis écart de longueur avec la saisie, puis numéro de Pokédex (pour que le résultat soit toujours le même). **La correspondance approchée ne se lance que s'il manque des résultats**, et elle passe par le port `SimilarityScorer`. Le domaine décide **quand** une faute est acceptée (le seuil) ; l'infrastructure décide **comment** on mesure la ressemblance.

### Étape 4 : introduction de la couche cas d'usage

`use_cases/suggest_pokemon.py` : `SuggestPokemon.execute(SuggestPokemonQuery(text, limit))`, en quatre temps :
1. **valider avant tout accès aux données** : limite entre 1 et 10, saisie non vide après normalisation, sinon `InvalidSearchQueryError` ;
2. récupérer tous les noms et les classer ;
3. charger **seulement** les Pokémon retenus après la limite ;
4. **les remettre dans l'ordre du classement** : le port `get_many` ne garantit aucun ordre, c'est un piège testé explicitement.

### Étape 5 : infrastructure

`SqlitePokemonRepository.list_name_candidates()` et `get_many()`. Un test vérifie que **chaque implémentation fournit toutes les méthodes de son port**, puisque le projet n'a pas de vérificateur de types.

### Étape 6 : API (première livraison)

`GET /pokemon/suggest`, déclarée **avant** `/pokemon/{ref}`, sinon « suggest » serait pris pour un nom de Pokémon. Les paramètres sont vérifiés par FastAPI, et `InvalidSearchQueryError` est transformée en 422. Un test d'acceptation de bout en bout reprend la demande mot pour mot.

### Étape 7 : tolérance aux fautes (benchmark puis implémentation)

1. **Benchmark** de 9 mesures et 2 combinaisons, sur 1 092 cas (voir [`benchmark-fuzzy-name-matching.md`](benchmark-fuzzy-name-matching.md)).
2. **Décision : Jaro-Winkler seul, au seuil de 0,80.** 95,3 % des fautes rattrapées, 1,4 % de faux positifs, une seule fonction de bibliothèque, aucun changement d'architecture.
3. Implémentation : `infrastructure/similarity.py` (`JaroWinklerScorer`, seul fichier qui importe rapidfuzz), `FUZZY_THRESHOLD = 0.80` dans le domaine, branchement dans `api/routes.py`.

### Étape 8 : confort

- **Cache HTTP** : `api/middleware.py` (`CacheControlMiddleware`) ajoute `Cache-Control: public, max-age=3600` aux réponses 2xx des requêtes GET et HEAD. Jamais sur les erreurs. Une route peut imposer son propre en-tête.
- **Nom affiché et surlignage** : `domain/display_name.py` donne le nom pour l'utilisateur (`mr-mime` → « Mr. Mime »). Le domaine exprime la partie qui correspond **dans le nom normalisé** (`NameMatch.span`), et `split_by_span()` découpe n'importe quelle façon d'écrire le nom. L'API renvoie `display_name` et `match.segments`, des morceaux prêts à afficher.

### Étape 9 : frontend

1. **Choix de la stack** (voir § 6.6), puis initialisation de `frontend/` avec des versions fixées.
2. **Types générés** depuis `/openapi.json`, client `openapi-fetch`, récupération des données avec TanStack Query (attente après la frappe, annulation, cache), combobox Downshift.
3. **Tests** Vitest + Testing Library + MSW. Deux pièges rencontrés et corrigés (voir § 7).
4. **Design** : trois itérations. Écran rétro, puis appareil Pokédex complet, puis **retour à un design simple**, pour que le code reste lisible et facile à défendre (voir § 6.7).

---

## 5. Le contrat d'API

```
GET /pokemon/suggest?q=<texte>&limit=<1..10, défaut 5>
```

```json
[
  {
    "id": 122,
    "name": "mr-mime",
    "display_name": "Mr. Mime",
    "sprite": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/122.png",
    "types": ["psychic", "fairy"],
    "genus": "Barrier Pokémon",
    "match": {
      "kind": "word_prefix",
      "score": 1.0,
      "segments": [
        { "text": "Mr. ", "matched": false },
        { "text": "Mime", "matched": true }
      ]
    }
  }
]
```

| Champ | Signification |
|---|---|
| `name` | slug du jeu de données, identifiant stable |
| `display_name` | nom à afficher |
| `match.kind` | `exact`, `prefix`, `word_prefix`, `substring` ou `fuzzy` |
| `match.score` | 1.0 pour une correspondance stricte, la similarité Jaro-Winkler pour `fuzzy` |
| `match.segments` | `display_name` découpé ; mettre en évidence ceux qui ont `matched: true`. Mis bout à bout, ils redonnent toujours `display_name`. Un seul morceau non surligné pour `fuzzy` |

| Cas | Réponse |
|---|---|
| aucun résultat | `200 []` (ce n'est pas une erreur) |
| `q` absent ou vide, `limit` hors de 1..10, `q` de plus de 100 caractères | `422`, `detail` sous forme de **liste** (validation FastAPI) |
| `q` sans lettre ni chiffre (`!!!`), ou de plus de 30 caractères une fois normalisé | `422`, `detail` sous forme de **texte** (règle métier) |

---

## 6. Les décisions et leurs raisons

Chaque décision est présentée avec le choix fait, les alternatives écartées et la raison.

### 6.1 Architecture : légère d'abord, cas d'usage ensuite

- **Au départ :** `domain` / `infrastructure` / `api`, **sans cas d'usage ni pagination**. Pour un Pokédex en lecture seule, ces couches auraient été de la cérémonie.
- **Pour cette feature :** introduction de `use_cases/`. Ici, il y a une **vraie coordination** (valider, classer, charger, remettre dans l'ordre, assembler), qui n'a sa place ni dans une route HTTP, ni dans le domaine.
- **Pourquoi pas une « Clean Architecture complète » :** presenters, DTO à chaque frontière… beaucoup de code pour peu de bénéfice ici. On garde l'idée commune aux deux architectures : **la règle de dépendance et les ports**.
- **Conséquence assumée :** les routes historiques appellent encore les repositories directement. Leur migration vers des cas d'usage est prévue (§ 9).

### 6.2 Endpoint dédié plutôt qu'enrichir `/pokemon?q=`

`/pokemon` sert à **filtrer** (type, habitat…). `/pokemon/suggest` sert à **retrouver** un Pokémon précis : il classe, limite le nombre de résultats et renvoie des infos de confirmation. Mélanger les deux aurait compliqué les deux.

### 6.3 Classement en Python, pas en SQL

Avec 151 noms, tout classer en mémoire prend environ 1 ms. SQLite ne sait pas calculer une similarité approchée sans extension. Le classement est donc **une fonction pure du domaine**, testable sans base de données. Si le volume grossit fortement (toutes les générations, plusieurs langues), il faudra envisager FTS5 ou un moteur de recherche dédié.

### 6.4 Pas de cache des noms côté serveur

Mesure : la requête `SELECT id, name` prend **0,08 ms**, le classement **1,1 ms**, presque entièrement consacré à la normalisation. Un cache des noms aurait supprimé la partie qui coûte le moins, en ajoutant un risque de données périmées après réimportation. **Décision : pas de cache.** Si un jour la rapidité devient un sujet, c'est la normalisation qu'il faudra précalculer.

### 6.5 Jaro-Winkler seul plutôt que la combinaison

Le benchmark montre que la combinaison Jaro-Winkler + `prefix_osa`, une mesure maison, donne les meilleurs résultats (99,6 %). Mais elle demande du code maison et deux seuils, donc un changement d'architecture du domaine. **Jaro-Winkler seul (95,3 %)** a été retenu pour sa simplicité. On perd environ 30 % des cas « début de nom + faute ». Les options pour ajouter `prefix_osa` plus tard sont documentées dans le benchmark.

### 6.6 Stack frontend

| Choix | Pourquoi | Alternatives écartées |
|---|---|---|
| React + TypeScript + Vite | connu de l'équipe ; TS détecte les erreurs de forme de données ; Vite est le standard actuel | Next.js (rendu côté serveur inutile ici), Vue ou Svelte (à apprendre de zéro), Create React App (abandonné) |
| **openapi-typescript + openapi-fetch** | les **types viennent du backend** : si l'API change, le front ne compile plus | types écrits à la main (ils finissent par diverger de l'API) |
| TanStack Query | chargement, erreurs, cache, annulation des requêtes dépassées, sans `useEffect` fragiles | `fetch` + `useEffect` à la main |
| **Downshift** | un seul hook, du HTML qu'on écrit soi-même, accessible ; simple pour qui débute en React | React Aria (plus complet, mais plus de concepts) |
| **pnpm** | rapide, strict sur les dépendances : l'équivalent de `uv` | npm (l'équivalent de `pip`) |
| Tailwind CSS | le style s'écrit dans le composant, sans fichiers CSS à nommer | bibliothèques de composants lourdes (MUI…) |
| Vitest + Testing Library + MSW | tests du point de vue de l'utilisateur, API simulée au niveau réseau | — |
| Biome | lint + formatage en un seul outil : l'équivalent de ruff | ESLint + Prettier |

**Versions fixées et éprouvées**, pas les toutes dernières : React 19.1, Vite 6.3, Vitest 3.2, Tailwind 4.1, pnpm 10.12.1 (`packageManager`). La dernière version de pnpm (12.x) ne fonctionnait pas avec le corepack installé. pnpm 10 bloque les scripts d'installation : seuls ceux d'esbuild, Tailwind et Biome sont autorisés.

### 6.7 Design : volontairement simple

Deux designs plus élaborés ont été essayés : un écran LCD rétro, puis un appareil Pokédex complet. Ils ont été **abandonnés au profit d'un design sobre** (bandeau rouge, carte blanche, types en couleurs), **uniquement avec des classes Tailwind standard**. La raison : le front doit pouvoir être **défendu techniquement** par un développeur backend. Moins de code de présentation, c'est moins de questions sans rapport avec la feature.

### 6.8 Ce que le front fait, et ne fait pas

- **Il fait :** attendre 200 ms après la dernière frappe, annuler les requêtes dépassées, ne rien envoyer si la saisie n'a ni lettre ni chiffre (pour éviter des 422 prévisibles), afficher les états (chargement, aucun résultat, erreurs), permettre la navigation au clavier.
- **Il ne fait pas :** trier, filtrer ou découper les noms. **Toute la logique de recherche est dans le backend**, à un seul endroit, et testée.

---

## 7. Stratégie de test

| Couche | Fichiers | Approche |
|---|---|---|
| domaine | `test_name_search.py`, `test_name_ranking.py`, `test_display_name.py`, `test_entities.py` | tests purs, `parametrize`, invariants ; le scorer est un mock `create_autospec(SimilarityScorer)` |
| cas d'usage | `test_suggest_pokemon.py` | **repository et scorer remplacés par des mocks** ; vérifie l'enchaînement (validation avant tout accès aux données, limite appliquée avant le chargement, ordre conservé même si le repository renvoie les Pokémon dans un autre ordre) |
| infrastructure | `test_sqlite_*.py`, `test_pokedex_json.py`, `test_similarity.py` | **vraie SQLite en mémoire** avec `tests/fixtures/mini_pokedex.json` (remplacer `sqlite3` par un mock ne testerait rien) ; aller-retour JSON → SQLite → entités identiques |
| API | `test_api.py`, `test_cache_middleware.py` | **cas d'usage remplacé par un mock** (`dependency_overrides`) : vérifie la correspondance HTTP ↔ cas d'usage, les erreurs 422, et que `/suggest` n'est pas capté par `/{ref}` |
| bout en bout | `test_app.py` | vraie app, vraie base de test, **sans mock** ; test d'acceptation « bulba → Bulbasaur » |
| frontend | `App.test.tsx`, `HighlightedName.test.tsx` | du point de vue de l'utilisateur (« je tape, je vois, je choisis »), API simulée par MSW |

**Pourquoi des mocks à certains endroits seulement :** ils isolent la couche testée (cas d'usage, API). Mais la base de données et le scorer réel sont testés en vrai, pour vérifier qu'ils produisent les bons résultats.

**Deux pièges du frontend, à connaître** (chacun commenté dans le code) :
1. **openapi-fetch mémorisait `fetch` à l'import du module**, avant que MSW ne l'intercepte : les tests faisaient de vrais appels réseau. Le client cherche maintenant `fetch` à chaque appel (`frontend/src/api/client.ts`).
2. **jsdom remplace `AbortController` par sa propre version**, que le `fetch` de Node refuse. L'environnement de test `frontend/src/test/jsdom-environment.ts` garde celui de Node. Vérifié : sans lui, les tests échouent.

Ces deux pièges ne concernent que les tests ; dans un vrai navigateur, tout est cohérent.

---

## 8. Limites connues et choix assumés

| Limite | Exemple | Pourquoi / piste |
|---|---|---|
| **Suggestions approchées qui complètent la liste** | « char » → 3 Charmander/Charizard + **Chansey** (Jaro-Winkler 0,808) | la recherche approchée complète la liste quand il y a moins de 5 résultats exacts. Piste documentée : ne la lancer que s'il n'y a **aucun** résultat exact. Laissé tel quel pour l'instant |
| Noms de 3 lettres avec deux lettres inversées | « mwe » ne trouve pas Mew | une inversion représente 33 % du nom ; limite connue de Jaro-Winkler |
| ≈ 30 % des cas « début de nom + faute » ratés | début tapé court par rapport au nom | prix de la simplicité (§ 6.5) |
| Types actuels, pas ceux de 1996 | Mr. Mime est `psychic` + `fairy` | les données viennent de PokéAPI aujourd'hui |
| `display_name` absent de la fiche complète | `/pokemon/{id}` renvoie le slug seulement (les listes l'ont depuis le catalogue) | à étendre à `PokemonOut` |
| Deux formats d'erreur 422 | `detail` en liste (FastAPI) ou en texte (métier) | le front n'affiche qu'un message selon le code HTTP ; à harmoniser si besoin |
| Données en cache jusqu'à 1 h après une réimportation | `Cache-Control: max-age=3600` | données quasi figées ; pas d'`ETag` |
| HEAD sans effet | FastAPI répond 405 aux requêtes HEAD sur les routes déclarées en `@get` | le middleware gère quand même HEAD |
| Routes historiques sans cas d'usage | `/pokemon/{id}`, `/moves`… appellent les repositories directement (`/pokemon` passe par `ListPokemon` depuis le catalogue) | migration prévue (§ 9) |
| Sprites petits dans la liste | marge transparente des images PokéAPI | gardé pour la simplicité du code |

---

## 9. Prochaines étapes

1. **Page de fiche détaillée** (`/pokemon/{id}`) avec React Router, pour que la fiche ait sa propre adresse (aujourd'hui, elle s'ouvre dans une fenêtre par-dessus la page).
2. **Migrer les autres routes vers des cas d'usage** (`GetPokemonDetail`…), pour une règle unique : une route n'appelle qu'un cas d'usage.
3. **Réduire le bruit des suggestions approchées** : recherche approchée seulement s'il n'y a aucun résultat exact (option A), avec une nouvelle mesure du benchmark.
4. Étendre `display_name` à la fiche complète.
5. Recalibrer le seuil de tolérance aux fautes avec des **recherches réelles** (par exemple en enregistrant celles qui ne renvoient aucun résultat).

---

## 10. Carte des fichiers

### Backend : `src/fullstack_pokedex/`

| Fichier | Rôle |
|---|---|
| `domain/entities.py` | entités Pydantic immuables (`Pokemon`, `Move`, `Ability`, `Stats`…) |
| `domain/repositories.py` | ports des repositories (`Protocol`) et critères de recherche |
| `domain/name_search.py` | **cœur de la feature** : normalisation, `MatchKind`, `rank_candidates`, port `SimilarityScorer`, `split_by_span`, `FUZZY_THRESHOLD` |
| `domain/display_name.py` | nom affiché (`mr-mime` → « Mr. Mime ») |
| `domain/errors.py` | `NotFoundError`, `InvalidSearchQueryError` |
| `use_cases/suggest_pokemon.py` | cas d'usage `SuggestPokemon` |
| `infrastructure/pokedex_json.py` | JSON → entités |
| `infrastructure/sqlite/` | `schema.sql`, `importer.py` (commande `pokedex-import`), `repositories.py` |
| `infrastructure/similarity.py` | `JaroWinklerScorer` (rapidfuzz) |
| `api/app.py` | `create_app()`, conversion des erreurs en 404/422, middleware |
| `api/routes.py` | routes, dont `/pokemon/suggest`, et assemblage des dépendances |
| `api/schemas.py` | schémas de réponse (`PokemonSuggestionOut`, `MatchOut`, `NameSegmentOut`…) |
| `api/middleware.py` | `CacheControlMiddleware` |

### Tests : `tests/`

`conftest.py` (fixtures : pokedex chargé, SQLite en mémoire), `factories.py` (`make_pokemon`, `make_move`, `make_ability`), `fixtures/mini_pokedex.json` (4 Pokémon), puis un fichier par couche (voir § 7).

### Frontend : `frontend/src/`

| Fichier | Rôle |
|---|---|
| `api/schema.d.ts` | **généré**, ne pas modifier à la main (`pnpm gen:api`) |
| `api/client.ts` | client typé, types exportés, `ApiError` |
| `features/suggest/useDebouncedValue.ts` | attente après la frappe |
| `features/suggest/useSuggestions.ts` | appel à l'API (TanStack Query), messages d'erreur |
| `features/suggest/PokemonSearch.tsx` | champ + liste (Downshift) |
| `features/suggest/SuggestionItem.tsx`, `HighlightedName.tsx` | affichage d'une suggestion |
| `shared/PokemonCard.tsx`, `shared/TypeBadge.tsx`, `shared/pokemon.ts` | carte d'un Pokémon (meilleur résultat par apparence, adversaire), badge de type, utilitaires ; partagés avec la [recherche par apparence](feature-recherche-par-apparence.md) |
| `test/` | API simulée (`handlers.ts`), `setup.ts`, `render.tsx`, `jsdom-environment.ts` |

### Documentation et benchmark

| Fichier | Rôle |
|---|---|
| `docs/feature-recherche-par-nom.md` | ce document |
| `docs/feature-recherche-par-apparence.md` | la feature suivante : identifier un Pokémon par son apparence |
| `docs/benchmark-fuzzy-name-matching.md` | protocole, résultats et décision sur la tolérance aux fautes |
| `benchmarks/fuzzy_name_matching.py` | script du benchmark (reproductible, graine fixe) |
| `benchmarks/results/fuzzy_name_matching.json` | résultats bruts |
