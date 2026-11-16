# Feature : identifier un Pokémon à partir d'une description de son apparence

> **Pour qui :** une personne qui arrive sur le projet et veut comprendre **ce qui a été construit, dans quel ordre, et pourquoi**.
>
> **Ce document raconte la démarche.** Il fait suite à [`feature-recherche-par-nom.md`](feature-recherche-par-nom.md) : l'architecture, la stack frontend et les conventions de test y sont expliquées, et ne sont pas répétées ici. Les données de référence de cette feature sont décrites dans [`data/README.md`](../data/README.md).
>
> **État au 2026-11-12 :** backend et frontend livrés pour cette feature. 364 tests backend (couverture 99 %) et 26 tests frontend passent.

---

## Sommaire

1. [La feature en une page](#1-la-feature-en-une-page)
2. [Démarrer en 5 minutes](#2-démarrer-en-5-minutes)
3. [Le principe : comparer des sens, pas des mots](#3-le-principe--comparer-des-sens-pas-des-mots)
4. [Architecture](#4-architecture)
5. [La démarche, étape par étape](#5-la-démarche-étape-par-étape)
6. [Le benchmark](#6-le-benchmark)
7. [Le contrat d'API](#7-le-contrat-dapi)
8. [Les décisions et leurs raisons](#8-les-décisions-et-leurs-raisons)
9. [Stratégie de test](#9-stratégie-de-test)
10. [Limites connues et choix assumés](#10-limites-connues-et-choix-assumés)
11. [Prochaines étapes](#11-prochaines-étapes)
12. [Carte des fichiers](#12-carte-des-fichiers)

---

## 1. La feature en une page

> *Un dresseur a vu un Pokémon mais ne connaît pas son nom. Il le décrit avec ses mots (« small yellow mouse with red cheeks ») et veut savoir de quel Pokémon il s'agit.*

**Ce que la demande implique :**

| Élément de la demande | Exigence technique | Réponse apportée |
|---|---|---|
| texte **libre** | comprendre des formulations variées, des synonymes (« mouse » / « rodent ») | **embeddings** : on compare le sens des phrases, pas les mots exacts |
| décrire **l'apparence** | une référence de ce à quoi ressemble chaque Pokémon | 151 descriptions de référence relues, versionnées dans `data/` |
| « **déduire** qui c'est » | un classement, pas une réponse unique (la description peut être vague) | les 5 Pokémon les plus proches, le meilleur mis en avant |
| reconnaître le bon | assez d'informations pour **confirmer** | sprite, types, catégorie, numéro |

**Périmètre : anglais uniquement**, comme le reste des données.

**Le résultat :** `GET /pokemon/identify?description=small yellow mouse with red cheeks`, et une section « By appearance » dans la page web.

```
small yellow mouse with red cheeks   → Pikachu (0.73), Sandshrew, Voltorb
big orange dragon with wings         → Charizard (0.75), Dragonite, Moltres
ball of blue vines with red feet     → Tangela (0.71), Vileplume, Oddish
kangaroo with a baby in its pouch    → Kangaskhan (0.77), Chansey, Wigglytuff
```

---

## 2. Démarrer en 5 minutes

Mêmes prérequis que la recherche par nom. Une seule différence : **le premier `pokedex-import` télécharge le modèle d'embeddings** (environ 130 Mo, dans le cache Hugging Face `~/.cache/huggingface/`). Les fois suivantes, tout se fait hors ligne.

```bash
# Backend (racine du projet)
uv sync
uv run pokedex-import            # crée pokedex.db ET l'index d'apparence (≈ 1 s une fois le modèle en cache)
uv run fullstack-pokedex         # API sur http://127.0.0.1:8000

# Frontend (dans un autre terminal)
cd frontend && pnpm install && pnpm dev     # http://localhost:5173, section « By appearance »
```

| Commande | Rôle |
|---|---|
| `curl "localhost:8000/pokemon/identify?description=small%20yellow%20mouse"` | essai direct de l'API |
| `uv run pytest tests/test_appearance_descriptions.py` | vérifie la forme des 151 descriptions après une modification |
| `uv run pytest tests/test_appearance_quality.py` | vérifie la qualité d'identification **avec le vrai modèle** |
| voir l'en-tête de `benchmarks/appearance_embeddings.py` | relancer le benchmark (environnement séparé) |

**Après toute modification de `data/pokemon_descriptions.json`, relancer `uv run pokedex-import`** : les vecteurs ne sont recalculés qu'à l'import.

---

## 3. Le principe : comparer des sens, pas des mots

Un **modèle d'embeddings** transforme un texte en une liste de nombres (un **vecteur**, ici 512 nombres). Il a été entraîné pour que deux textes **de sens proche** donnent des vecteurs proches, même sans mot en commun : « small yellow rodent » est proche de « little yellow mouse ».

La feature tient en deux moments :

```
À L'IMPORT (une fois)                                À CHAQUE REQUÊTE
─────────────────────                                ─────────────────
151 descriptions de référence                        « small yellow mouse with red cheeks »
  └─ modèle d'embeddings                               └─ même modèle
       └─ 151 vecteurs, stockés dans SQLite                 └─ 1 vecteur
                                                                 └─ similarité cosinus avec les 151
                                                                      └─ les 5 plus proches
```

**Similarité cosinus :** l'« angle » entre deux vecteurs. 1 = même sens, 0 = sans rapport. C'est un **score relatif** (0,73 ne veut pas dire « 73 % de chances »), qui ne sert qu'à classer.

**Ce que ce n'est pas : un LLM génératif.** Le modèle ne « raisonne » pas et ne génère rien. Il produit des vecteurs, toujours les mêmes pour le même texte : le résultat est **déterministe**. Un LLM n'a servi qu'**une fois, hors ligne**, pour rédiger les descriptions de référence, qui ont ensuite été versionnées.

---

## 4. Architecture

Les mêmes quatre couches que la recherche par nom. Le modèle d'embeddings est derrière un **port**, comme `SimilarityScorer` l'était pour Jaro-Winkler.

| Couche | Ce que la feature y ajoute |
|---|---|
| **domain/** `appearance.py` | `AppearanceDescription` (et son `reference_text`), `AppearanceCandidate`, `AppearanceMatch`, **port `TextEmbedder`**, `validate_description`, `cosine_similarity`, `rank_by_appearance`. En Python pur, sans numpy |
| **domain/** `repositories.py` | `PokemonRepository.list_appearance_candidates()` |
| **use_cases/** `identify_pokemon.py` | `IdentifyPokemon` : valider → vectoriser → classer → charger → remettre dans l'ordre |
| **infrastructure/** | `embeddings.py` (`Model2VecEmbedder`, **seul fichier qui importe model2vec**), `appearance_descriptions.py` (lecture du JSON), tables et import SQLite |
| **api/** | route `/pokemon/identify`, `PokemonIdentificationOut`, erreur 503 si l'index manque |

**Le domaine ne connaît ni model2vec, ni numpy, ni SQLite.** Changer de modèle, ou passer à une API d'embeddings, ne toucherait que `infrastructure/embeddings.py` et l'assemblage dans `api/routes.py`.

### Chemin complet d'une requête

```
Navigateur : « small yellow mouse with red cheeks » + Identify
  └─ GET /api/pokemon/identify?description=…&limit=5        (TanStack Query + openapi-fetch)
       └─ api/routes.py : get_identify_pokemon
       │    └─ read_appearance_model(conn) == configured_model() ?   sinon 503
       └─ use_cases/identify_pokemon.py : IdentifyPokemon.execute()
            ├─ domain : validate_description(...)              (sinon 422)
            ├─ infra  : embedder.embed([description])          (model2vec, ≈ 1 ms)
            ├─ infra  : repository.list_appearance_candidates()  (151 vecteurs)
            ├─ domain : rank_by_appearance(...)                (cosinus, tri, limite)
            └─ infra  : repository.get_many([25, 27, 100, …])  puis remise dans l'ordre
       └─ réponse JSON + Cache-Control: public, max-age=3600
  └─ affichage : carte « Best match: Pikachu » + « Other possibilities »
```

### Stockage

```sql
pokemon_appearance(pokemon_id PRIMARY KEY → pokemon.id, reference_text, embedding BLOB)
appearance_index(model, dimensions)    -- une ligne : le modèle qui a produit les vecteurs
```

Chaque vecteur est stocké en **float32 binaire** (`array('f')`) : 512 × 4 octets = 2 Ko par Pokémon, environ 300 Ko pour les 151. `reference_text` garde le texte exact qui a été vectorisé, pour pouvoir déboguer.

---

## 5. La démarche, étape par étape

### Étape 1 : explorer les options

Quatre familles de solutions ont été comparées avant d'écrire du code :

| Option | Principe | Pourquoi écartée / retenue |
|---|---|---|
| A. Filtres sur les données | utiliser `color` et `shape` de `pokedex.json` | trop pauvre (une couleur, une forme) ; et on a découvert ensuite que `color` est **faux dans 32 cas sur 151** (§ 5, étape 2) |
| B. Dictionnaire de mots-clés | liste de traits par Pokémon, comptage des mots communs | ne comprend pas les synonymes ; gros travail de dictionnaire. Gardée comme **référence sans IA** dans le benchmark |
| C. LLM génératif | envoyer la description à un LLM, qui répond un nom | par API : clé, coût, réseau, non déterministe. **Embarqué** (Ollama, Mistral…) : conteneur de plusieurs Go, lent sans GPU, non déterministe. Disproportionné pour 151 candidats |
| **D. Embeddings** | comparer la description à 151 descriptions de référence | **retenue** : petit modèle embarqué, déterministe, quelques ms, testable |

L'option D garde de l'option B l'idée d'une **référence par Pokémon**, mais remplace la comparaison de mots par une comparaison de sens.

### Étape 2 : construire les descriptions de référence

C'est le vrai travail de la feature. **La qualité de l'identification dépend d'abord de la qualité de ces textes.**

1. **Un prompt** ([`src/fullstack_pokedex/prompts/pokemon_descriptions.md`](../src/fullstack_pokedex/prompts/pokemon_descriptions.md)) demande à un grand LLM, pour chaque Pokémon, trois descriptions courtes :
   - `glance` : ce qu'on remarque en une seconde (5 à 10 mots) ;
   - `detailed` : les traits du plus au moins visible, **avec ce qui le distingue de ses voisins** (12 à 25 mots) ;
   - `everyday` : comme le dirait quelqu'un qui ne connaît pas Pokémon, « looks like a … » (8 à 20 mots) ;
   - plus `confidence` et `notes` (doutes, écarts avec les données).
2. **Pourquoi trois descriptions courtes et pas une longue** : un vecteur résume tout un texte. Un texte long dilue les traits importants. Trois formulations couvrent plusieurs façons de décrire le même Pokémon.
3. **Règles :** uniquement l'apparence (pas de capacités, d'évolution, de « fire type »), **aucun nom de Pokémon**, anglais.
4. **Génération par lots** de 15 à 25, familles d'évolution regroupées (pour que le LLM distingue Charmander de Charmeleon dans la même réponse).
5. **Vérifications automatiques** (`tests/test_appearance_descriptions.py`, 12 tests) : 151 entrées dans l'ordre, longueurs, absence de noms et de vocabulaire de jeu, textes différents entre eux.

**Découverte en chemin :** le générateur a signalé **32 cas où le champ `color` de `pokedex.json` ne correspond pas à ce qu'on voit** (Charmander « red » alors qu'il est orange, Zubat « purple » alors qu'il est bleu…). C'est une raison de plus pour ne pas s'appuyer sur ce champ (option A). Le détail est dans [`data/README.md`](../data/README.md).

### Étape 3 : le benchmark

Avant de choisir un modèle, mesure de 6 modèles et de 6 façons de combiner les trois descriptions, sur 68 requêtes (§ 6). **Décision : `minishlab/potion-base-32M` (model2vec), les trois descriptions réunies en un seul texte.**

### Étape 4 : domaine

`domain/appearance.py`, sans dépendance :
- `AppearanceDescription.reference_text` = `"{glance}. {detailed}. {everyday}"` : la stratégie « textes réunis » retenue par le benchmark est **une règle du domaine**, pas un détail du modèle ;
- `validate_description()` : espaces normalisés, au moins une lettre ou un chiffre, **300 caractères au maximum**, sinon `InvalidSearchQueryError` (la même erreur que pour la recherche par nom, donc une 422) ;
- `cosine_similarity()` avec `math.sumprod` et `math.hypot` : 151 × 512 multiplications, pas besoin de numpy ;
- `rank_by_appearance()` : tri par score décroissant puis par numéro de Pokédex (résultat toujours le même en cas d'égalité) ;
- le port `TextEmbedder` : `embed(texts) -> list[list[float]]`.

### Étape 5 : infrastructure et import

- `Model2VecEmbedder` : charge le modèle, `embed()` renvoie des listes Python (le domaine ne voit pas numpy). Modèle configurable par la variable d'environnement `POKEDEX_EMBEDDING_MODEL` (un nom Hugging Face ou un **dossier local**, pour un déploiement sans réseau).
- `import_appearance()` : refuse clairement une description qui vise un Pokémon inconnu, remplace l'index précédent **en une transaction**, et enregistre le modèle utilisé et la dimension des vecteurs.
- La commande `pokedex-import` prend une option `--descriptions` (par défaut `data/pokemon_descriptions.json`). Si le fichier manque, l'import des Pokémon se fait quand même, avec un message : la recherche par nom ne dépend pas de cette feature.
- Corrigé au passage : l'import ne fermait pas toujours sa connexion SQLite (`contextlib.closing`).

### Étape 6 : cas d'usage

`IdentifyPokemon.execute(IdentifyPokemonQuery(description, limit))`, sur le même modèle que `SuggestPokemon` :
1. **valider avant tout calcul** : limite entre 1 et 10, description valide ;
2. vectoriser la description ;
3. récupérer les 151 vecteurs et classer ;
4. charger **seulement** les Pokémon retenus ;
5. **les remettre dans l'ordre du classement** (`get_many` ne garantit aucun ordre).

### Étape 7 : API

- `GET /pokemon/identify`, déclarée avant `/pokemon/{ref}`.
- **Le modèle est chargé une seule fois par processus** (`@cache` sur `get_text_embedder`), au premier appel : la première requête prend environ 0,4 s, les suivantes environ 7 ms.
- **Garde-fou :** des vecteurs produits par deux modèles différents ne sont **pas comparables**. Si l'index est absent, ou construit avec un autre modèle que celui configuré, l'API répond **503** avec la commande à lancer, au lieu de renvoyer des résultats absurdes.

### Étape 8 : frontend

- Section « By appearance » sous la recherche par nom, dans `features/identify/`.
- La carte et le badge de type, utilisés par les deux recherches, ont été déplacés dans `src/shared/`.
- Types régénérés depuis l'OpenAPI (`pnpm gen:api`) : `PokemonIdentificationOut` vient du backend.
- Choix d'interface détaillés au § 8.6.

---

## 6. Le benchmark

**Script :** `benchmarks/appearance_embeddings.py`. **Requêtes :** `benchmarks/appearance_queries.json`. **Résultats bruts :** `benchmarks/results/appearance_embeddings.json`.

### Protocole

- **68 requêtes** rédigées comme un utilisateur les taperait, **sans reprendre** le texte des descriptions de référence, réparties en 4 catégories :

| Catégorie | Nombre | Exemple |
|---|---|---|
| `famous` | 20 | « orange lizard with a flame on its tail » → Charmander |
| `obscure` | 29 | Pokémon moins connus |
| `sibling` | 11 | doit être distingué d'un Pokémon qui lui ressemble (Voltorb / Electrode…) |
| `misremembered` | 8 | description vague, ou couleur différente du champ `color` |

- **Mesures :** `hit@1` (le bon Pokémon est 1er), `hit@3` (dans les 3 premiers), `hit@5`.
- **Stratégies** pour combiner les 3 descriptions : `joined` (réunies en un texte, un vecteur), `max-of-3` (meilleure des trois similarités), `mean-of-3` (moyenne), et chaque description seule.
- **Référence sans IA :** proportion des mots de la requête présents dans les descriptions.

### Résultats (stratégie `joined`, sauf la référence)

| Modèle | Bibliothèque | hit@1 | hit@3 | Taille | Chargement |
|---|---|---|---|---|---|
| **potion-base-32M** | **model2vec** | **95,6 %** | **100 %** | **131 Mo** | 3,6 s* |
| potion-base-8M | model2vec | 92,6 % | 100 % | 31 Mo | 1,9 s* |
| potion-retrieval-32M | model2vec | 94,1 % | 98,5 % | 131 Mo | 4,8 s* |
| all-MiniLM-L6-v2 | sentence-transformers (PyTorch) | 95,6 % | 100 % | 92 Mo + PyTorch | 7,9 s |
| bge-small-en-v1.5 | sentence-transformers (PyTorch) | 91,2 % | 98,5 % | 135 Mo + PyTorch | 5,7 s |
| all-mpnet-base-v2 | sentence-transformers (PyTorch) | 95,6 % | 100 % | 439 Mo + PyTorch | 12,9 s |
| *mots communs (sans IA)* | — | *83,8 %* | *97,1 %* | — | — |

\* temps mesurés dans l'environnement du benchmark ; dans l'application, le chargement de potion-base-32M prend environ 0,4 s.

### Les stratégies (potion-base-32M)

| Stratégie | hit@1 | hit@3 |
|---|---|---|
| **joined** | **95,6 %** | **100 %** |
| mean-of-3 | 91,2 % | 100 % |
| max-of-3 | 88,2 % | 98,5 % |
| `glance` seul | 88,2 % | 98,5 % |
| `everyday` seul | 80,9 % | 98,5 % |
| `detailed` seul | 67,6 % | 92,6 % |

**À noter :** l'intuition de départ était `max-of-3`. **La mesure l'a contredite** : réunir les trois textes fonctionne mieux. C'est ce qui est implémenté.

### Ce qu'on en retient

- Le meilleur petit modèle **sans PyTorch** fait aussi bien que les modèles PyTorch, pour une fraction du poids : PyTorch seul ajoute environ 780 Mo en version CPU.
- L'IA apporte surtout sur les descriptions **approximatives** : la référence sans IA tombe à 50 % en 1re position sur `misremembered`.
- **Prudence :** la référence sans IA atteint déjà 84 %. Le jeu de requêtes est probablement **trop facile**, et il a été écrit par la même personne que les descriptions. Il faudra l'enrichir avec de vraies saisies d'utilisateurs (§ 11).

---

## 7. Le contrat d'API

```
GET /pokemon/identify?description=<texte>&limit=<1..10, défaut 5>
```

```json
[
  {
    "id": 25,
    "name": "pikachu",
    "display_name": "Pikachu",
    "sprite": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png",
    "types": ["electric"],
    "genus": "Mouse Pokémon",
    "score": 0.73
  }
]
```

| Champ | Signification |
|---|---|
| `score` | similarité cosinus entre la description et la référence du Pokémon. **Sert à classer, ce n'est pas une probabilité** |
| autres champs | identiques à `/pokemon/suggest` (sans `match`) |

| Cas | Réponse |
|---|---|
| résultats | `200`, triés du plus au moins proche |
| `description` absente, vide, ou de plus de 1 000 caractères ; `limit` hors de 1..10 | `422`, `detail` en **liste** (validation FastAPI) |
| description sans lettre ni chiffre (`!!!`), ou de plus de 300 caractères | `422`, `detail` en **texte** (règle métier) |
| index d'apparence absent, ou construit avec un autre modèle | `503`, `detail` indique la commande à lancer |

---

## 8. Les décisions et leurs raisons

### 8.1 Embeddings plutôt qu'un LLM génératif

Pour **choisir parmi 151 candidats connus**, il suffit de mesurer une proximité. Un LLM génératif répondrait en une seule fois, mais il est lourd, lent sans GPU, non déterministe (difficile à tester) et peut inventer un nom. L'IA générative reste utile **là où elle est forte : rédiger les références, une fois, avec une relecture humaine.**

### 8.2 model2vec plutôt que sentence-transformers ou fastembed

- **sentence-transformers** demande PyTorch : environ 780 Mo pour la version CPU, pour une qualité égale sur notre jeu de requêtes.
- **fastembed / onnxruntime** : pas disponible pour Python 3.15, la version du projet.
- **model2vec** : des embeddings « statiques » (un vecteur par mot, puis une moyenne), sans réseau de neurones à l'exécution. Il dépend de numpy, tokenizers et safetensors, pas de PyTorch. Le calcul d'un vecteur prend une fraction de milliseconde.

### 8.3 potion-base-32M plutôt que potion-base-8M

Le 8M est 4 fois plus léger (31 Mo) et perd 2 requêtes sur 68 en 1re position. **Le choix a été fait pour la qualité.** Si la taille du conteneur devenait un sujet, le 8M est une alternative mesurée : il suffit de changer `POKEDEX_EMBEDDING_MODEL` et de relancer l'import.

### 8.4 Vecteurs calculés à l'import, stockés dans SQLite

- **Calculés à l'import** : les références ne changent qu'avec le fichier `data/`. Les recalculer à chaque démarrage ralentirait le démarrage sans raison.
- **Dans SQLite, pas dans une base vectorielle** : 151 vecteurs, une comparaison complète prend environ 1 ms en Python. Une base vectorielle (ou l'extension `sqlite-vec`) serait une dépendance de plus pour rien.
- **Le nom du modèle est enregistré avec l'index**, et vérifié à chaque requête (503 sinon). Sans ce garde-fou, changer de modèle sans relancer l'import donnerait des résultats faux sans aucune erreur.

### 8.5 Le cosinus dans le domaine, en Python pur

Le classement est une **règle métier** (« le plus proche d'abord, puis le numéro de Pokédex »). Il est dans le domaine, testable sans modèle ni base. numpy serait plus rapide, mais pour 151 vecteurs la différence ne se voit pas, et le domaine resterait dépendant d'une bibliothèque.

### 8.6 Frontend : simple, et sans faire croire à une certitude

| Choix | Pourquoi |
|---|---|
| **Recherche à la validation** (bouton ou Entrée), pas pendant la frappe | une description est une phrase, pas un début de nom ; des résultats sur une phrase incomplète ne voudraient rien dire |
| **Score non affiché** | « 0,73 » serait lu comme « 73 % de chances ». L'ordre suffit |
| Meilleur résultat en **grande carte**, les autres en **liste courte** | la carte sert de confirmation ; la liste rappelle que la description peut être ambiguë |
| Champ limité à **300 caractères**, bouton désactivé sans lettre ni chiffre | mêmes règles que le backend : évite des 422 prévisibles |
| Pas de mention de langue dans le libellé | toute l'interface est en anglais, comme les données |
| Message dédié pour la **503** | « Search by appearance is unavailable right now » : l'utilisateur n'a pas à connaître l'index |

Comme pour la recherche par nom, **le front ne contient aucune logique métier** : il affiche ce que l'API renvoie, dans l'ordre.

---

## 9. Stratégie de test

| Couche | Fichiers | Approche |
|---|---|---|
| données | `test_appearance_descriptions.py` | forme des 151 descriptions (structure, longueurs, pas de noms, textes distincts) |
| domaine | `test_appearance.py` | tests purs : validation, cosinus (vecteurs nuls, tailles différentes), classement et égalités |
| cas d'usage | `test_identify_pokemon.py` | **repository et embedder remplacés par des mocks** : validation avant tout calcul, limite, ordre conservé, Pokémon manquants ignorés |
| infrastructure | `test_sqlite_importer.py`, `test_sqlite_repositories.py` | vraie SQLite en mémoire, **faux modèle déterministe** ; aller-retour des vecteurs float32 ; index remplacé à chaque import ; base créée avant cette feature |
| API | `test_api.py` | cas d'usage remplacé par un mock ; 422 ; **503** si l'index manque |
| bout en bout | `test_app.py` | vraie app, vraie base de test, faux modèle ; 503 si l'index vient d'un autre modèle |
| **qualité réelle** | `test_appearance_quality.py` | **vrai modèle** sur les 68 requêtes ; échoue sous 92 % en 1re position ou 97 % dans le top 3 |
| frontend | `features/identify/AppearanceSearch.test.tsx` | du point de vue de l'utilisateur, API simulée par MSW : carte + liste, envoi à la validation seulement, erreurs 422/503/500/réseau |

**Le faux modèle (`FakeEmbedder`, dans `tests/factories.py`)** : chaque mot est haché dans un vecteur de 32 nombres. Deux textes qui partagent des mots ont donc des vecteurs proches. Il respecte le port `TextEmbedder`, ne télécharge rien et répond toujours la même chose : les tests restent rapides et fiables.

**Le test de qualité ne télécharge jamais le modèle.** Il est **ignoré** si le modèle n'est pas déjà sur la machine (premier `pokedex-import`), et force le mode hors ligne de Hugging Face. Son rôle : si quelqu'un modifie une description et fait baisser la qualité, il échoue en listant les requêtes ratées.

---

## 10. Limites connues et choix assumés

| Limite | Exemple / détail | Pourquoi / piste |
|---|---|---|
| **Jeu d'évaluation probablement trop facile** | la méthode sans IA atteint déjà 84 % | à enrichir avec de vraies saisies |
| Descriptions **pas encore relues** par un humain | checklist dans `data/README.md` (Venomoth, paires ressemblantes, 32 écarts de couleur) | les tests vérifient la forme, pas l'exactitude visuelle |
| Paires très ressemblantes | Voltorb / Electrode, Nidoqueen / Nidoking | dépend de la qualité de la description `detailed` |
| Descriptions imagées ratées | « walking pile of blue noodles with legs » ne trouve pas Tangela dans le top 3 avec `max-of-3` | les métaphores éloignées restent difficiles pour un petit modèle |
| Négations probablement mal comprises | « a bird **without** wings » risque d'être proche de « a bird with wings » | limite connue des embeddings en général ; **non mesurée** sur ce projet |
| Anglais uniquement | — | périmètre de la feature |
| Toujours une réponse | même une description absurde renvoie 5 Pokémon | pas de seuil de score minimum ; à calibrer avec de vraies saisies si besoin |
| Premier appel plus lent | ≈ 0,4 s pour charger le modèle | possible de le charger au démarrage de l'API |
| Mémoire | le modèle reste chargé (≈ 130 Mo) par processus | acceptable pour un seul processus |
| Nouvelles dépendances | model2vec, numpy, tokenizers, safetensors… | prix d'une identification par le sens |
| Modèle téléchargé au premier import | depuis Hugging Face | pour un conteneur sans réseau : télécharger une fois et pointer `POKEDEX_EMBEDDING_MODEL` vers le dossier |
| Deux formats d'erreur 422 | comme pour la recherche par nom | le front n'affiche qu'un message selon le code HTTP |

---

## 11. Prochaines étapes

1. **Relire les descriptions** (checklist de `data/README.md`) et compléter leur provenance (modèle utilisé, corrections manuelles).
2. **Enrichir le jeu d'évaluation** avec des descriptions écrites par d'autres personnes, puis relancer le benchmark et ajuster les seuils du test de qualité Les signalements « I didn't find my Pokémon » ([`feature-signalement.md`](feature-signalement.md)) sont enregistrés dans ce but.
3. **Charger le modèle au démarrage** de l'API (événement `lifespan` de FastAPI) pour supprimer la latence du premier appel.
4. **Seuil de score minimum**, pour répondre « je ne sais pas » à une description qui ne ressemble à rien, si les vraies saisies le justifient.
5. **Relier les résultats à la future fiche détaillée** (`/pokemon/{id}`), comme pour la recherche par nom.

---

## 12. Carte des fichiers

### Données et benchmark

| Fichier | Rôle |
|---|---|
| `data/pokemon_descriptions.json` | **source de vérité** : 151 descriptions de référence |
| `src/fullstack_pokedex/prompts/pokemon_descriptions.md` | prompt qui a servi à les générer |
| `data/README.md` | format, provenance, relecture, comment modifier |
| `benchmarks/appearance_queries.json` | 68 requêtes d'évaluation |
| `benchmarks/appearance_embeddings.py` | script du benchmark (environnement séparé) |
| `benchmarks/results/appearance_embeddings.json` | résultats bruts |

### Backend : `src/fullstack_pokedex/`

| Fichier | Rôle |
|---|---|
| `domain/appearance.py` | **cœur de la feature** : texte de référence, port `TextEmbedder`, validation, cosinus, classement |
| `domain/repositories.py` | `list_appearance_candidates()` |
| `use_cases/identify_pokemon.py` | cas d'usage `IdentifyPokemon` |
| `infrastructure/embeddings.py` | `Model2VecEmbedder`, `configured_model()`, `POKEDEX_EMBEDDING_MODEL` |
| `infrastructure/appearance_descriptions.py` | lecture de `data/pokemon_descriptions.json` |
| `infrastructure/sqlite/schema.sql` | tables `pokemon_appearance` et `appearance_index` |
| `infrastructure/sqlite/importer.py` | `import_appearance()`, option `--descriptions` |
| `infrastructure/sqlite/repositories.py` | `encode_vector` / `decode_vector`, `read_appearance_model()` |
| `api/routes.py` | route `/pokemon/identify`, chargement unique du modèle, vérification de l'index (503) |
| `api/schemas.py` | `PokemonIdentificationOut` |
| `api/app.py` | conversion de `AppearanceIndexUnavailableError` en 503 |

### Tests : `tests/`

`test_appearance.py`, `test_identify_pokemon.py`, `test_appearance_descriptions.py`, `test_appearance_quality.py`, plus des ajouts dans `test_sqlite_importer.py`, `test_sqlite_repositories.py`, `test_api.py` et `test_app.py`. `FakeEmbedder` est dans `factories.py`, les fixtures `mini_descriptions` et `appearance_conn` dans `conftest.py`.

### Frontend : `frontend/src/`

| Fichier | Rôle |
|---|---|
| `features/identify/useIdentification.ts` | appel à l'API (TanStack Query), messages d'erreur, limites |
| `features/identify/AppearanceSearch.tsx` | formulaire, carte du meilleur résultat, liste des autres |
| `features/identify/AppearanceSearch.test.tsx` | tests de la feature |
| `shared/PokemonCard.tsx`, `shared/TypeBadge.tsx`, `shared/pokemon.ts` | éléments communs aux deux recherches |
| `test/handlers.ts` | ajout de la route `/api/pokemon/identify` simulée |
