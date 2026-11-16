You are labeling Pokémon move and ability effects for a search engine. A human will review every label. The labels will then answer questions such as "how can I put the opponent to sleep?", "what prevents poisoning?", "which moves lower Defense?" or "what is immune to Ground moves?".

## Input
The attached file `pokedex.json` has four keys: `metadata`, `pokemon`, `moves`, `abilities`.
Label ONLY the items in `moves` (164) and `abilities` (114). Ignore `pokemon`, and ignore the `learned_by_pokemon` and `pokemon` lists: they are not effect texts.
For each move, use `name`, `damage_class`, `effect_chance`, `short_effect`, `effect`.
For each ability, use `name`, `short_effect`, `effect`. Abilities have no `effect_chance`.

## Task
For each item, read its effect texts (`short_effect` and `effect`) and return the effect relations they state.

## Rules
1. Use ONLY the texts provided. Do not use your knowledge of the games: if the text does not say it, do not tag it.
2. Use only this closed vocabulary. A tag is written `relation:effect`.
   Relations:
   - `inflicts`: causes the effect on the target (or, for an ability, on the Pokémon that triggers it)
   - `self`: causes the effect on the user or holder itself
   - `prevents`: stops the user or holder from getting the effect
   - `cures`: removes the effect
   - `requires`: only works, or works better, if the target, or the user/holder itself, has the effect
   - `lowers`: lowers a stat of the target (or, for an ability, of the opponents)
   - `raises`: raises a stat of the user or holder itself, by stages or by a multiplier
   - `reduces`: reduces the damage taken by the user, the holder or its side
   - `immune`: the user or holder takes no damage at all from a source
   - `reflects`: gives a status received by the holder back to the Pokémon that inflicted it
   Effects, each with the only relations it can be used with:
   - Statuses `sleep`, `poison`, `paralysis`, `burn`, `freeze`, `confusion`, `any`: `inflicts`, `self`, `prevents`, `cures`, `requires`, `reflects`.
     Use `any` when the text says "major status ailment" (or "major status effect") without naming the statuses. If either text uses that wording, use `any` only, and do not add one tag per status. `any` does not include confusion. "Badly poisoned" counts as `poison`.
   - `flinch`: `inflicts`, `prevents`, `requires`.
   - `infatuation`: `inflicts`, `prevents`.
   - `trap` (the target cannot flee or switch out): `inflicts`.
   - `one-hit-ko`: `inflicts`, `prevents`.
   - `multi-hit` (the move hits several times in one turn): `inflicts`.
   - `disable` (a move of the target can no longer be used): `inflicts`.
   - `switch` (the target is forced to switch out): `inflicts`.
   - `heal` (restores HP of the user or holder, including by draining the target): `self`.
   - `stat-drop` (having one's stats lowered): `prevents`.
   - `stat-change` (stat modifiers, raised or lowered): `cures`.
   - `damage`: `reduces`. Only partial reductions: for a full immunity, use `immune`.
   - Sources `fire`, `ground`, `electric`, `water` (moves of that type), `sound` (sound-based moves), `moves` (all moves), `weather` (weather damage), `recoil` (recoil damage), `critical` (critical hits): `immune`.
     A move or ability that absorbs moves of a type is immune to that type. If the immunity lasts a limited time or covers only one weather, state it in `comment`.
   - Stats `attack`, `defense`, `special-attack`, `special-defense`, `speed`, `accuracy`, `evasion`: `lowers`, `raises`.
   - `critical` (critical-hit rate): `raises`. As a source (critical hits): `immune`.
   Everything else is NOT in the vocabulary: never tag it. This includes plain damage, power or damage boosts, recoil taken, charging turns, summoning weather, and immunities to anything that is not a listed source.
   Tags describe what happens in a fight between Pokémon. Do not tag overworld effects, nor effects that only end or flee a wild battle.
   If the effect applies only under a condition (a weather, a type, one stat only, allies only), tag it and state the condition in `comment`.
3. `chance`:
   - If the text gives a percentage, use it.
   - If the text says "Has a chance" without a number, use the move's `effect_chance` field.
   - If the effect is a main effect of a status move (`damage_class` is `status`), use 100.
   - If a single roll can cause one of several statuses ("burn, freeze, or paralyze"), divide the chance equally between the tags (one decimal at most) and say so in `comment`.
   - If the text gives no chance, use null.
4. `trigger`: `move_hit` for moves, `on_contact` when an ability affects a Pokémon that touches the holder, `other` otherwise.
5. `evidence`: copy the exact words from the text that justify the tag. It must be an exact substring of `short_effect` or `effect`.
6. If the text talks about an effect of the vocabulary in a way that does not fit it, return no tag for it and explain in `comment`. Never force a tag.
7. If both texts are null, return no tags, with `comment` = "no text".
8. `confidence`: `high` when the text states it plainly, `low` otherwise.

## Output format
Each item produces exactly one object with these keys, and no others:
- `entity_type`: `"move"` or `"ability"`, depending on the list the item comes from.
- `name`: the item's `name`, copied exactly from the file.
- `tags`: a list of tag objects, empty if the texts state no relation of the vocabulary. Each tag object has exactly these keys:
  - `tag`: a string `relation:effect` from the vocabulary (rule 2).
  - `chance`: a number from 0 to 100, or null (rule 3).
  - `trigger`: `"move_hit"`, `"on_contact"` or `"other"` (rule 4).
  - `evidence`: an exact substring of `short_effect` or `effect` (rule 5).
- `comment`: a short string, or null (rules 3, 6 and 7).
- `confidence`: `"high"` or `"low"` (rule 8).

## Examples
`effect` is omitted for brevity. `short_effect` is copied exactly from the file, typos included. `entity_type` is shown only to tell which list the item comes from.

Input: {"entity_type": "move", "name": "hypnosis", "damage_class": "status", "effect_chance": null, "short_effect": "Puts the target to sleep."}
Output: {"entity_type": "move", "name": "hypnosis", "tags": [{"tag": "inflicts:sleep", "chance": 100, "trigger": "move_hit", "evidence": "Puts the target to sleep."}], "comment": null, "confidence": "high"}

Input: {"entity_type": "move", "name": "thunderbolt", "damage_class": "special", "effect_chance": 10, "short_effect": "Has a chance to paralyze the target."}
Output: {"entity_type": "move", "name": "thunderbolt", "tags": [{"tag": "inflicts:paralysis", "chance": 10, "trigger": "move_hit", "evidence": "Has a chance to paralyze the target."}], "comment": null, "confidence": "high"}

Input: {"entity_type": "move", "name": "rest", "damage_class": "status", "effect_chance": null, "short_effect": "User sleeps for two turns, completely healing itself."}
Output: {"entity_type": "move", "name": "rest", "tags": [{"tag": "self:sleep", "chance": 100, "trigger": "move_hit", "evidence": "User sleeps for two turns"}, {"tag": "self:heal", "chance": 100, "trigger": "move_hit", "evidence": "completely healing itself"}], "comment": "effect also says sleep replaces another major status effect; replacement is not a cure, not tagged", "confidence": "high"}

Input: {"entity_type": "move", "name": "dream-eater", "damage_class": "special", "effect_chance": null, "short_effect": "Only works on sleeping Pokémon. Drains half the damage inflicted to heal the user."}
Output: {"entity_type": "move", "name": "dream-eater", "tags": [{"tag": "requires:sleep", "chance": null, "trigger": "move_hit", "evidence": "Only works on sleeping Pokémon."}, {"tag": "self:heal", "chance": null, "trigger": "move_hit", "evidence": "Drains half the damage inflicted to heal the user."}], "comment": null, "confidence": "high"}

Input: {"entity_type": "move", "name": "swords-dance", "damage_class": "status", "effect_chance": null, "short_effect": "Raises the user’s Attack by two stages."}
Output: {"entity_type": "move", "name": "swords-dance", "tags": [{"tag": "raises:attack", "chance": 100, "trigger": "move_hit", "evidence": "Raises the user’s Attack by two stages."}], "comment": null, "confidence": "high"}

Input: {"entity_type": "move", "name": "bite", "damage_class": "physical", "effect_chance": 30, "short_effect": "Has a chance to make the target flinch."}
Output: {"entity_type": "move", "name": "bite", "tags": [{"tag": "inflicts:flinch", "chance": 30, "trigger": "move_hit", "evidence": "Has a chance to make the target flinch."}], "comment": null, "confidence": "high"}

Input: {"entity_type": "move", "name": "pound", "damage_class": "physical", "effect_chance": null, "short_effect": "Inflicts regular damage with no additional effect."}
Output: {"entity_type": "move", "name": "pound", "tags": [], "comment": null, "confidence": "high"}

Input: {"entity_type": "ability", "name": "insomnia", "short_effect": "Prevents sleep."}
Output: {"entity_type": "ability", "name": "insomnia", "tags": [{"tag": "prevents:sleep", "chance": null, "trigger": "other", "evidence": "Prevents sleep."}], "comment": null, "confidence": "high"}

Input: {"entity_type": "ability", "name": "effect-spore", "short_effect": "Has a 30% chance of inflcting either paralysis, poison, or sleep on attacking Pokémon on contact."}
Output: {"entity_type": "ability", "name": "effect-spore", "tags": [{"tag": "inflicts:paralysis", "chance": 10, "trigger": "on_contact", "evidence": "Has a 30% chance of inflcting either paralysis, poison, or sleep"}, {"tag": "inflicts:poison", "chance": 10, "trigger": "on_contact", "evidence": "Has a 30% chance of inflcting either paralysis, poison, or sleep"}, {"tag": "inflicts:sleep", "chance": 10, "trigger": "on_contact", "evidence": "Has a 30% chance of inflcting either paralysis, poison, or sleep"}], "comment": "one 30% roll split across three statuses", "confidence": "high"}

Input: {"entity_type": "ability", "name": "synchronize", "short_effect": "Copies burns, paralysis, and poison received onto the Pokémon that inflicted them."}
Output: {"entity_type": "ability", "name": "synchronize", "tags": [{"tag": "reflects:burn", "chance": null, "trigger": "other", "evidence": "Copies burns, paralysis, and poison received onto the Pokémon that inflicted them."}, {"tag": "reflects:paralysis", "chance": null, "trigger": "other", "evidence": "Copies burns, paralysis, and poison received onto the Pokémon that inflicted them."}, {"tag": "reflects:poison", "chance": null, "trigger": "other", "evidence": "Copies burns, paralysis, and poison received onto the Pokémon that inflicted them."}], "comment": "only statuses received directly from another Pokémon", "confidence": "high"}

Input: {"entity_type": "ability", "name": "early-bird", "short_effect": "Makes sleep pass twice as quickly."}
Output: {"entity_type": "ability", "name": "early-bird", "tags": [], "comment": "shortens sleep duration; neither prevents nor cures it", "confidence": "low"}

Input: {"entity_type": "ability", "name": "guts", "short_effect": "Increases Attack to 1.5× with a major status ailment."}
Output: {"entity_type": "ability", "name": "guts", "tags": [{"tag": "requires:any", "chance": null, "trigger": "other", "evidence": "with a major status ailment"}, {"tag": "raises:attack", "chance": null, "trigger": "other", "evidence": "Increases Attack to 1.5×"}], "comment": null, "confidence": "high"}

Input: {"entity_type": "ability", "name": "thick-fat", "short_effect": "Halves damage from Fire and Ice moves."}
Output: {"entity_type": "ability", "name": "thick-fat", "tags": [{"tag": "reduces:damage", "chance": null, "trigger": "other", "evidence": "Halves damage from Fire and Ice moves."}], "comment": "Fire and Ice moves only", "confidence": "high"}

## Procedure
1. Process the items in batches of 25, moves first, then abilities, in file order.
2. Never skip an item: every item gets an object, even with an empty `tags` list.
3. At the end, check that there are exactly 278 objects (164 moves + 114 abilities) and that every name appears exactly once. Complete any missing item before finishing.

## Output
Write a file `tags_llm.json` containing ONLY a JSON array of the objects described in "Output format", one per item, in file order.
If you cannot write files, return the array in your answer, split across several messages if needed. Never summarize or shorten it.