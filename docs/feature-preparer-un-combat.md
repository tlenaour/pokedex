# Feature : préparer un combat

## Le besoin

Le dresseur choisit un Pokémon (page `#/battle`, recherche par nom). L'application montre :
- ses **faiblesses**, ses **résistances**, ses **immunités**, et les types contre lesquels il est **efficace** ;
- **ce qu'il peut vous infliger** (empoisonner, endormir, paralyser…) ;
- **ce qu'il peut éviter ou soigner** (insensible au sommeil, se soigne des statuts…) ;
- **ce qu'il faut éviter** de lui faire.

L'application ne recommande pas d'adversaire à lui envoyer : cette partie a été retirée, elle alourdissait trop le code pour l'instant.

Tout est déterministe : on applique les règles du jeu, aucune IA n'intervient à la requête.

## Architecture

| Couche | Fichier | Rôle |
|---|---|---|
| domaine | `domain/type_chart.py` | table d'efficacité des 18 types, `effectiveness()` |
| domaine | `domain/matchup.py` | profil défensif, points forts |
| domaine | `domain/effects.py` | ce que disent les tags : menaces, protections, pièges |
| use case | `use_cases/get_matchup.py` | `GetMatchup` : assemble le tout pour un Pokémon |
| infrastructure | `infrastructure/effect_tags.py`, `sqlite/importer.py` | import de `data/tags_llm.json` dans `effect_tag` |
| infrastructure | `SqliteEffectRepository.list_pokemon_effects()` | les tags de chaque Pokémon, via ses attaques et ses talents |
| API | `GET /pokemon/{ref}/matchup` | réponse `MatchupOut` (404 si inconnu) |
| front | `features/matchup/` | `BattlePrep.tsx`, `useMatchup.ts`, `labels.ts` (les phrases en anglais) |

## Pourquoi la table des types est du code

Ce sont des règles fixes du jeu, pas des données : environ 120 lignes dans le domaine, testées, plutôt qu'une table SQL avec son import. Elle suit les **types actuels** (Fée, Acier, Ténèbres), comme les données (`fairy` pour Clefairy). Elle a été vérifiée contre PokéAPI (`/type/{name}`, `damage_relations`) : aucune différence.

## Règles de calcul

- **Multiplicateur** d'une attaque contre un Pokémon : produit sur ses deux types (×4, ×2, ×1, ×½, ×¼, ×0).
- **Points forts** : les types que ses propres types touchent à ×2. On n'utilise pas ses attaques : elles couvrent presque tous les types.
- **Immunité possible** : un talent de la cible qui bloque un type (`immune:ground` pour Levitate) fait passer ce type des faiblesses aux immunités, avec le nom du talent.

## Ce que disent les tags

Les tags (`data/tags_llm.json`) de la cible donnent quatre informations :

| Affichage | Tags de la cible | Exemple |
|---|---|---|
| **Immune to** (en plus des types) | `immune:<type>` de ses talents | Gastly (Levitate) : sol |
| **What it can inflict on you** | `inflicts:X` | Arbok : empoisonner, paralyser… |
| **What it can avoid or cure** | `prevents:X`, `cures:X` | Hypno (Insomnia) : insensible au sommeil ; Chansey (Natural Cure) : se soigne des statuts |
| **What to avoid** | `reflects:X`, `requires:X` de ses talents | Alakazam (Synchronize) renvoie le poison ; Machamp (Guts) est renforcé par un statut |

`X` est un effet que quelque chose peut empêcher : sommeil, poison, paralysie, brûlure, gel, confusion, peur, attraction, K.O. en un coup, et `any` (tous les statuts majeurs).

**Seuls les tags comptent.** Le champ `comment` n'est pas utilisé.

**Une règle en plus des tags :** les attaques apprises par plus de 80 % des Pokémon sont ignorées (`UNIVERSAL_MOVE_SHARE`) : Toxic, Rest, Substitute, Double Team, Rage. Sinon, tout le monde « peut empoisonner ».

## Limites

- **Pas de recommandation d'adversaire** : le dresseur lit les faiblesses et choisit lui-même.
- **Les points forts viennent des types de la cible, pas de ses attaques.**
- **La méthode d'apprentissage d'une attaque est inconnue** (niveau ou CT) : `pokemon.moves` est une simple liste de noms.
- **Les talents des données sont les talents actuels**, alors que les attaques sont celles de Rouge, Bleu et Jaune (en génération 1, les talents n'existaient pas).
- **Pas de niveaux, ni de statistiques.**
