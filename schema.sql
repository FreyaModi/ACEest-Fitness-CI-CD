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

CREATE TABLE IF NOT EXISTS workouts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id    INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    date         TEXT    NOT NULL,
    workout_type TEXT    NOT NULL,
    duration_min INTEGER NOT NULL,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS exercises (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts (id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    sets       INTEGER NOT NULL,
    reps       INTEGER NOT NULL,
    weight     REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS metrics (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    date      TEXT    NOT NULL,
    weight    REAL,
    waist     REAL,
    bodyfat   REAL
);
