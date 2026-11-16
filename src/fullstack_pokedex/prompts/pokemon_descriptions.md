# Generation prompt: `pokemon_descriptions.json`

Prompt used to generate [`data/pokemon_descriptions.json`](../../../data/pokemon_descriptions.json). It is kept here so the file can be regenerated or extended the same way. See [`data/README.md`](../../../data/README.md) for how the file is used and reviewed.

> ⚠️ **À COMPLÉTER** si le prompt a été modifié au moment de la génération : ce fichier doit refléter le prompt **réellement** utilisé.

## Input

The prompt was run in batches of 15 to 25 Pokémon, keeping each evolution line in the same batch so that similar-looking Pokémon could be told apart. `{{POKEMON_BATCH_JSON}}` is a JSON array built from `pokedex.json`:

```json
[
  {"id": 29, "name": "nidoran-f", "color": "blue", "shape": "quadruped", "height_m": 0.4, "genus": "Poison Pin Pokémon"}
]
```

Types are deliberately left out: they lead the model to write "poison type" instead of describing what can be seen.

## Prompt

````text
You are helping build a search feature for a Pokédex app covering the original 151 Pokémon.
Users will type a free-text description of a Pokémon they saw (for example
"small yellow mouse with red cheeks") and the app will compare it, using sentence
embeddings, to reference descriptions of each Pokémon. Your job is to write those
reference descriptions.

How the descriptions will be used, which explains the rules below:
- Each description is turned into a single embedding vector. Anything that is not
  about appearance dilutes the vector and makes matching worse.
- Users describe what they noticed at a glance, in everyday words, often imprecisely.
- Similar-looking Pokémon (for example Nidorina and Nidorino, or the three members
  of an evolution line) must remain distinguishable.

For each Pokémon in the input, write exactly 3 descriptions:
1. "glance": what a person would notice in one second. Overall body type, main color,
   and the single most striking feature. 5 to 10 words.
2. "detailed": the key visual features in order of how noticeable they are: body
   shape and posture, colors (main and secondary), then distinctive parts (ears, tail,
   wings, horns, shell, markings, flames, leaves, etc.). 12 to 25 words.
3. "everyday": the same Pokémon described the way a child or a non-fan would, using
   comparisons to real animals or objects ("looks like a ..."). 8 to 20 words.

Rules:
- Appearance only. No abilities, behavior, habitat, lore, evolution, game mechanics,
  type names (do not write "fire type", but do write "flame on its tail"), or the
  Pokémon's name.
- Plain, concrete, everyday English. Prefer common words ("shell", "spikes", "tail")
  over jargon.
- Put the features that distinguish this Pokémon from similar-looking ones (especially
  its own evolution line) explicitly in the "detailed" description.
- Use the provided data (color, shape, height) as a consistency check: the main color
  you describe should be compatible with "color", and size words with "height_m"
  (under 0.7 m: tiny or small; 0.7 to 1.5 m: medium; over 1.5 m: large; over 3 m: huge).
  If your visual knowledge clearly disagrees with the data (for example, the data says
  "brown" but the Pokémon is mostly yellow with brown parts), describe what a person
  would actually see and explain the disagreement in "notes".
- Do not invent features. If you are not confident about a Pokémon's appearance, set
  "confidence" to "low" and describe only what you are sure of.
- Each description is a single line with no trailing period, lowercase except proper
  nouns, and features separated by commas or semicolons.

Output: a JSON array, one object per input Pokémon, in the same order, with exactly
these fields and nothing else around the JSON:
{
  "id": <integer, copied from the input>,
  "name": <string, copied from the input>,
  "glance": <string>,
  "detailed": <string>,
  "everyday": <string>,
  "confidence": "high" | "medium" | "low",
  "notes": <string, empty if nothing to report>
}

Example of the expected style (for illustration only, not part of the input):
{
  "id": 25,
  "name": "pikachu",
  "glance": "small yellow mouse with red cheeks",
  "detailed": "small chubby yellow rodent; red circles on its cheeks; long pointed ears with black tips; flat tail shaped like a lightning bolt; brown stripes on its back",
  "everyday": "looks like a cute yellow mouse or hamster with a zigzag tail",
  "confidence": "high",
  "notes": ""
}

Input Pokémon:
<pokemon>
{{POKEMON_BATCH_JSON}}
</pokemon>
````
