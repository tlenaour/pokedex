# Spec agent : refonte UX V1 (2 écrans)

> **Pour qui :** un agent de code qui part de zéro sur ce dépôt et doit livrer la refonte seul.
>
> **Périmètre :** le dossier `frontend/` uniquement. **Aucune modification du backend ni de l'API.**
>
> **Langue :** l'interface, le code et les commentaires sont en anglais (comme l'existant). Ne pas ajouter de français dans le produit.

---

## 1. Objectif

Aujourd'hui l'accueil propose 4 cartes qui mènent à 4 pages séparées (catalogue, recherche par nom, recherche par apparence, préparation de combat). Le joueur doit choisir un outil avant de pouvoir chercher.

La cible : **2 écrans**.

1. **Accueil** : une barre de recherche (nom ou description) au-dessus du catalogue.
2. **Fiche Pokémon** : le bloc « How to beat it » en premier, les informations encyclopédiques en dessous.

Le cas d'usage qui guide tous les arbitrages : un joueur en plein combat, téléphone à côté de la console, qui veut savoir quoi faire contre un Pokémon en deux interactions (taper, toucher un résultat).

## 2. Ce qui existe (à lire avant de coder)

| Sujet | Fichier |
|---|---|
| Pages et routage par hash, sans librairie | `src/navigation.ts`, `src/App.tsx` |
| Accueil à 4 choix (à remplacer) | `src/Home.tsx` |
| Catalogue en grille | `src/features/catalog/` |
| Recherche par nom (combobox Downshift) | `src/features/suggest/` |
| Recherche par apparence | `src/features/identify/` |
| Préparation de combat | `src/features/matchup/` (`BattlePrep.tsx`, `labels.ts`, `useMatchup.ts`) |
| Fiche détaillée en modale `<dialog>` | `src/features/detail/` |
| Signalement « I didn't find my Pokémon » | `src/features/feedback/` |
| Types générés depuis l'OpenAPI | `src/api/schema.d.ts`, `src/api/client.ts` |
| Outils de test (MSW, rendu de l'app) | `src/test/` |

Endpoints utilisés, tous déjà en place :

| Endpoint | Usage dans la cible |
|---|---|
| `GET /pokemon` | grille complète quand le champ est vide |
| `GET /pokemon/suggest?q=&limit=` | résultats du mode Name (limite max : 10) |
| `GET /pokemon/identify?description=&limit=` | résultats du mode Description (limite max : 10) |
| `GET /pokemon/{ref}` | section « About » de la fiche (`ref` accepte le nom : `/pokemon/pikachu`) |
| `GET /pokemon/{ref}/matchup` | en-tête de la fiche et bloc « How to beat it » |
| `POST /feedback/missing-result` | signalement, `kind` = `name` ou `appearance` |

## 3. Routes

On garde le routage par hash (pas de librairie, pas de configuration serveur).

| Hash | Écran |
|---|---|
| `#/` | accueil, mode Name, champ vide |
| `#/?q=bulba` | accueil, mode Name, recherche « bulba » |
| `#/?mode=description&q=yellow%20mouse` | accueil, mode Description, recherche soumise |
| `#/pokemon/pikachu` | fiche de Pikachu (le `name` de l'API, pas l'id) |
| tout le reste, y compris les anciens `#/catalog`, `#/name`, `#/appearance`, `#/battle` | accueil |

Règles :

- L'état de la recherche vit dans l'URL pour que le bouton Retour depuis une fiche retrouve la recherche, et pour qu'un lien soit partageable.
- L'accueil lit `mode` et `q` au montage **et à chaque `hashchange`** (lien « Pokédex » de l'en-tête, adresse modifiée à la main, bouton Retour), et met alors le champ et les résultats à jour. Un `mode` inconnu vaut Name.
- L'accueil écrit l'URL avec `history.replaceState` (mode Name : à chaque requête envoyée après le debounce ; mode Description : à la soumission). Une frappe ne doit jamais créer d'entrée d'historique.
- Piège : `replaceState` ne déclenche pas `hashchange`, donc l'accueil ne se relit pas lui-même. Ne pas remonter l'accueil quand l'URL change (pas de `key` dérivée du hash), sinon le champ perd le focus pendant la frappe.
- Ouvrir un Pokémon est une vraie navigation (lien `<a href="#/pokemon/...">`), donc une entrée d'historique.
- **Défilement** : le routage par hash ne remet pas la page en haut. À l'ouverture d'une fiche (y compris d'un membre de la famille d'évolution), remonter en haut de page. Au retour sur l'accueil par le bouton Retour, retrouver la position de défilement d'avant (la mémoriser en quittant l'accueil, la restaurer une fois la grille affichée).

## 4. Écran 1 : accueil

```
┌──────────────────────────────────┐
│  [ Name | Description ]          │
│  [ Search a Pokémon...         ] │
│  Recently viewed: Gyarados · …   │
├──────────────────────────────────┤
│  151 Pokémon                     │
│  [card] [card] [card] [card]     │
│  [card] [card] [card] [card]     │
└──────────────────────────────────┘
```

### 4.1 Sélecteur de mode

- Deux options exclusives, `Name` (par défaut) et `Description`, accessibles au clavier et annoncées aux lecteurs d'écran (groupe de boutons radio ou équivalent).
- Changer de mode **vide le champ** et les résultats, et donne le focus au champ.
- Le placeholder suit le mode : `e.g. bulba` / `e.g. small yellow mouse with red cheeks`.

### 4.2 Mode Name

- Champ vide : la grille complète du catalogue (`GET /pokemon`), dans l'ordre du Pokédex, avec le compteur « N Pokémon ».
- Dès que le texte est cherchable (`isSearchable`) : les résultats de `GET /pokemon/suggest` (`limit=10`) **remplacent** la grille, dans l'ordre renvoyé par l'API, avec les mêmes cartes que le catalogue. Pas de filtrage côté client.
- Réutiliser le hook `useSuggestions` (debounce, annulation, liste précédente conservée pendant le chargement).
- Le nom de chaque carte met en gras les segments `matched` (composant `HighlightedName` existant).
- Un résultat approché (`match.kind === "fuzzy"`) garde la mention `did you mean?` sur sa carte, comme dans la liste actuelle.
- Touche Entrée dans le champ : ouvre le premier résultat **du texte actuellement dans le champ**. `useSuggestions` attend 200 ms et garde la liste précédente pendant le chargement : si Entrée arrive pendant ce délai, ne pas ouvrir le premier résultat de l'ancienne liste, mais attendre la réponse du texte courant (comparer avec le `query` renvoyé par le hook et `isLoading`), puis ouvrir son premier résultat. Sans résultat, ou si le texte change entre-temps, Entrée ne fait rien.
- Le combobox Downshift disparaît : les résultats sont la grille. Retirer la dépendance `downshift`.
- **Écart d'accessibilité assumé** : on perd la navigation aux flèches du combobox. Les résultats sont des liens, atteints avec Tab. En échange, la zone `aria-live` annonce le nombre de résultats (`3 results`, `1 result`).

### 4.3 Mode Description

- Recherche **à la soumission** (Entrée ou bouton `Search`), pas pendant la frappe. Réutiliser `useIdentification` avec `limit=10` et la limite de longueur existante.
- Les résultats remplacent la grille, dans l'ordre renvoyé par l'API, avec les mêmes cartes. Plus de grande carte séparée, mais **la première carte porte un libellé visible `Best match`** : dans une grille, rien d'autre ne dit quel résultat est le plus proche.
- `/pokemon/identify` renvoie toujours les plus proches, même pour une description sans rapport : `No Pokémon found.` est donc rare dans ce mode. Ne pas inventer de seuil de score côté front.
- Tant que rien n'est soumis : la grille complète, comme en mode Name.

### 4.4 Cartes

- Une carte est un lien vers `#/pokemon/<name>`. Toute la carte est cliquable, le nom accessible reste le nom du Pokémon.
- Contenu inchangé : sprite (chargement `lazy`), numéro, nom, genus, types.

### 4.5 Pokémon vus récemment

Libellé affiché : `Recently viewed`. Ce sont des fiches consultées, pas des recherches.

- Les 5 derniers Pokémon dont la fiche a été affichée, le plus récent d'abord, sans doublon.
- Stockés dans `localStorage` sous la clé `pokedex.recent` (`name`, `display_name`, `sprite`).
- Affichés sous le champ, **uniquement quand le champ est vide**, sous forme de liens vers la fiche. Rien n'est affiché si la liste est vide.
- `localStorage` indisponible ou contenu illisible : ignorer en silence, la page fonctionne sans.

### 4.6 États

| Situation | Affichage |
|---|---|
| Chargement | texte `Searching…` / `Loading the catalog…` dans une zone `aria-live="polite"` de hauteur réservée (pas de saut de mise en page) |
| Résultats affichés | le nombre de résultats (`3 results`) dans la même zone `aria-live` |
| Aucun résultat, mode Name | `No Pokémon found.` + bouton `Try a description search` (bascule de mode, règle 4.1) |
| Aucun résultat, mode Description | `No Pokémon found.` |
| Erreur API | les messages existants des hooks, en rouge ; la page reste utilisable et la recherche suivante repart normalement |
| Résultats affichés ou aucun résultat | ligne de signalement sous les résultats (composant `ReportMissingResult` existant, `key` = la requête), dans les deux modes |

Le signalement envoie `kind` (`name` ou `appearance`), la requête exacte et les ids affichés dans l'ordre. Pas de signalement sur une erreur.

## 5. Écran 2 : fiche Pokémon

```
┌──────────────────────────────────┐
│ ← All Pokémon                    │
│ [img] #130 Gyarados              │
│       Atrocious Pokémon          │
│       water · flying             │
├──────────────────────────────────┤
│ HOW TO BEAT IT                   │
│ Use         electric ×4 · rock ×2│
│ Avoid       ground ×0 · fire ×½  │
│             Immune to … (…)      │
│ Watch out   Paralyze (…)         │
├──────────────────────────────────┤
│ ABOUT                            │
│ description, stats, abilities,   │
│ evolution family                 │
└──────────────────────────────────┘
```

C'est une **page**, plus une modale : `PokemonDetailDialog` disparaît, son contenu est réutilisé.

### 5.1 Données

- Deux requêtes en parallèle : `GET /pokemon/{name}/matchup` et `GET /pokemon/{name}`. Le bloc « How to beat it » n'attend pas la seconde.
- En-tête : `matchup.pokemon` (numéro, `display_name`, genus, types, sprite). L'illustration `official_artwork` remplace le sprite quand le détail arrive. L'image a une taille fixe dès le départ (96 px de côté au plus sur mobile) : pas de saut de mise en page au remplacement.
- 404 sur le nom : `Pokémon not found.` et un lien vers l'accueil. Les hooks renvoient aujourd'hui `Server error (404).` : `useMatchup` et `usePokemonDetail` doivent distinguer le 404. Les autres erreurs gardent les messages existants.

États de la fiche :

| Situation | Affichage |
|---|---|
| Chargement | `Loading…` dans une zone `aria-live="polite"`, à la place du bloc qui charge |
| `/matchup` échoue, le détail réussit | le message d'erreur à la place de « How to beat it » ; l'en-tête est construit depuis le détail (`readable(name)` mis en capitales par CSS, comme les talents, car le détail n'a pas de `display_name`) ; « About » s'affiche |
| le détail échoue, `/matchup` réussit | l'en-tête et « How to beat it » s'affichent ; le message d'erreur à la place de « About » |
| les deux échouent | le message d'erreur et un lien vers l'accueil |

- Quand la fiche s'affiche avec succès (réponse de `/matchup`), le Pokémon est ajouté aux récents (4.5).

### 5.2 Bloc « How to beat it »

Les 7 encadrés actuels de `BattlePrep.tsx` sont regroupés en 3 lignes d'action. Toutes les données viennent de `MatchupOut`, toutes les phrases de `labels.ts`. Aucune règle de jeu n'est calculée dans le front.

| Ligne | Contenu, dans cet ordre | Si vide |
|---|---|---|
| **Use** | `weaknesses` : badge du type + multiplicateur (`×4`, `×2`), ordre de l'API | `No weakness.` (pas de conseil : ce serait une règle de jeu écrite dans le front) |
| **Avoid** | `immunities` (`×0`, avec la note « if its ability is … » quand `ability` est renseigné), puis `resistances` (`×¼`, `×½`), puis `protections` (`protectionText` + sources), puis une phrase par `pitfalls` (`pitfallText`) | ligne masquée |
| **Watch out** | `strong_against` (« Its types hit hard: » + badges), puis `threats` (`THREAT_TITLES` + sources) | ligne masquée |

- Le découpage : **Use** et **Avoid** disent quoi faire ou ne pas faire à l'adversaire (« Immune to sleep » veut dire « n'essayez pas de l'endormir », d'où `protections` dans Avoid) ; **Watch out** dit ce que l'adversaire peut vous faire.
- La ligne **Use** est toujours affichée, en premier, et doit être visible sans défilement sur un écran de 375×667. jsdom ne mesure pas la mise en page : c'est une vérification manuelle (§ 10), pas un test.
- Chaque ligne est une section avec un titre accessible.

### 5.3 Section « About »

Le contenu actuel de la modale, inchangé : description, taille, poids, habitat, stats avec barres, talents, famille d'évolution. Les membres de la famille deviennent des liens vers leur fiche ; le Pokémon courant est marqué et ne mène nulle part.

### 5.4 Navigation

- Lien `← All Pokémon` vers `#/` en haut de la fiche : il mène à l'accueil **sans recherche** (grille complète), comme son libellé l'indique. Le bouton Retour du navigateur, lui, ramène à l'accueil avec la recherche d'origine. Cette différence est voulue : ne pas aligner l'un sur l'autre.
- Le titre « Pokédex » de l'en-tête reste un lien vers `#/`. Le sous-titre actuel de l'en-tête, qui décrit les 4 features, est à raccourcir.

## 6. Contraintes transverses

- **Mobile d'abord** : tout se conçoit à 375 px de large, sans défilement horizontal. Zones tactiles d'au moins 44 px de haut. Les grandes largeurs gardent la grille actuelle (jusqu'à 5 colonnes).
- **Accessibilité au niveau de l'existant** : labels sur les champs, navigation complète au clavier, états annoncés en `aria-live`, focus visible.
- **Style** : Tailwind, palette actuelle (rouge / stone). Pas de nouvelle librairie d'UI, pas de librairie de routage.
- **Code mort** : supprimer ce qui ne sert plus (accueil à 4 choix, `FeaturePage`, pages séparées, combobox, modale, tests correspondants). Pas de code conservé « au cas où ».
- **Conventions** : celles du code existant (un dossier par feature, hooks `useX` qui renvoient `isLoading` / `errorMessage`, commentaires qui expliquent le pourquoi).

## 7. Hors périmètre

Ne pas faire, même si cela semble utile :

- comptes, connexion, favoris, équipe sauvegardée ;
- filtres du catalogue (type, habitat, légendaire) ;
- conseils tirés des statistiques (« fast », « weaker on Sp. Def ») : ce serait une nouvelle règle métier, à calculer côté API dans une version suivante ;
- recommandation d'un Pokémon à envoyer ;
- fusion automatique des deux recherches dans un seul champ sans sélecteur ;
- squelettes de chargement animés, mode sombre, animations ;
- toute modification de `src/fullstack_pokedex/`, des données ou de `schema.d.ts`.

## 8. Ordre de travail conseillé

Chaque lot laisse l'application et les tests dans un état vert.

1. **Routes** : `navigation.ts` sait lire `#/`, `#/?mode=&q=` et `#/pokemon/<name>`. Tests unitaires du parseur.
2. **Fiche en page** : nouvelle page à partir du contenu de la modale et de `BattlePrep` (bloc en 3 lignes). Les cartes du catalogue deviennent des liens.
3. **Accueil unifié** : sélecteur de mode, champ, résultats dans la grille, synchronisation avec l'URL, signalement.
4. **Récents**. Lot indépendant : c'est le premier à retirer si la V1 doit être réduite (supprimer alors 4.5 et les critères correspondants).
5. **Nettoyage** : suppression du code et des tests morts, retrait de `downshift`, mise à jour des passages de `docs/feature-*.md` qui décrivent les anciennes pages.

## 9. Critères d'acceptation

Chacun est couvert par au moins un test (Vitest + Testing Library + MSW, comme l'existant, via `renderApp`).

**Accueil**

1. À l'ouverture de `#/`, la grille complète est affichée dans l'ordre du Pokédex, sans aucun clic.
2. Taper `bulba` en mode Name remplace la grille par les résultats de `/pokemon/suggest`, dans l'ordre de l'API, avec « Bulba » en gras.
3. Un résultat approché (`bulbsaur`) porte la mention `did you mean?`.
4. Une frappe rapide n'envoie qu'une requête (debounce).
5. Entrée dans le champ ouvre la fiche du premier résultat.
6. Entrée pressée avant la réponse ouvre le premier résultat du texte tapé, jamais celui de la liste précédente.
7. Vider le champ réaffiche la grille complète.
8. En mode Description, rien n'est envoyé avant la soumission ; après soumission, les résultats de `/pokemon/identify` s'affichent dans l'ordre de l'API, et seule la première carte porte `Best match`.
9. Changer de mode vide le champ et les résultats.
10. Aucun résultat en mode Name : le message et le bouton `Try a description search`, qui bascule en mode Description.
11. Le nombre de résultats est annoncé dans la zone `aria-live`.
12. Le signalement part avec le bon `kind`, la requête et les ids affichés, dans les deux modes ; il n'est pas proposé sur une erreur.
13. API injoignable : un message, pas de plantage, et la recherche suivante fonctionne.
14. Ouvrir `#/?q=bulba` ou `#/?mode=description&q=yellow%20mouse` affiche directement la recherche correspondante.
15. Après une recherche, ouvrir une fiche puis revenir en arrière retrouve le texte et les résultats.
16. Depuis `#/?q=bulba`, le lien « Pokédex » de l'en-tête vide le champ et réaffiche la grille complète.
17. Une ancienne adresse (`#/battle`) affiche l'accueil.

**Fiche**

18. Cliquer une carte mène à `#/pokemon/<name>` ; ouvrir cette adresse directement affiche la même fiche.
19. À l'ouverture d'une fiche, la page est remontée en haut (`window.scrollTo` appelé).
20. « How to beat it » apparaît avant « About » dans le document, et s'affiche même si la requête de détail échoue.
21. Si `/matchup` échoue, l'en-tête (nom, types) et « About » s'affichent quand même, avec le message d'erreur à la place de « How to beat it ».
22. Use liste les faiblesses avec leur multiplicateur ; sans faiblesse, `No weakness.` est affiché.
23. Avoid liste immunités (avec la note de talent quand il y en a une), résistances, protections et pièges ; Watch out liste points forts et menaces. Une ligne sans contenu n'est pas rendue.
24. Un nom inconnu affiche `Pokémon not found.` et un lien vers l'accueil.
25. Un membre de la famille d'évolution mène à sa fiche ; le Pokémon courant n'est pas un lien.

**Récents**

26. Après la visite de deux fiches, l'accueil à champ vide les liste, la plus récente d'abord, sans doublon, 5 au maximum.
27. Un `localStorage` au contenu invalide ne casse pas l'accueil.

## 10. Définition de terminé

Depuis `frontend/` :

```bash
pnpm test --run   # tous les tests passent
pnpm lint         # aucune erreur Biome
pnpm build        # tsc + build Vite sans erreur
```

Et une vérification à la main, backend lancé (scripts dans `pyproject.toml`) et `pnpm dev` : à 375 px de large, parcourir « taper un nom → toucher un résultat → lire la ligne Use », puis le même parcours en mode Description. Vérifier aussi ce que les tests ne voient pas : la ligne Use visible sans défilement à 375×667, la fiche ouverte en haut de page depuis le bas de la grille, et la position de défilement retrouvée au retour. Signaler dans le compte rendu ce qui a été vérifié à la main et ce qui ne l'a pas été.

Compte rendu attendu en fin de travail : les fichiers créés, modifiés et supprimés ; tout écart par rapport à cette spec, avec sa raison ; les critères d'acceptation non couverts, s'il y en a.
