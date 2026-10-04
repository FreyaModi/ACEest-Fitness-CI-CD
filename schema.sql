-- ACEest Fitness & Gym database schema (SQLite).
-- Every statement is idempotent so the schema can be applied on each start-up.

CREATE TABLE IF NOT EXISTS clients (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    age               INTEGER,
    height            REAL,
    weight            REAL,
    program           TEXT,
    calories          INTEGER,
    target_weight     REAL,
    target_adherence  INTEGER,
    membership_status TEXT    NOT NULL DEFAULT 'Active',
    membership_end    TEXT,
    created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    week       TEXT    NOT NULL,
    adherence  INTEGER NOT NULL CHECK (adherence BETWEEN 0 AND 100)
);
