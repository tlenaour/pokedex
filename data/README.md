# `data/`: données de référence du projet

Contrairement à `pokedex.json` (données brutes, non versionnées), les fichiers de ce dossier sont **versionnés** et **maintenus à la main**.

| Fichier | Contenu |
|---|---|
| [`pokemon_descriptions.json`](pokemon_descriptions.json) | descriptions d'apparence de référence des 151 Pokémon |
| [`tags_llm.json`](tags_llm.json) | tags d'effets des 164 attaques et 114 talents (`immune:ground`, `inflicts:sleep`…) |

---

## `pokemon_descriptions.json`

### À quoi il sert

Il alimente la feature « **identifier un Pokémon à partir d'une description de son apparence** » : `GET /pokemon/identify?description=…`. Un utilisateur tape par exemple « small yellow mouse with red cheeks ». L'application compare le **sens** de cette phrase à celui de ces descriptions de référence, et propose les Pokémon les plus proches.

Fonctionnement :
- **à l'import** (`uv run pokedex-import`), les trois descriptions de chaque Pokémon sont réunies en un seul texte (`AppearanceDescription.reference_text`), puis transformées en vecteur par le modèle d'embeddings `minishlab/potion-base-32M` (model2vec). Les vecteurs sont stockés dans la table `pokemon_appearance`, avec le nom du modèle dans `appearance_index` ;
- **à chaque requête**, la description de l'utilisateur est transformée en vecteur par le même modèle, puis les Pokémon sont classés par similarité cosinus (`domain/appearance.py`).

Le choix du modèle et de la stratégie « textes réunis » est mesuré dans `benchmarks/appearance_embeddings.py`, sur le jeu d'évaluation `benchmarks/appearance_queries.json`. Un test (`tests/test_appearance_quality.py`) vérifie avec le vrai modèle que la qualité ne baisse pas.

**Après toute modification de ce fichier, relancer `uv run pokedex-import`** pour recalculer les vecteurs.

**C'est la source de vérité de la feature :** la qualité de l'identification dépend directement de la qualité de ces textes. Si un Pokémon est mal retrouvé, on **améliore sa description** ; on ne touche ni au code ni au modèle.

> **Périmètre : anglais uniquement**, comme le reste des données.

### Format

Un tableau JSON de 151 objets, triés par numéro de Pokédex :

```json
{
  "id": 1,
  "name": "bulbasaur",
  "glance": "squat green four-legged creature with bulb on back",
  "detailed": "squat blue-green four-legged toad-like body with darker green patches; large closed green plant bulb on its back; red eyes; pointed ears; no flower, no leaves",
  "everyday": "looks like a green frog or little dinosaur carrying a big onion on its back",
  "confidence": "high",
  "notes": ""
}
```

| Champ | Rôle | Règle |
|---|---|---|
| `id`, `name` | identifient le Pokémon | identiques à `pokedex.json` (`name` est le slug, par exemple `mr-mime`) |
| `glance` | ce qu'on remarque en une seconde | 5 à 10 mots |
| `detailed` | les traits visuels du plus au moins visible, **avec ce qui le distingue de ses voisins** | 12 à 25 mots |
| `everyday` | comme le décrirait quelqu'un qui ne connaît pas les Pokémon (« looks like a … ») | 8 à 20 mots |
| `confidence` | confiance du générateur | `high`, `medium` ou `low` |
| `notes` | remarque du générateur (écart avec les données, doute) | vide si rien à signaler |

**Pourquoi trois descriptions courtes plutôt qu'une longue :** un embedding résume tout un texte en un seul vecteur. Un texte long « dilue » les traits visuels, et peut être tronqué sans avertissement par le modèle. Trois formulations courtes couvrent plus de façons de décrire le Pokémon ; à l'usage, on garde la meilleure similarité des trois.

**Règles communes aux trois textes :** uniquement l'apparence (pas de capacités, de comportement, d'évolution, de vocabulaire de jeu comme « fire type »), **aucun nom de Pokémon**, une seule ligne, pas de point final.

### Origine

| | |
|---|---|
| Généré par | un LLM, **une seule fois, hors ligne** ; à l'exécution, aucune IA générative n'intervient |
| Modèle utilisé | **À COMPLÉTER** (nom et version exacts) |
| Date de génération | 2026-11-11 (date du fichier) |
| Prompt | [`src/fullstack_pokedex/prompts/pokemon_descriptions.md`](../src/fullstack_pokedex/prompts/pokemon_descriptions.md) |
| Données fournies au modèle | depuis `pokedex.json` : `id`, `name`, `color`, `shape`, hauteur (en m), `genus`, par lots de 15 à 25 avec les familles d'évolution regroupées |
| Modifications manuelles | **À COMPLÉTER** : liste des Pokémon corrigés à la main, ou « aucune » |

Le générateur doit être **un grand modèle** : il faut connaître précisément l'apparence des 151 Pokémon. C'est un coût ponctuel, pas un coût par requête.

### État de la relecture

**Vérifications automatiques** : [`tests/test_appearance_descriptions.py`](../tests/test_appearance_descriptions.py), lancés avec `uv run pytest`. Ils vérifient la structure (151 entrées dans l'ordre, champs, types), la cohérence avec les données, les longueurs, l'absence de nom de Pokémon et de vocabulaire de jeu, le format, et que les descriptions sont différentes entre elles et d'un Pokémon à l'autre. **Ils vérifient la forme, pas l'exactitude visuelle** : celle-ci demande une relecture humaine.

**Relecture humaine**, à cocher au fur et à mesure (**À COMPLÉTER** : qui, quand) :

- [ ] **Venomoth** (#49), seule entrée à `confidence: medium` : le générateur doute des motifs des ailes et de la couleur des yeux. À comparer avec le sprite.
- [ ] **Paires très ressemblantes**, que les embeddings risquent de confondre. Vérifier que la description `detailed` contient bien ce qui les distingue :
  - [ ] Voltorb / Electrode (inversion rouge/blanc, bouche) : **la paire la plus à risque**
  - [ ] Nidoqueen / Nidoking
  - [ ] Clefairy / Clefable
  - [ ] Poliwhirl / Poliwrath
  - [ ] Nidoran♂ / Nidorino
  - [ ] Pidgeotto / Pidgeot
  - [ ] Bulbasaur / Ivysaur, Squirtle / Wartortle / Blastoise, Charmander / Charmeleon
  - [ ] Machoke / Machamp, Kadabra / Alakazam
- [ ] **Les 32 écarts de couleur signalés** dans `notes` (voir ci-dessous) : confirmer la couleur réellement visible.
- [ ] Un parcours rapide de toutes les autres entrées, en comparant avec le sprite.

### Ce que le fichier a révélé sur les données

Le générateur a signalé **32 cas où le champ `color` de `pokedex.json` ne correspond pas à la couleur réellement visible**, plus une note de doute (Venomoth). Quelques exemples :

| Pokémon | `color` dans les données | Couleur visible |
|---|---|---|
| Charmander, Charizard | red | orange |
| Raichu | yellow | orange |
| Abra, Kadabra, Alakazam | brown | jaune (seulement les parties « armure » sont brunes) |
| Bellsprout, Weepinbell, Victreebel | green | jaune (seulement les feuilles sont vertes) |
| Zubat, Golbat | purple | bleu (seulement la membrane des ailes est violette) |
| Snorlax | black | bleu-vert foncé avec un ventre crème |

Le champ `color` donne une couleur « officielle » unique, souvent éloignée de ce que les gens retiennent. **Il est peu fiable pour décrire l'apparence.** C'est l'une des raisons du choix des embeddings sur des descriptions relues, plutôt que d'un classement à partir des catégories `color` et `shape`.

Autre point : les descriptions suivent les **designs actuels** (par exemple Jynx avec le visage violet), cohérents avec les données de PokéAPI, qui sont actuelles elles aussi.

### Modifier le fichier

1. **Corriger à la main** la ou les entrées concernées, en respectant les règles du tableau ci-dessus.
2. Lancer `uv run pytest tests/test_appearance_descriptions.py` : toutes les erreurs de forme sont listées en une fois.
3. Noter la modification dans « Modifications manuelles » ci-dessus.
4. Relancer `uv run pokedex-import` (recalcul des vecteurs), puis `uv run pytest tests/test_appearance_quality.py` pour vérifier que la qualité ne baisse pas.

**Ne pas régénérer le fichier entièrement** sans refaire toute la relecture : les corrections manuelles seraient perdues. Pour ajouter ou refaire quelques Pokémon, relancer le prompt **sur ces seuls Pokémon** (avec leur famille d'évolution), puis relire.

---

## `tags_llm.json`

**Rôle :** les effets des attaques et des talents, dans un vocabulaire fermé (`relation:effet`), chacun avec une preuve (`evidence`, extrait exact du texte). Ils sont importés dans la table `effect_tag` par `uv run pokedex-import` (option `--tags`). Ils sont utilisés par la feature « Préparer un combat » : menaces, parades, pièges et statuts (voir [`docs/feature-preparer-un-combat.md`](../docs/feature-preparer-un-combat.md)).

**Le champ `comment` n'est pas importé, ni utilisé :** seuls les tags comptent. Une condition qu'on veut voir prise en compte doit devenir un tag.

**Origine :** des étiquettes écrites par un LLM selon le prompt [`src/fullstack_pokedex/prompts/tag_effects.md`](../src/fullstack_pokedex/prompts/tag_effects.md), assemblées et vérifiées par [`scripts/build_tags.py`](../scripts/build_tags.py), qui réécrit ce fichier. On corrige une étiquette dans le script, pas dans le JSON.

**Après toute modification, relancer `uv run pokedex-import`.**

**À relire :** les 9 entrées en `confidence: low` (par exemple `shield-dust`, `serene-grace`, `compound-eyes`).
