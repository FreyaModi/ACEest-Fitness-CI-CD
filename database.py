"""SQLite connection management for the Flask application."""

import os
import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    """Return the request-scoped SQLite connection, opening it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables that do not exist yet."""
    db = get_db()
    with current_app.open_resource("schema.sql") as schema:
        db.executescript(schema.read().decode("utf-8"))


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the database tables."""
    init_db()
    click.echo("Initialised the database.")


def init_app(app):
    """Register database hooks and make sure the schema exists."""
    db_dir = os.path.dirname(os.path.abspath(app.config["DATABASE"]))
    os.makedirs(db_dir, exist_ok=True)
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    with app.app_context():
        init_db()
