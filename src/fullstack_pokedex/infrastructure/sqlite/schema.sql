DROP TABLE IF EXISTS effect_tag;
DROP TABLE IF EXISTS appearance_index;
DROP TABLE IF EXISTS pokemon_appearance;
DROP TABLE IF EXISTS pokemon_move;
DROP TABLE IF EXISTS pokemon_ability;
DROP TABLE IF EXISTS pokemon_type;
DROP TABLE IF EXISTS move;
DROP TABLE IF EXISTS ability;
DROP TABLE IF EXISTS pokemon;
DROP TABLE IF EXISTS type;

CREATE TABLE type (
    name TEXT PRIMARY KEY
);

CREATE TABLE pokemon (
    id                   INTEGER PRIMARY KEY,
    name                 TEXT    NOT NULL UNIQUE,
    height_decimetres    INTEGER NOT NULL,
    weight_hectograms    INTEGER NOT NULL,
    base_experience      INTEGER NOT NULL,
    -- stats
    hp                   INTEGER NOT NULL,
    attack               INTEGER NOT NULL,
    defense              INTEGER NOT NULL,
    special_attack       INTEGER NOT NULL,
    special_defense      INTEGER NOT NULL,
    speed                INTEGER NOT NULL,
    -- species
    genus                TEXT    NOT NULL,
    description          TEXT    NOT NULL,
    generation           TEXT    NOT NULL,
    color                TEXT    NOT NULL,
    shape                TEXT    NOT NULL,
    habitat              TEXT    NOT NULL,
    is_legendary         INTEGER NOT NULL CHECK (is_legendary IN (0, 1)),
    is_mythical          INTEGER NOT NULL CHECK (is_mythical IN (0, 1)),
    evolution_chain_id   INTEGER NOT NULL,
    -- images
    sprite_url           TEXT    NOT NULL,
    official_artwork_url TEXT    NOT NULL
);
CREATE INDEX idx_pokemon_evolution_chain ON pokemon (evolution_chain_id);

CREATE TABLE move (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    type          TEXT    NOT NULL REFERENCES type (name),
    damage_class  TEXT    NOT NULL CHECK (damage_class IN ('physical', 'special', 'status')),
    power         INTEGER,
    accuracy      INTEGER,
    pp            INTEGER NOT NULL,
    priority      INTEGER NOT NULL,
    effect_chance INTEGER,
    effect        TEXT    NOT NULL,
    short_effect  TEXT    NOT NULL,
    generation    TEXT    NOT NULL
);
CREATE INDEX idx_move_type ON move (type);

CREATE TABLE ability (
    id             INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL UNIQUE,
    effect         TEXT    NOT NULL,
    short_effect   TEXT    NOT NULL,
    generation     TEXT    NOT NULL,
    is_main_series INTEGER NOT NULL CHECK (is_main_series IN (0, 1))
);

CREATE TABLE pokemon_type (
    pokemon_id INTEGER NOT NULL REFERENCES pokemon (id) ON DELETE CASCADE,
    slot       INTEGER NOT NULL CHECK (slot IN (1, 2)),
    type       TEXT    NOT NULL REFERENCES type (name),
    PRIMARY KEY (pokemon_id, slot),
    UNIQUE (pokemon_id, type)
);
CREATE INDEX idx_pokemon_type_type ON pokemon_type (type);

CREATE TABLE pokemon_move (
    pokemon_id INTEGER NOT NULL REFERENCES pokemon (id) ON DELETE CASCADE,
    move_id    INTEGER NOT NULL REFERENCES move (id) ON DELETE CASCADE,
    PRIMARY KEY (pokemon_id, move_id)
);
CREATE INDEX idx_pokemon_move_move ON pokemon_move (move_id);

CREATE TABLE pokemon_ability (
    pokemon_id INTEGER NOT NULL REFERENCES pokemon (id) ON DELETE CASCADE,
    ability_id INTEGER NOT NULL REFERENCES ability (id) ON DELETE CASCADE,
    PRIMARY KEY (pokemon_id, ability_id)
);
CREATE INDEX idx_pokemon_ability_ability ON pokemon_ability (ability_id);

-- Appearance search: one reference vector per Pokémon (see data/README.md).
CREATE TABLE pokemon_appearance (
    pokemon_id     INTEGER PRIMARY KEY REFERENCES pokemon (id) ON DELETE CASCADE,
    reference_text TEXT    NOT NULL,
    embedding      BLOB    NOT NULL  -- float32 values, native byte order
);

-- Which embedding model produced the vectors: queries must use the same one.
CREATE TABLE appearance_index (
    model      TEXT    NOT NULL,
    dimensions INTEGER NOT NULL
);

-- Effect tags of moves and abilities, e.g. `immune:ground` for Levitate
-- (see data/README.md). entity_id is a move id or an ability id, by entity_type.
CREATE TABLE effect_tag (
    entity_type TEXT    NOT NULL CHECK (entity_type IN ('move', 'ability')),
    entity_id   INTEGER NOT NULL,
    tag         TEXT    NOT NULL,
    chance      REAL,
    trigger     TEXT    NOT NULL CHECK (trigger IN ('move_hit', 'on_contact', 'other')),
    evidence    TEXT    NOT NULL
);
CREATE INDEX idx_effect_tag_tag ON effect_tag (tag);
