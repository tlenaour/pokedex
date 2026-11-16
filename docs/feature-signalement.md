# Feature : « I didn't find my Pokémon »

> **Pour qui :** une personne qui arrive sur le projet et veut comprendre **ce qui a été construit et pourquoi**.
>
> **Contexte :** cette feature s'appuie sur les deux recherches déjà en place, [par le nom](feature-recherche-par-nom.md) et [par l'apparence](feature-recherche-par-apparence.md). L'architecture et la stack y sont expliquées et ne sont pas répétées ici.
>
> **État au 2026-11-12 :** backend et frontend livrés. 397 tests backend (couverture 99 %) et 35 tests frontend passent.

---

## Sommaire

1. [La feature en une page](#1-la-feature-en-une-page)
2. [Pourquoi : l'objectif à terme](#2-pourquoi--lobjectif-à-terme)
3. [Ce que voit l'utilisateur](#3-ce-que-voit-lutilisateur)
4. [Ce qui est enregistré, et où](#4-ce-qui-est-enregistré-et-où)
5. [Architecture](#5-architecture)
6. [Le contrat d'API](#6-le-contrat-dapi)
7. [Les décisions et leurs raisons](#7-les-décisions-et-leurs-raisons)
8. [Stratégie de test](#8-stratégie-de-test)
9. [Limites connues et choix assumés](#9-limites-connues-et-choix-assumés)
10. [Prochaines étapes](#10-prochaines-étapes)
11. [Carte des fichiers](#11-carte-des-fichiers)

---

## 1. La feature en une page

**Une feature de qualité produit :** quand une recherche ne montre pas le Pokémon voulu, l'utilisateur le signale **en un clic, directement dans les résultats**. Le signalement est enregistré en base avec la recherche et les Pokémon qui étaient affichés.

| Besoin | Réponse apportée |
|---|---|
| savoir **quelles recherches échouent** | chaque signalement garde la saisie exacte et le type de recherche (`name` ou `appearance`) |
| savoir **ce que l'application a proposé** | les ids des Pokémon affichés, dans l'ordre |
| ne pas gêner l'utilisateur | un clic, sans formulaire, sans quitter les résultats |
| ne jamais perdre ces données | une base séparée, `feedback.db`, que `pokedex-import` ne touche pas |

---

## 2. Pourquoi : l'objectif à terme

Les deux recherches ont des seuils et des choix qui ont été **mesurés sur des cas écrits à la main** :
- la tolérance aux fautes de la recherche par nom (benchmark de 1 092 cas générés) ;
- la recherche par apparence (68 requêtes écrites par la même personne que les descriptions de référence, **probablement trop faciles** : la méthode sans IA atteint déjà 84 %).

**Il manque de vraies saisies d'utilisateurs, et en particulier celles qui échouent.** Les signalements fournissent précisément ça.

**À terme**, le circuit visé est le suivant :

```
signalements (feedback.db)
  └─ relecture humaine : quel Pokémon l'utilisateur cherchait-il ?   (« expected », à renseigner à la main)
       └─ ajout des cas retenus au jeu d'évaluation
            ├─ benchmarks/appearance_queries.json   → benchmark + test de qualité de la recherche par apparence
            └─ cas réels pour recalibrer la tolérance aux fautes de la recherche par nom
```

**Pour l'instant, on se contente d'enregistrer les signalements.** Il n'y a ni export, ni écran de consultation, ni lien automatique avec le jeu d'évaluation. On les consulte directement en SQL :

```bash
sqlite3 feedback.db "SELECT created_at, kind, query, shown_ids FROM missing_result_report ORDER BY id DESC LIMIT 20"
```

**Le Pokémon attendu n'est volontairement pas demandé à l'utilisateur.** S'il le connaissait, il l'aurait trouvé, surtout avec la recherche par nom. On l'indiquera à la main lors de la relecture.

---

## 3. Ce que voit l'utilisateur

```
Par le nom (liste déroulante)            Par l'apparence (sous les résultats)
┌────────────────────────────────┐       ┌─ Best match: Pikachu ────────────────┐
│ [img] Charmander   #004 …      │       └──────────────────────────────────────┘
│ [img] Charmeleon   #005 …      │       Other possibilities
│ [img] Chansey      #113 …      │        Sandshrew · Voltorb · …
│ I didn't find my Pokémon       │       Didn't find your Pokémon? Report
└────────────────────────────────┘
```

**Par le nom :** une dernière ligne dans la liste déroulante.
- On l'atteint **au clavier** (↓ puis Entrée) ou à la souris, comme une suggestion.
- Elle apparaît **aussi quand il n'y a aucun résultat** : la liste s'ouvre alors avec cette seule ligne. C'est le cas le plus utile à connaître.
- La choisir **ne remplace pas le texte tapé** et ne sélectionne aucun Pokémon.
- Elle devient « Sending… », puis « Thanks, noted. ». En cas d'échec : « Could not send the report. Retry ».

**Par l'apparence :** une ligne « Didn't find your Pokémon? **Report** » sous les résultats, ou sous « No Pokémon found ». Elle devient « Thanks, noted. ». En cas d'échec, un bouton « Retry » apparaît.

**Dans les deux cas :**
- **un seul signalement par recherche** ; la ligne revient à son état de départ à la recherche suivante ;
- **pas de ligne de signalement si la recherche elle-même a échoué** (erreur, API injoignable, index absent) : il n'y aurait rien d'utile à enregistrer.

---

## 4. Ce qui est enregistré, et où

```sql
-- feedback.db
CREATE TABLE IF NOT EXISTS missing_result_report (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('name', 'appearance')),
    query       TEXT NOT NULL,                              -- saisie, espaces normalisés
    shown_ids   TEXT NOT NULL,                              -- liste JSON, ordre d'affichage : [29, 30]
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))     -- UTC
);
```

**Rien d'autre :** ni IP, ni identifiant d'utilisateur, ni navigateur.

### Pourquoi une base séparée

| | `pokedex.db` | `feedback.db` |
|---|---|---|
| contenu | données de référence | données des utilisateurs |
| reconstructible | **oui**, depuis `pokedex.json` | **non** |
| `pokedex-import` | supprime et recrée toutes les tables | **n'y touche pas** |
| accès par l'API | lecture seule | lecture et écriture |
| schéma | `DROP` puis `CREATE` | `CREATE TABLE IF NOT EXISTS`, **jamais de `DROP`** |

Si les signalements étaient dans `pokedex.db`, le prochain `pokedex-import` les effacerait.

**Emplacement :** à côté de `pokedex.db` par défaut, ou à l'endroit indiqué par la variable d'environnement `POKEDEX_FEEDBACK_DB`. La base et sa table sont créées au démarrage de l'API si elles n'existent pas. Elle est en mode WAL, pour qu'une écriture ne bloque pas les lectures. `*.db`, `*.db-wal` et `*.db-shm` sont ignorés par git.

---

## 5. Architecture

Mêmes couches que les deux recherches. C'est **la première écriture** de l'application.

| Couche | Fichier | Contenu |
|---|---|---|
| **domain/** | `feedback.py` | `SearchKind`, `MissingResultReport`, `validate_report` (saisie non vide et de 300 caractères au plus, 10 Pokémon au plus, sans doublon) |
| **domain/** | `repositories.py` | **port `FeedbackRepository`** : `add(report) -> int` |
| **domain/** | `errors.py` | `InvalidReportError` (→ 422) |
| **use_cases/** | `report_missing_result.py` | `ReportMissingResult` : valider → **vérifier que les Pokémon affichés existent** → enregistrer |
| **infrastructure/** | `sqlite/feedback.py`, `sqlite/feedback_schema.sql` | `init_feedback_db`, `connect_feedback_db`, `SqliteFeedbackRepository` |
| **api/** | `routes.py`, `schemas.py`, `app.py` | `POST /feedback/missing-result`, `MissingResultReportIn`, `ReportCreatedOut`, création de `feedback.db` au démarrage |

Le cas d'usage utilise **deux repositories** : `FeedbackRepository` pour écrire, `PokemonRepository` pour vérifier les ids. Il ne sait pas qu'ils sont dans deux bases différentes : c'est l'assemblage dans `api/routes.py` qui le décide.

### Chemin d'un signalement

```
Navigateur : clic sur « I didn't find my Pokémon » (recherche « nido », 2 Pokémon affichés)
  └─ POST /api/feedback/missing-result  { kind: "name", query: "nido", shown_ids: [29, 30] }   (useMutation)
       └─ api/routes.py : report_missing_result      schéma Pydantic (422 si invalide)
            └─ use_cases/report_missing_result.py : ReportMissingResult.execute()
                 ├─ domain : validate_report(...)                      (sinon 422)
                 ├─ infra  : pokemon.get_many([29, 30])  → pokedex.db   (ids inconnus : 422)
                 └─ infra  : feedback.add(report)        → feedback.db
       └─ 201 { "id": 7 }
  └─ la ligne affiche « Thanks, noted. »
```

---

## 6. Le contrat d'API

```
POST /feedback/missing-result
Content-Type: application/json

{ "kind": "appearance", "query": "walking pile of blue noodles", "shown_ids": [7, 12, 60] }

→ 201 { "id": 42 }
```

| Champ | Règle |
|---|---|
| `kind` | `name` ou `appearance` |
| `query` | la saisie qui a produit les résultats ; 1 000 caractères au plus à l'entrée de l'API, **300 après normalisation des espaces** (règle métier) |
| `shown_ids` | ids des Pokémon affichés, dans l'ordre ; **peut être vide** (aucun résultat) ; 10 au plus, sans doublon, tous existants |

| Cas | Réponse |
|---|---|
| enregistré | `201`, avec l'id du signalement |
| corps invalide (champ manquant, `kind` inconnu, mauvais types, trop long) | `422`, `detail` en **liste** (validation FastAPI) |
| saisie vide après normalisation, doublon, id inconnu | `422`, `detail` en **texte** (règle métier) |

Pas d'en-tête `Cache-Control` : le middleware de cache ne s'applique qu'aux GET.

---

## 7. Les décisions et leurs raisons

### 7.1 Dans les résultats, en un clic, sans formulaire

Le signalement se fait **au moment où l'on constate l'échec**, sans changer d'écran. On a écarté un formulaire « Lequel cherchiez-vous ? » : l'utilisateur ne connaît pas la réponse, sinon il aurait trouvé son Pokémon. Un clic de plus aurait surtout fait baisser le nombre de signalements.

### 7.2 Enregistrer la liste affichée, pas seulement la saisie

Sans la liste, on ne peut pas rejouer le cas : la recherche aura peut-être changé entre-temps. Avec la liste, on sait ce que l'application proposait **au moment du signalement**.

Pour la recherche par nom, **la ligne de signalement n'apparaît qu'une fois que l'API a répondu pour la recherche en cours**. La liste change pendant la frappe, et le signalement doit porter sur ce qui est réellement à l'écran. Le front envoie donc la recherche envoyée à l'API (après les 200 ms d'attente) et les ids qu'elle a renvoyés, sans nouvelle requête.

### 7.3 Vérifier que les Pokémon affichés existent

Ça coûte un `SELECT` sur au plus 10 ids. En échange, on n'enregistre pas de données incohérentes, qui seraient inutilisables le jour où on relira les signalements. La vérification est dans le **cas d'usage**, parce qu'une clé étrangère entre deux bases SQLite est impossible.

### 7.4 La date posée par la base

`DEFAULT (datetime('now'))`, en UTC. Le domaine n'a pas besoin de la date. On évite ainsi d'injecter une horloge pour la tester.

### 7.5 Downshift : une ligne d'action dans la liste

La ligne « I didn't find my Pokémon » est **un élément de la liste Downshift** comme les autres. Elle profite donc gratuitement du clavier et de l'accessibilité. Trois réglages la distinguent d'un Pokémon :
- un **`stateReducer`** : la choisir ne remplace pas le texte tapé et ne ferme pas la liste ;
- **`selectedItem` contrôlé** : la choisir ne change pas le Pokémon sélectionné. Choisir la ligne une deuxième fois est donc toujours vu comme un nouveau choix (ce qui permet de réessayer après une erreur) ;
- **un seul envoi par recherche** : l'état d'envoi (`useMutation`) n'est affiché que s'il concerne la recherche en cours. Il « revient à zéro » à la recherche suivante sans `useEffect`.

### 7.6 Ce qui n'est pas fait (encore)

L'export, la consultation dans l'interface et l'intégration au jeu d'évaluation (§ 2). On attend d'avoir des signalements pour savoir quel outillage est vraiment utile.

---

## 8. Stratégie de test

| Couche | Fichier | Ce qui est vérifié |
|---|---|---|
| domaine | `test_feedback.py` | validation : vide, trop long, plus de 10 Pokémon, doublons ; limites incluses ; espaces normalisés |
| cas d'usage | `test_report_missing_result.py` | **repositories remplacés par des mocks** : validation avant tout accès ; ids inconnus refusés **sans écriture** ; aucune lecture des Pokémon si rien n'était affiché |
| infrastructure | `test_sqlite_feedback.py` | sur un vrai fichier : enregistrement, date posée par la base, ordre des ids gardé ; **un redémarrage ne perd rien** ; `kind` inconnu refusé par la base ; pas de création de base à la connexion |
| infrastructure | `test_sqlite_repositories.py` | `SqliteFeedbackRepository` fournit toutes les méthodes de son port |
| API | `test_api.py` | cas d'usage remplacé par un mock : 201 avec l'id, pas de cache, 422 (Pydantic et métier) |
| bout en bout | `test_app.py` | signalement réel enregistré dans `feedback.db` ; `feedback.db` créée à côté de `pokedex.db` ou à l'endroit indiqué par `POKEDEX_FEEDBACK_DB` ; **les signalements survivent à un `pokedex-import`** |
| frontend | `features/feedback/ReportMissingResult.test.tsx` | dans les deux recherches : données envoyées (saisie + ids affichés), clavier, aucun résultat, un seul envoi par recherche, nouvelle recherche, échec puis nouvel essai, pas de signalement si la recherche a échoué |

Les tests existants de la recherche par nom ont été adaptés : la liste contient désormais une ligne de plus.

---

## 9. Limites connues et choix assumés

| Limite | Détail | Piste |
|---|---|---|
| **Pas de protection contre les abus** | sans compte ni limite de débit, n'importe qui peut envoyer de faux signalements | acceptable tant que l'API n'est pas publique ; sinon limite de débit (par IP, au niveau du proxy) |
| Le Pokémon attendu est inconnu | volontaire (§ 2) | renseigné à la main lors de la relecture |
| Aucun outil de consultation | requête `sqlite3` à la main | export lorsque le volume le justifie |
| Pas de suppression ni de durée de conservation | les signalements restent indéfiniment | à définir si la feature devient publique (RGPD : la saisie est libre et pourrait contenir autre chose qu'une description) |
| Un clic accidentel est enregistré | pas d'annulation | volume faible attendu ; la relecture filtre |
| Un seul processus d'écriture prévu | SQLite en WAL suffit pour une instance de l'API | une vraie base (PostgreSQL) si l'API passe à plusieurs instances |

---

## 10. Prochaines étapes

1. **Relire les premiers signalements** et indiquer à la main le Pokémon attendu.
2. **Export** vers le format de `benchmarks/appearance_queries.json`, puis ajout des cas retenus au jeu d'évaluation (§ 2).
3. Recalibrer la tolérance aux fautes de la recherche par nom avec les signalements `kind = 'name'`.
4. Si l'API devient publique : limite de débit et durée de conservation.

---

## 11. Carte des fichiers

### Backend : `src/fullstack_pokedex/`

| Fichier | Rôle |
|---|---|
| `domain/feedback.py` | `SearchKind`, `MissingResultReport`, `validate_report`, limites |
| `domain/repositories.py` | port `FeedbackRepository` |
| `domain/errors.py` | `InvalidReportError` |
| `use_cases/report_missing_result.py` | cas d'usage `ReportMissingResult` |
| `infrastructure/sqlite/feedback_schema.sql` | table `missing_result_report` (jamais de `DROP`) |
| `infrastructure/sqlite/feedback.py` | création, connexion, `SqliteFeedbackRepository` |
| `api/routes.py` | `POST /feedback/missing-result`, assemblage des dépendances |
| `api/schemas.py` | `MissingResultReportIn`, `ReportCreatedOut` |
| `api/app.py` | emplacement de `feedback.db` (`POKEDEX_FEEDBACK_DB`), création au démarrage, 422 |

### Tests : `tests/`

`test_feedback.py`, `test_report_missing_result.py`, `test_sqlite_feedback.py`, plus des ajouts dans `test_api.py`, `test_app.py` et `test_sqlite_repositories.py`.

### Frontend : `frontend/src/`

| Fichier | Rôle |
|---|---|
| `features/feedback/useReportMissingResult.ts` | envoi du signalement (`useMutation`) |
| `features/feedback/ReportMissingResult.tsx` | ligne « Didn't find your Pokémon? Report » (recherche par apparence) |
| `features/feedback/ReportMissingResult.test.tsx` | tests de la feature dans les deux recherches |
| `features/suggest/PokemonSearch.tsx` | dernière ligne de la liste déroulante (recherche par nom) |
| `features/identify/AppearanceSearch.tsx` | affiche la ligne de signalement sous les résultats |
| `test/handlers.ts` | route `/api/feedback/missing-result` simulée |
