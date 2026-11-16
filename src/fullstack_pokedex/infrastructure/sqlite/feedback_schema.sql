-- Product feedback: user data that cannot be rebuilt.
-- Kept in its own database (feedback.db), NOT in pokedex.db, which
-- `pokedex-import` drops and rebuilds. Never DROP anything here.

CREATE TABLE IF NOT EXISTS missing_result_report (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('name', 'appearance')),
    query       TEXT NOT NULL,
    -- JSON list of Pokémon ids, in display order. No foreign key: the
    -- Pokémon live in another database (checked by the use case instead).
    shown_ids   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))  -- UTC
);
