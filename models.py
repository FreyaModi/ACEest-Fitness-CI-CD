"""Data-access layer: all SQL used by the API lives here."""

import sqlite3

from database import get_db

CLIENT_COLUMNS = (
    "name", "age", "height", "weight", "program", "calories",
    "target_weight", "target_adherence", "membership_status", "membership_end",
)


class NotFoundError(LookupError):
    """Raised when a requested record does not exist."""


class ConflictError(Exception):
    """Raised when a record would violate a uniqueness constraint."""


def _check_columns(fields):
    # Column names are interpolated into SQL, so only allow known ones.
    unknown = set(fields) - set(CLIENT_COLUMNS)
    if unknown:
        raise ValueError(f"Unknown client columns: {sorted(unknown)}")


# ---------- CLIENTS ----------

def list_clients():
    rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def get_client(name):
    row = get_db().execute("SELECT * FROM clients WHERE name = ?",
                           (name,)).fetchone()
    if row is None:
        raise NotFoundError(f"Client '{name}' not found")
    return dict(row)


def create_client(fields):
    _check_columns(fields)
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    db = get_db()
    try:
        db.execute(f"INSERT INTO clients ({columns}) VALUES ({placeholders})",
                   tuple(fields.values()))
    except sqlite3.IntegrityError:
        raise ConflictError(f"Client '{fields['name']}' already exists") from None
    db.commit()
    return get_client(fields["name"])


def update_client(name, fields):
    client = get_client(name)
    if fields:
        _check_columns(fields)
        assignments = ", ".join(f"{column} = ?" for column in fields)
        db = get_db()
        db.execute(f"UPDATE clients SET {assignments} WHERE id = ?",
                   (*fields.values(), client["id"]))
        db.commit()
    return get_client(client["name"])


def delete_client(name):
    client = get_client(name)
    db = get_db()
    db.execute("DELETE FROM clients WHERE id = ?", (client["id"],))
    db.commit()


# ---------- WEEKLY PROGRESS ----------

def add_progress(client_id, week, adherence):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO progress (client_id, week, adherence) VALUES (?, ?, ?)",
        (client_id, week, adherence))
    db.commit()
    return {"id": cursor.lastrowid, "week": week, "adherence": adherence}


def list_progress(client_id):
    rows = get_db().execute(
        "SELECT id, week, adherence FROM progress WHERE client_id = ? ORDER BY id",
        (client_id,)).fetchall()
    return [dict(row) for row in rows]
