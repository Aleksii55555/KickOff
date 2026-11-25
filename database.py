"""
database.py - everything about the SQLite database.

We use Python's built-in `sqlite3` module, so nothing extra to install.
The whole database is ONE file: data/kickoff.db

Dates and times are stored as text in the format "YYYY-MM-DD HH:MM",
for example "2026-11-27 19:00". Text in this format sorts correctly,
so we can compare times with < and > directly in SQL.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "kickoff.db")


def get_connection():
    """Open a connection to the database.

    row_factory = sqlite3.Row lets us read columns by name: row["name"]
    instead of by position: row[1].
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# All tables of the project. Some of them (pending_actions, notifications)
# are used in later steps, but it is simpler to create everything at once.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fields (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    address         TEXT NOT NULL,
    surface         TEXT NOT NULL,      -- e.g. 'artificial grass'
    capacity        INTEGER NOT NULL,   -- players for a full game, e.g. 12
    price_per_hour  REAL NOT NULL       -- in BGN
);

-- One row = one hour on one field.
CREATE TABLE IF NOT EXISTS slots (
    id          INTEGER PRIMARY KEY,
    field_id    INTEGER NOT NULL REFERENCES fields(id),
    start_time  TEXT NOT NULL,          -- 'YYYY-MM-DD HH:MM'
    end_time    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'free'   -- 'free' / 'booked' / 'open_game'
);

-- An open game: people join until it is full (e.g. 12/12).
CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY,
    slot_id       INTEGER NOT NULL REFERENCES slots(id),
    organizer_id  INTEGER NOT NULL REFERENCES users(id),
    name          TEXT NOT NULL,        -- short name, max 40 chars
    level         TEXT NOT NULL,        -- 'beginner' / 'intermediate' / 'advanced'
    capacity      INTEGER NOT NULL,
    joined        INTEGER NOT NULL,     -- how many players have joined
    deadline      TEXT NOT NULL,        -- if not full by then -> cancelled
    status        TEXT NOT NULL DEFAULT 'open'  -- 'open' / 'confirmed' / 'cancelled'
);

-- Who booked what. Either a whole slot (game_id is NULL) or seats in a game.
CREATE TABLE IF NOT EXISTS bookings (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id),
    slot_id   INTEGER NOT NULL REFERENCES slots(id),
    game_id   INTEGER REFERENCES games(id),
    seats     INTEGER NOT NULL,
    status    TEXT NOT NULL DEFAULT 'active'   -- 'active' / 'cancelled'
);

-- Actions the AI has PROPOSED, waiting for the user to press "Confirm".
CREATE TABLE IF NOT EXISTS pending_actions (
    id          TEXT PRIMARY KEY,       -- random id
    user_id     INTEGER NOT NULL REFERENCES users(id),
    action      TEXT NOT NULL,          -- e.g. 'book_field'
    params      TEXT NOT NULL,          -- JSON text
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'  -- 'pending' / 'done' / 'rejected' / 'expired'
);

CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    game_id     INTEGER REFERENCES games(id),
    text        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0
);
"""


def create_tables():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
