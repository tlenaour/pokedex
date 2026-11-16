# Benchmark : tolérance aux fautes de frappe dans la recherche de Pokémon par nom

> **But de ce document :** expliquer à une personne qui arrive sur le projet **pourquoi** et **comment** nous avons choisi l'algorithme qui permet de retrouver un Pokémon malgré une faute de frappe. Ce document couvre le contexte, le protocole, les algorithmes comparés, les résultats, les compromis, la recommandation et les limites de l'étude.
>
> - Script : [`benchmarks/fuzzy_name_matching.py`](../benchmarks/fuzzy_name_matching.py)
> - Résultats bruts : [`benchmarks/results/fuzzy_name_matching.json`](../benchmarks/results/fuzzy_name_matching.json)
> - Date : 2026-11-10 — rapidfuzz 3.14.6, Python 3.15.2

---

## Sommaire

1. [En bref](#1-en-bref)
2. [Contexte : où se place la tolérance aux fautes](#2-contexte--où-se-place-la-tolérance-aux-fautes)
3. [Lancer le benchmark](#3-lancer-le-benchmark)
4. [Protocole](#4-protocole)
5. [Les cas de test et pourquoi ils existent](#5-les-cas-de-test-et-pourquoi-ils-existent)
6. [Les algorithmes comparés](#6-les-algorithmes-comparés)
7. [Résultats](#7-résultats)
8. [Compromis : avantages et inconvénients de chaque méthode](#8-compromis--avantages-et-inconvénients-de-chaque-méthode)
9. [Recommandation et décisions ouvertes](#9-recommandation-et-décisions-ouvertes)
10. [Limites de l'étude et pistes](#10-limites-de-létude-et-pistes)
11. [Glossaire](#11-glossaire)

---

## 1. En bref

- **La question :** quand un dresseur tape un nom avec une faute (`bulbsaur`, `pikachoo`, `bulbs`…), quelle mesure de similarité permet de lui proposer quand même le bon Pokémon, sans afficher de suggestions absurdes quand il tape n'importe quoi ?
- **La méthode :** 11 mesures (9 seules et 2 combinaisons) sont testées sur **1 092 cas**, en passant par le **vrai code du domaine** (`rank_candidates`).
- **Le résultat :**

| | Bon Pokémon en 1re position | Dans les 5 suggestions | Saisies sans rapport qui obtiennent une suggestion |
|---|---|---|---|
| Sans tolérance aux fautes (avant la feature) | 4,5 % | 4,5 % | 0 % |
| **Jaro-Winkler seul (seuil 0,80) — retenu** | **92,6 %** | **95,3 %** | **1,4 %** |
| Jaro-Winkler ≥ 0,80 *ou* prefix_osa ≥ 0,70 (meilleur score du benchmark) | 96,2 % | 99,6 % | 4,3 % |

- **Le meilleur score du benchmark :** combiner **Jaro-Winkler**, excellent sur les fautes « à l'oreille » comme `pikachoo`, et **prefix_osa**, une mesure écrite pour ce cas qui excelle sur un **début de nom avec une faute** comme `bulbs`.
- **La décision :** **Jaro-Winkler seul, au seuil de 0,80**. Pas de code maison et aucun changement d'architecture, au prix d'environ 30 % des cas « début de nom + faute ». prefix_osa pourra être ajouté plus tard si les recherches réelles le justifient (voir [§ 9](#9-recommandation-et-décisions-ouvertes)).

---

## 2. Contexte : où se place la tolérance aux fautes

### La feature

> *A new trainer saw a Pokémon whose name began with "bulba", but cannot remember the full name. They want to find it quickly and confirm that it is the Pokémon they had in mind.*

Elle est exposée par `GET /pokemon/suggest?q=…&limit=…` : une liste courte de Pokémon, classés, avec ce qu'il faut pour les reconnaître (image, types, catégorie).

### Le chemin d'une recherche dans le code

```
api/routes.py             GET /pokemon/suggest
   └─ use_cases/suggest_pokemon.py   SuggestPokemon.execute()
        └─ domain/name_search.py     normalize_query() puis rank_candidates()
             ├─ niveaux stricts : EXACT > PREFIX > WORD_PREFIX > SUBSTRING
             └─ niveau FUZZY → port SimilarityScorer  ◄── ce que ce benchmark aide à choisir
```

Les règles de classement sont dans `domain/name_search.py` :

1. **Normalisation** (`normalize_name`) : minuscules, sans accents, sans séparateurs. `"Mr. Mime"` devient `"mrmime"`. Les mesures comparent toujours des formes normalisées.
2. **Niveaux stricts** : correspondance exacte, puis début du nom, puis début d'un mot du nom, puis texte contenu dans le nom. Ils sont sûrs et toujours prioritaires.
3. **Niveau approché (FUZZY)** : il ne sert **qu'à compléter** la liste quand les niveaux stricts trouvent moins de `limit` résultats. Un nom est retenu si son score de similarité est **au moins égal au seuil** (`FUZZY_THRESHOLD`, fixé à **0,80** à la suite de ce benchmark ; il était à 0,85 avant). Le calcul du score est délégué au **port** `SimilarityScorer`, que l'infrastructure implémente.

**Ce benchmark répond à deux questions :** quelle mesure placer derrière ce port, et avec quel seuil ?

---

## 3. Lancer le benchmark

**Prérequis :**
- les dépendances installées (`uv sync`) ; `rapidfuzz` est une dépendance du projet ;
- le fichier `pokedex.json` à la racine. Il n'est **pas versionné** (voir `.gitignore`).

```bash
uv run python benchmarks/fuzzy_name_matching.py
# ou avec d'autres chemins :
uv run python benchmarks/fuzzy_name_matching.py <pokedex.json> <sortie.json>
```

- **Durée :** environ 4 minutes. Chaque mesure est évaluée sur 10 seuils × 1 092 cas.
- **Sortie console :** le nombre de cas par groupe et la référence sans tolérance aux fautes.
- **Fichier JSON :**
  - `methods.<méthode>.sweep` : les métriques pour chaque seuil testé ;
  - `methods.<méthode>.raw` : la capacité à distinguer le bon Pokémon, sans seuil ;
  - `methods.<méthode>.timing` : les temps de calcul ;
  - `methods.<méthode>.chosen_threshold` : le seuil retenu ;
  - `detail.<méthode>` : le détail par type de faute, les cas limites, les saisies courtes, les faux positifs et les échecs.
- **Reproductibilité :** les cas sont générés avec une **graine fixe** (`SEED = 20261110`). Deux exécutions donnent **exactement** les mêmes taux. Seuls les **temps** varient selon la charge de la machine (jusqu'à ± 50 % entre deux exécutions).

---

## 4. Protocole

### 4.1 Principe : tester le vrai comportement, pas la mesure seule

Chaque cas passe par **`rank_candidates` du domaine**, avec `limit = 5` (la valeur par défaut de l'API). On mesure donc ce que **l'utilisateur verrait** :
- les niveaux stricts passent en premier ;
- la recherche approchée ne se lance que s'il manque des résultats ;
- la normalisation est appliquée.

Pour pouvoir donner chaque mesure au domaine, le script l'enveloppe dans un petit objet qui respecte le port `SimilarityScorer` (`CachedScorer`). Ses scores sont gardés en mémoire pour ne pas les recalculer à chaque seuil testé.

### 4.2 Les métriques

| Métrique | Définition | Question à laquelle elle répond |
|---|---|---|
| **hit@1** | % des cas où le bon Pokémon est **en 1re position** | « Je vois mon Pokémon tout de suite » : la meilleure expérience. |
| **hit@5** | % des cas où il est **dans les 5 suggestions** | « Je le trouve dans la liste » : le minimum pour que la feature fonctionne. |
| **Faux positifs (FP)** | % des **saisies sans rapport** qui obtiennent **au moins une** suggestion approchée | « Je tape n'importe quoi et on me propose quand même des Pokémon » : signe d'une méthode trop permissive. |
| **Bruit** | Nombre moyen de suggestions approchées **fausses** affichées à côté de la bonne | Propreté de la liste. |
| **Bon Pokémon en tête parmi les 151** (sans seuil) | % des cas où le bon Pokémon a **le meilleur score** des 151 | Capacité à reconnaître le bon nom, indépendamment du seuil. Permet de distinguer « mauvaise mesure » et « mauvais seuil ». |
| **Temps** | ms pour 151 calculs de similarité, et pour un appel à `rank_candidates` dans le pire cas | Rapidité de l'autocomplétion. |

Les cas sémantiques (§ 5.4) sont **exclus** des taux globaux, et les saisies sans rapport ne servent qu'au calcul des faux positifs.

### 4.3 Comment le seuil est choisi

Pour chaque mesure, on teste les seuils **0,50, 0,55… jusqu'à 0,95**. Le **seuil retenu** est celui qui **maximise hit@5 tout en gardant au plus 5 % de faux positifs**. En cas d'égalité, on prend le meilleur hit@1, puis le seuil le plus bas.

Le plafond de 5 % est un choix produit. Une suggestion approximative coûte peu à l'utilisateur (il l'ignore), alors qu'une liste vide quand il a fait une faute est un échec visible de la feature. Pour ne retenir que les méthodes très prudentes, il suffit d'abaisser ce plafond.

### 4.4 Le modèle de clavier

Certaines fautes générées utilisent une **touche voisine** sur le clavier. Le script décrit un clavier **QWERTY** par ses trois rangées (`qwertyuiop`, `asdfghjkl`, `zxcvbnm`). Les voisines d'une lettre sont les lettres à une colonne près, sur sa rangée et sur celles du dessus et du dessous. Par exemple, `s` a pour voisines `q w e a d z x c`.

**Important :** le clavier ne sert **qu'à générer des fautes réalistes**. **Aucune des mesures comparées ne connaît le clavier** : remplacer `s` par `d` (deux touches voisines) coûte autant que remplacer `s` par `p`. Changer de disposition (par exemple en AZERTY) changerait les fautes générées, pas leur coût. Ce point n'a pas été mesuré (voir [§ 10](#10-limites-de-létude-et-pistes)).

---

## 5. Les cas de test et pourquoi ils existent

**1 092 cas** en 6 groupes. Chaque groupe répond à une question précise.

| Groupe | Nombre | Rôle |
|---|---|---|
| Fautes standard | 755 | Volume et couverture des 151 noms, par type de faute |
| Fautes phonétiques | 242 | Réalisme : fautes de plusieurs lettres, « comme ça se prononce » |
| Cas limites | 20 | Points faibles connus des algorithmes |
| Fautes sémantiques | 5 | Montrer la limite de l'approche (exclus des scores) |
| Saisies sans rapport | 70 | Mesurer les faux positifs et fixer le seuil |
| Saisies très courtes | 7 | Observer le comportement, sans bonne réponse attendue |

### 5.1 Fautes standard : 755 cas (5 types × 151 Pokémon)

Pour **chacun des 151 Pokémon**, le script génère une faute de chaque type :

| Type | Exemple | Pourquoi ce type |
|---|---|---|
| **Lettre supprimée** | `charzard` | Faute très courante. Toutes les mesures devraient la rattraper : c'est la référence minimale. |
| **Lettre ajoutée** (lettre doublée ou touche voisine) | `pikachuu` | Le doigt appuie deux fois ou touche la voisine. |
| **Lettre remplacée** par une touche voisine | `bulbasaue` | Le doigt glisse. Révèle les mesures où un remplacement compte double (Indel) et la fragilité des trigrammes. |
| **Deux lettres inversées** | `bulbasuar` | Frappe rapide. **Sépare Levenshtein (inversion = 2 erreurs) de Damerau-OSA (inversion = 1 erreur).** |
| **Début de nom + faute** (60 % du nom, au moins 4 lettres, une touche voisine) | `bulbs`, `charmamd` | **C'est la situation même de la feature** : on ne connaît que le début, et on peut se tromper en le tapant. C'est le type qui départage le plus les méthodes. |

**Pourquoi tous les Pokémon :** pour couvrir les noms courts (`mew`, `muk`, `onix`), les longs (`kangaskhan`), les noms très proches (`nidorina`/`nidorino`) et les noms à tiret (`mr-mime`). Sur un nom de 3 lettres, une seule erreur représente 33 % du mot.

**Deux règles de génération :**
- **La 1re lettre n'est jamais modifiée dans ce groupe.** Ce cas est plus rare en pratique, et Jaro-Winkler le pénalise fortement, ce qui fausserait la comparaison. Il est testé à part, dans les cas limites.
- **Une faute qui produit le nom d'un autre Pokémon est régénérée**, pour que la bonne réponse ne soit jamais ambiguë.

### 5.2 Fautes phonétiques : 242 cas, écrits à la main, pour 86 Pokémon

Exemples : `pikachoo`, `ninetails` (pour ninetales), `onyx` (onix), `jinx` (jynx), `gyrados`, `snorelax`, `farfetched`, `magicarp`, `geodood`, `taurus` (tauros).

**Pourquoi :** les fautes générées n'ont **qu'une seule erreur**. Dans la réalité, beaucoup d'erreurs viennent de la façon dont on **entend** le nom. Elles cumulent souvent plusieurs modifications (`bulbasore` en demande 3 par rapport à `bulbasaur`) ou changent la longueur du mot.

### 5.3 Cas limites : 20 cas

Chacun cible **un point faible connu d'au moins une méthode**.

| Saisie → attendu | Ce qu'on vérifie |
|---|---|
| `vulbasaur` → bulbasaur | 1re lettre fausse : Jaro-Winkler, qui favorise le début, s'effondre-t-il ? |
| `ublbasaur` → bulbasaur | Inversion au tout début |
| `bulbsor` → bulbasaur | Deux fautes : le seuil est-il assez tolérant ? |
| `bulbs` → bulbasaur | Début très court + faute |
| `pikc` → pikachu | Début de 4 lettres + inversion |
| `charmad` → charmander | Début + faute, avec des noms proches (charizard, charmeleon) |
| `bulbasaurr`, `pikachuu` | Lettre en trop à la fin |
| `pikachuuuu` → pikachu | Beaucoup de lettres répétées |
| `mrmine` → mr-mime | Nom à tiret + faute (normalisation et mesure ensemble) |
| `nidorna` → nidorina, `nidokng` → nidoking | Noms presque identiques : on vérifie la **1re position** |
| `mwe` → mew | Nom de 3 lettres : une inversion représente 33 % du mot |
| `mewtow` → mewtwo | Inversion à la fin, et le piège mew/mewtwo |
| `onyx` → onix, `jinx` → jynx | Nom de 4 lettres, une lettre remplacée (fautes « classiques » de joueurs) |
| `eve` → eevee | Saisie très courte, deux lettres manquantes |
| `charzard` → charizard | Lettre manquante au milieu d'un nom proche d'autres |
| `charmeleom` → charmeleon | Dernière lettre remplacée par la touche voisine |
| `raichu pikachu` → raichu | Deux noms tapés à la suite |

### 5.4 Fautes sémantiques : 5 cas, exclus des scores

`butterfly` (butterfree), `mister mime`, `eggsecutor` (exeggutor), `coughing` (koffing), `kangaroo` (kangaskhan).

**Pourquoi ils sont là :** ils représentent ce qu'**aucune mesure sur les lettres ne peut raisonnablement trouver**, parce que l'utilisateur pense au sens ou au jeu de mots du nom. Ils montrent la **limite** de l'approche. On ne cherche pas à les réussir : une méthode qui les « trouve » est plutôt trop permissive.

### 5.5 Saisies sans rapport : 70 cas

- **30 mots** : `pokemon`, `test`, `table`, `lorem`, `computer`, `trainer`… Ils ont la forme de vrais mots et partagent souvent des morceaux avec des noms (`test`/`tentacool`). Ce sont les faux positifs les plus probables.
- **40 chaînes aléatoires** de 4 à 9 lettres : elles mesurent le bruit de fond.

**Pourquoi :** sans ce groupe, la « meilleure » méthode serait celle qui propose toujours 5 Pokémon. **C'est ce groupe qui fixe le seuil** (§ 4.3).

### 5.6 Saisies très courtes : 7 cas, observés seulement

`bu`, `pk`, `mw`, `ch`, `sq`, `zz`, `a`. Il n'y a **pas de bonne réponse** : plusieurs Pokémon sont légitimes. On vérifie seulement que les **niveaux stricts remplissent les 5 places**, et donc que la recherche approchée, source de bruit sur des saisies si courtes, ne se lance pas.

---

## 6. Les algorithmes comparés

Toutes les mesures renvoient un score **entre 0 (rien en commun) et 1 (identique)** et comparent des formes **normalisées**. Les fonctions viennent de **rapidfuzz** (bibliothèque compilée en C++), sauf `prefix_osa`, `hybrid_osa` et `trigram_jaccard`, écrites dans le script.

### Scores d'exemple

Pour se faire une idée du comportement de chaque mesure :

| Méthode | `bulbsaur` / bulbasaur | `bulbs` / bulbasaur | `pikachoo` / pikachu | `vulbasaur` / bulbasaur | `test` / tentacool | `xyz` / bulbasaur |
|---|---|---|---|---|---|---|
| levenshtein | 0,89 | 0,56 | 0,75 | 0,89 | 0,33 | 0,00 |
| damerau_osa | 0,89 | 0,56 | 0,75 | 0,89 | 0,33 | 0,00 |
| indel_ratio | 0,94 | 0,71 | 0,80 | 0,89 | 0,46 | 0,00 |
| jaro_winkler | 0,95 | **0,91** | **0,92** | 0,88 | 0,69 | 0,00 |
| partial_ratio | 0,88 | 0,89 | 0,92 | 0,94 | **0,75** | 0,00 |
| wratio | 0,94 | 0,80 | 0,80 | 0,89 | 0,68 | 0,00 |
| prefix_osa | 0,89 | 0,83 | 0,75 | 0,89 | **0,75** | 0,00 |
| trigram_jaccard | 0,58 | 0,33 | 0,55 | 0,54 | 0,15 | 0,00 |

Sur `bulbs`, les mesures qui comparent le **nom entier** (Levenshtein, OSA) donnent un score bas (0,56), parce que les 4 lettres non tapées comptent comme des erreurs. Sur `test`, les mesures centrées sur le **début du nom** ou sur un **morceau** (prefix_osa, partial_ratio) donnent un score élevé (0,75) à un mot sans rapport.

### Description de chaque méthode

| Méthode | Principe | Fonction |
|---|---|---|
| **levenshtein** | Nombre minimal d'ajouts, suppressions et remplacements pour passer d'un mot à l'autre, ramené à la longueur | `Levenshtein.normalized_similarity` |
| **damerau_osa** | Levenshtein, plus l'inversion de deux lettres voisines comptée comme **une** seule faute | `OSA.normalized_similarity` |
| **indel_ratio** | Ajouts et suppressions seulement : un remplacement compte comme 2 | `Indel.normalized_similarity` |
| **jaro_winkler** | Lettres communes proches les unes des autres, avec un **bonus si le début correspond** (jusqu'à 4 lettres) | `JaroWinkler.similarity` |
| **partial_ratio** | Meilleure correspondance entre la saisie et **un morceau** du nom | `fuzz.partial_ratio / 100` |
| **wratio** | Heuristique de rapidfuzz qui combine plusieurs mesures avec des poids | `fuzz.WRatio / 100` |
| **prefix_osa** *(maison)* | Damerau-OSA entre la saisie et **le début du nom de même longueur** (± 1 lettre). Si le nom est plus court que la saisie, il est comparé en entier. | `prefix_osa()` dans le script |
| **hybrid_osa** *(maison)* | Maximum de Damerau-OSA sur le nom entier et de prefix_osa | lambda dans le script |
| **trigram_jaccard** *(maison)* | Part des groupes de 3 lettres en commun (Jaccard) | `trigrams()` dans le script |
| **jw_prefix_max** *(combinaison)* | max(Jaro-Winkler, prefix_osa), avec **un seul seuil** | lambda dans le script |
| **jw_or_prefix** *(combinaison)* | **Jaro-Winkler ≥ s *ou* prefix_osa ≥ s − 0,10**, ce qui donne au seuil 0,80 : JW ≥ 0,80 ou prefix_osa ≥ 0,70 | lambda dans le script (§ 9) |

**Pourquoi `prefix_osa` a été écrit :** la feature porte sur un **début de nom**. Comparer `bulbs` au nom **entier** `bulbasaur` revient à compter les 4 lettres non tapées comme des fautes. `prefix_osa` compare `bulbs` à `bulba`, le début du nom de même longueur, et ne compte que la vraie faute. La tolérance de ± 1 lettre sur la longueur couvre une lettre ajoutée ou supprimée dans le début tapé.

---

## 7. Résultats

> Les taux sont reproductibles exactement. Les temps sont indicatifs (± 50 % selon la charge de la machine).

### 7.1 Synthèse, chaque méthode à son seuil retenu

| Méthode | Seuil | **hit@1** | **hit@5** | Début + faute | Phonétique | Cas limites | **FP** | Bruit | Bon Pokémon en tête (sans seuil) | ms / 151 scores |
|---|---|---|---|---|---|---|---|---|---|---|
| *Sans tolérance aux fautes* | — | 4,5 | 4,5 | — | 9,1 | 5 | 0 | 0 | — | — |
| levenshtein | 0,60 | 85,4 | 85,8 | 11,9 | 99,6 | 80 | 1,4 | 0,21 | 92,5 | 0,03 |
| damerau_osa | 0,60 | 86,2 | 86,5 | 11,9 | 99,6 | 85 | 1,4 | 0,22 | 93,7 | 0,03 |
| indel_ratio | 0,70 | 84,3 | 85,0 | 4,6 | 98,8 | 90 | **0,0** | 0,20 | 93,1 | 0,03 |
| jaro_winkler | 0,80 | 92,6 | 95,3 | 70,2 | **100** | **95** | 1,4 | 0,53 | 95,2 | 0,04 |
| partial_ratio | 0,85 | 70,0 | 74,3 | 36,4 | 80,2 | 75 | 1,4 | 0,18 | 87,9 | 0,08 |
| wratio | 0,75 | 87,5 | 90,3 | 43,7 | 96,3 | **95** | 1,4 | 0,18 | 93,0 | 0,15 |
| prefix_osa | 0,70 | 95,2 | 98,2 | 98,0 | 96,7 | 85 | 2,9 | 0,23 | 95,1 | 0,09 |
| hybrid_osa | 0,70 | 95,2 | 98,2 | 98,0 | 96,7 | 85 | 2,9 | 0,23 | 95,1 | 0,18 |
| trigram_jaccard | 0,50 | 50,6 | 51,0 | 0,0 | 64,0 | 50 | 0,0 | 0,02 | 91,8 | 0,63 |
| jw_prefix_max | 0,80 | 93,6 | 96,7 | 79,5 | **100** | **95** | 1,4 | 0,54 | 95,4 | 0,19 |
| **jw_or_prefix** | 0,80 / 0,70 | **96,2** | **99,6** | **99,3** | **100** | **95** | 4,3 | 0,57 | **95,7** | 0,15 |

**Temps de bout en bout :** un appel à `rank_candidates` dans le pire cas (aucune correspondance stricte, donc 151 scores) prend **entre 1,3 et 2,6 ms** selon la méthode et la charge de la machine. La part fixe, la **normalisation** des 151 noms, prend environ 1,1 ms. Le calcul de similarité ne représente qu'une petite partie du total : **la rapidité ne départage pas les méthodes.**

### 7.2 Détail par type de faute (hit@5, en %)

| Type de faute (n) | lev | osa | indel | **jw** | partial | wratio | **prefix_osa** | trigram | **jw_or_prefix** |
|---|---|---|---|---|---|---|---|---|---|
| Lettre supprimée (151) | 100 | 100 | 100 | 100 | 74,2 | 100 | 100 | 78,8 | 100 |
| Lettre ajoutée (151) | 100 | 100 | 100 | 100 | 89,4 | 100 | 100 | 93,4 | 100 |
| Lettre remplacée (151) | 100 | 100 | 98,7 | 100 | 81,5 | 98,7 | 98,7 | 55,0 | 100 |
| Lettres inversées (151) | 96,0 | **100** | 98,7 | 98,7 | 80,8 | 98,7 | 98,7 | 7,3 | 98,7 |
| **Début de nom + faute (151)** | 11,9 | 11,9 | 4,6 | 70,2 | 36,4 | 43,7 | 98,0 | 0,0 | **99,3** |
| Phonétique (242) | 99,6 | 99,6 | 98,8 | **100** | 80,2 | 96,3 | 96,7 | 64,0 | **100** |
| *Sémantique (5, exclu)* | 40 | 40 | 60 | 60 | 40 | 20 | 20 | 20 | 60 |

**Ce qu'on en retient :**
1. **Sur une faute dans un nom complet, les mesures sérieuses se valent** (≥ 96 %).
2. **Ce qui départage les méthodes, c'est « début de nom + faute », la situation de la feature.** Les mesures qui comparent le nom entier s'effondrent sous 12 %. Seuls prefix_osa (98 %) et, en partie, Jaro-Winkler (70 %, grâce à son bonus sur le début) tiennent.
3. **Sur les fautes phonétiques, Jaro-Winkler est le meilleur** (100 %). prefix_osa rate celles qui demandent plusieurs modifications ou changent la longueur : `bulbasore`, `snorlacks`, `oniks`, `vulpicks`, `ridon`, `jynks`, `craby`, `toros`.
4. **Les deux sont complémentaires**, d'où la combinaison.

### 7.3 Cas limites, pour les méthodes principales

| Saisie | Situation | jaro_winkler | prefix_osa | damerau_osa | **jw_or_prefix** |
|---|---|---|---|---|---|
| `vulbasaur` | 1re lettre fausse | ✅ | ✅ | ✅ | ✅ |
| `ublbasaur` | inversion au début | ✅ | ✅ | ✅ | ✅ |
| `bulbsor` | deux fautes | ✅ | ❌ | ✅ | ✅ |
| `bulbs` | début court + faute | ✅ | ✅ | ❌ | ✅ |
| `pikc` | début court + inversion | ✅ | ✅ | ❌ | ✅ |
| `charmad` | début + faute | ✅ | ✅ | ✅ | ✅ |
| `bulbasaurr`, `pikachuu`, `pikachuuuu` | lettres en trop | ✅ | ✅ | ✅ | ✅ |
| `mrmine` | nom à tiret + faute | ✅ | ✅ | ✅ | ✅ |
| `nidorna`, `nidokng` | noms très proches | ✅ en 1er | ✅ en 1er | ✅ en 1er | ✅ en 1er |
| `mwe` | nom de 3 lettres | ❌ | ❌ | ✅ | ❌ |
| `mewtow` | inversion à la fin | ✅ | ✅ | ✅ | ✅ |
| `onyx`, `jinx` | nom de 4 lettres | ✅ | ✅ | ✅ | ✅ |
| `eve` | très court | ✅ | ✅ | ✅ | ✅ |
| `raichu pikachu` | deux noms tapés | ✅ | ❌ | ❌ | ✅ |

`mwe` n'est trouvé que par Levenshtein, OSA et WRatio. Sur un nom de 3 lettres, une inversion représente 33 % du mot ; trop pour les autres mesures.

### 7.4 Saisies très courtes

On obtient **le même résultat avec toutes les méthodes**. Par exemple, `bu` donne bulbasaur, butterfree, kabuto, kabutops, electabuzz, et `a` donne abra, arbok, arcanine, alakazam, articuno. Ce sont des correspondances **strictes** qui remplissent les 5 places, donc la recherche approchée ne se lance pas. C'est une **protection naturelle** contre le bruit sur les saisies courtes. Seules différences : `pk` ne donne rien ; `mw` donne `mew` seulement avec OSA et WRatio.

### 7.5 Faux positifs observés

| Méthode | Saisies sans rapport qui obtiennent une suggestion |
|---|---|
| jaro_winkler 0,80 | `aaaa` → alakazam |
| prefix_osa 0,70 | `test` → tentacool, tentacruel ; `eqeg` → exeggcute, exeggutor |
| damerau_osa 0,60 | `lorem` → golem |
| wratio 0,75 | `table` → clefable |
| **jw_or_prefix** | `aaaa`, `test`, `eqeg` (ceux des deux méthodes) |

Ces erreurs restent **plausibles à l'écran** (« test » ressemble au début de « tentacool »). Elles gênent peu l'utilisateur.

### 7.6 Capacité à distinguer le bon Pokémon, et plage de seuils utilisable

| Méthode | Bon Pokémon en tête | Score du bon Pokémon (10e centile / médiane) | Meilleur score sur une saisie sans rapport (médiane / 90e centile / max) |
|---|---|---|---|
| jaro_winkler | 95,2 % | 0,824 / 0,956 | 0,662 / 0,771 / **0,850** |
| prefix_osa | 95,1 % | 0,750 / 0,857 | 0,429 / 0,600 / 0,750 |
| damerau_osa | 93,7 % | 0,500 / 0,857 | 0,354 / 0,500 / 0,600 |
| trigram_jaccard | 91,8 % | 0,250 / 0,500 | 0,091 / 0,167 / 0,250 |
| partial_ratio | 87,9 % | 0,800 / 0,875 | 0,667 / 0,750 / 0,889 |

**Comment lire ce tableau :** un bon seuil se place **entre** les scores des saisies sans rapport et ceux du bon Pokémon. Plus l'écart entre les deux est grand, plus le réglage est facile.
- **Jaro-Winkler distingue le mieux le bon Pokémon, mais ses scores sont tassés vers le haut.** Une saisie sans rapport atteint déjà 0,66 en médiane. Résultat : à 0,75, il y a **14 %** de faux positifs ; à 0,80, **1,4 %**. **Le réglage est délicat.**
- **prefix_osa laisse un écart net** : les saisies sans rapport plafonnent à 0,75. Le réglage est plus facile.
- **Le trigramme** classe correctement, mais ses scores sont bas par nature. Il lui faudrait un seuil sous 0,50, qui n'a pas été testé, et même là, les scores du bon Pokémon et des saisies sans rapport se chevauchent.

---

## 8. Compromis : avantages et inconvénients de chaque méthode

### Levenshtein
- ➕ Standard, facile à expliquer (« 2 fautes sur 9 lettres »), rapide.
- ➖ Compare le nom **entier** : sans valeur pour un début de nom avec une faute (12 %). Une inversion compte double. Le seuil doit être bas (0,60), donc il est sensible sur les noms courts.

### Damerau-Levenshtein (OSA)
- ➕ Comme Levenshtein, mais une inversion compte comme une seule faute (100 % sur les inversions). L'une des rares méthodes qui trouvent `mwe`. Peu de bruit.
- ➖ Même faiblesse sur les débuts de nom (12 %). Rate `bulbs` et `pikc`.

### Indel ratio
- ➕ **Zéro faux positif.**
- ➖ Un remplacement compte double : le pire sur les débuts de nom avec faute (4,6 %).

### Jaro-Winkler
- ➕ **Le meilleur sur les fautes phonétiques (100 %) et les cas limites (95 %).** Il distingue le mieux le bon Pokémon. Son bonus sur le début du nom correspond à la feature. Une seule fonction de bibliothèque, aucun code maison.
- ➖ 70 % seulement sur les débuts de nom avec faute. Scores tassés, donc **seuil délicat à régler** (0,75 → 14 % de faux positifs, 0,80 → 1,4 %). Plus de bruit (0,53 suggestion fausse par recherche, par exemple `charmad` → charmander, charizard, charmeleon).

### partial_ratio
- ➕ Pensé pour retrouver un morceau dans une chaîne plus longue.
- ➖ **La plus faible au global (74 %).** Trop permissive entre une saisie courte et un nom long, et sans seuil satisfaisant. **À éviter.**

### WRatio
- ➕ Toute faite. 95 % sur les cas limites, peu de bruit.
- ➖ **Opaque** (une combinaison pondérée, difficile à expliquer et à régler). Plus lente que les autres (négligeable ici). 44 % sur les débuts de nom avec faute.

### prefix_osa
- ➕ **Le meilleur sur les débuts de nom avec faute (98 %), meilleur hit@1 des mesures seules (95,2 %).** Peu de bruit. Facile à expliquer (« une faute dans les 5 premières lettres »). Seuil facile à régler.
- ➖ **Code maison** à maintenir et tester (environ 10 lignes). Plus faible sur les fautes phonétiques (96,7 %). Faux positifs sur les mots de 4 lettres (`test` → tentacool). Rate `bulbsor` et `raichu pikachu`.

### hybrid_osa
- ➖ **N'apporte rien** par rapport à prefix_osa : résultats identiques. **Abandonnée.**

### Trigrammes (Jaccard)
- ➕ Aucune dépendance. Résiste à l'ordre des lettres.
- ➖ Mauvaise sur les noms courts et les fautes isolées. Scores mal calibrés. **À écarter.**

### jw_prefix_max (un seul seuil)
- ➕ 100 % phonétique, mieux que Jaro-Winkler seul sur les débuts de nom (79,5 %).
- ➖ **Un seul seuil pour deux mesures qui n'ont pas la même plage de scores.** prefix_osa ne donne son meilleur qu'à 0,70, et Jaro-Winkler qu'à 0,80. Avec un seuil unique, on bride l'une ou l'autre.

### jw_or_prefix (deux seuils), recommandée
- ➕ **La meilleure partout** : 99,6 % hit@5, 96,2 % hit@1, 100 % phonétique, 99,3 % début de nom + faute, 95 % des cas limites. Chaque mesure couvre les échecs de l'autre. Aussi rapide que les autres.
- ➖ **Le plus de faux positifs (4,3 %, soit 3 sur 70)** et un peu plus de bruit (0,57). **Deux seuils** à régler. Si on la code comme un seul score avec décalage (comme dans le script), ce score devient artificiel : `xyz` contre `bulbasaur` vaut 0,10 au lieu de 0.

---

## 9. Recommandation et décisions ouvertes

### Décision retenue (2026-11-10)

**Jaro-Winkler seul, au seuil de 0,80** (implémentation : `JaroWinklerScorer` dans `infrastructure/similarity.py`, `FUZZY_THRESHOLD = 0.80` dans `domain/name_search.py`).

- **Pourquoi :** c'est le meilleur compromis entre simplicité et efficacité. Une fonction de bibliothèque sans code maison, un seul seuil, aucun changement de la signature du domaine, et le moins de faux positifs parmi les bonnes méthodes (1,4 %).
- **Ce qu'on accepte de perdre :** environ 30 % des cas « début de nom + faute », surtout quand le début tapé est court par rapport au nom.
- **Quand revenir dessus :** si les recherches réelles qui ne renvoient aucun résultat contiennent beaucoup de débuts de nom avec une faute. On ajoutera alors prefix_osa selon l'option B ci-dessous, sans casser l'existant.

### Recommandation issue du benchmark

**Le meilleur score est obtenu avec la combinaison Jaro-Winkler ≥ 0,80 *ou* prefix_osa ≥ 0,70.**

La feature porte sur une **mémoire partielle**. Ne pas trouver `bulbs` serait un échec visible ; une suggestion en trop (`test` → tentacool) est sans gravité.

**Si on préfère une seule mesure, sans code maison :** Jaro-Winkler à 0,80. On perd environ 30 % des cas « début de nom + faute ».

### Options étudiées, si on ajoute prefix_osa plus tard

**1. Comment intégrer deux seuils dans le domaine**, qui n'en prévoit qu'un aujourd'hui (`rank_candidates(…, scorer, fuzzy_threshold)`) :

| Option | Description | ➕ | ➖ |
|---|---|---|---|
| **A. Adaptateur calibré** | `RapidfuzzScorer` renvoie `max(JW, prefix_osa + 0,10)` ; le domaine garde un seuil unique de 0,80 (ce que fait le script) | Aucun changement dans le domaine | L'adaptateur contient une connaissance du seuil (le décalage de 0,10, valeur arbitraire) ; le score renvoyé à l'API est artificiel |
| **B. Plusieurs scorers dans le domaine** | `rank_candidates` reçoit une liste de paires `(scorer, seuil)` ; un nom est retenu si **l'une** des mesures dépasse **son** seuil | Les seuils restent des règles métier, explicites et testées dans le domaine | La signature de `rank_candidates` et du cas d'usage change ; un peu plus de code |

Préférence de l'auteur : **option B**, cohérente avec le principe « les règles métier vont dans le domaine ».

**2. La valeur de `FUZZY_THRESHOLD`** : 0,85 était **trop strict pour toutes les mesures**. Il est passé à 0,80 (décision ci-dessus) ; avec l'option B, on aurait deux seuils (0,80 et 0,70).

**3. Une longueur minimale pour prefix_osa ?** Ne l'appliquer qu'à partir de 5 caractères supprimerait le faux positif `test` → tentacool, mais ferait rater `pikc` (4 lettres). Avec cet échantillon, le gain et la perte sont du même ordre : **pas recommandé pour l'instant.**

---

## 10. Limites de l'étude et pistes

| Limite | Effet | Piste |
|---|---|---|
| **Cas construits par nous** (fautes générées, et fautes phonétiques écrites par quelqu'un qui connaît les noms) | Les vraies fautes d'utilisateurs peuvent être différentes | Enregistrer les recherches de production **sans résultat** et recalibrer avec |
| **Peu de saisies sans rapport (70)** | Chaque cas vaut 1,4 point de faux positifs : l'écart entre 1,4 % et 4,3 % ne tient qu'à 2 cas | Étendre à plusieurs centaines de saisies, idéalement réelles |
| **Clavier QWERTY uniquement** | Un public francophone tape en AZERTY (touches voisines différentes) | Relancer avec un modèle AZERTY, en changeant la constante `QWERTY` du script. Les conclusions ne devraient pas changer (§ 4.4), mais ce n'est pas vérifié. |
| **Seuils réglés et évalués sur les mêmes cas** | Les résultats sont un peu optimistes | Séparer les cas en deux : une partie pour régler, une autre pour valider |
| **Pas de pondération par clavier** dans les mesures | Une erreur sur une touche voisine coûte autant qu'une erreur sur une touche éloignée | Distance pondérée (à écrire nous-mêmes, rapidfuzz ne le permet pas paire par paire). Gain probablement faible vu les résultats actuels. |

---

## 11. Glossaire

| Terme | Définition |
|---|---|
| **Normalisation** | Transformation d'un nom en forme comparable : minuscules, sans accents, sans séparateurs (`"Mr. Mime"` → `"mrmime"`). Voir `normalize_name` dans `domain/name_search.py`. |
| **Niveaux stricts** | Correspondance EXACT, PREFIX, WORD_PREFIX ou SUBSTRING. Sûrs, toujours classés avant la correspondance approchée. |
| **FUZZY** | Correspondance approchée par mesure de similarité ; elle ne sert qu'à compléter la liste. |
| **Port `SimilarityScorer`** | Interface du domaine (`score(query, name) -> float` entre 0 et 1), implémentée par l'infrastructure. Le benchmark aide à choisir cette implémentation. |
| **Seuil (threshold)** | Score minimal pour qu'un nom soit retenu en correspondance approchée. |
| **hit@1 / hit@5** | % des cas où le bon Pokémon est en 1re position / dans les 5 suggestions. |
| **Faux positif (FP)** | Une saisie sans rapport qui obtient au moins une suggestion approchée. |
| **Bruit** | Nombre moyen de suggestions approchées fausses affichées à côté de la bonne. |
| **Distance d'édition** | Nombre minimal de modifications (ajout, suppression, remplacement, et inversion pour OSA) pour passer d'un mot à l'autre. |
| **OSA** (*Optimal String Alignment*) | Variante de Damerau-Levenshtein : l'inversion de deux lettres voisines compte comme une seule modification. |
| **Jaro-Winkler** | Similarité fondée sur les lettres communes et leur ordre, avec un bonus quand le début correspond. |
| **Trigramme** | Groupe de 3 lettres consécutives (`bul`, `ulb`, `lba`…). |
| **Graine (seed)** | Valeur qui fixe le générateur aléatoire : mêmes cas à chaque exécution. |
