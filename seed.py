"""
seed.py - fills the database with test data so the demo is predictable.

Run it with:   python seed.py
It DELETES the old database and creates a fresh one.

All dates are relative to "today", so the demo always has future slots.
"""

import os
import random
from datetime import datetime, timedelta

from database import DB_PATH, create_tables, get_connection

TIME_FORMAT = "%Y-%m-%d %H:%M"

USERS = ["Alex", "Maria", "Ivan", "Georgi"]

# name, address, surface, capacity, price per hour (BGN)
FIELDS = [
    ("Arena Mladost", "Sofia, Mladost 1, bul. Andrey Lyapchev 10", "artificial grass", 12, 120),
    ("Sport Park Lozenets", "Sofia, Lozenets, ul. Krastyo Sarafov 5", "artificial grass", 12, 100),
    ("Futbolna Baza Lyulin", "Sofia, Lyulin 5, ul. Pancho Vladigerov 20", "rubber", 10, 80),
]


def fmt(dt):
    """datetime -> 'YYYY-MM-DD HH:MM'"""
    return dt.strftime(TIME_FORMAT)


def seed():
    # Start from an empty database every time.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    create_tables()

    conn = get_connection()
    rnd = random.Random(42)  # fixed seed -> same "random" data every time

    # --- users ---
    for name in USERS:
        conn.execute("INSERT INTO users (name) VALUES (?)", (name,))

    # --- fields ---
    for field in FIELDS:
        conn.execute(
            "INSERT INTO fields (name, address, surface, capacity, price_per_hour) "
            "VALUES (?, ?, ?, ?, ?)",
            field,
        )

    # --- slots: next 7 days, one-hour slots ---
    # Weekdays: 17:00 - 22:00, weekends: 10:00 - 22:00
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    for day in range(7):
        date = tomorrow + timedelta(days=day)
        is_weekend = date.weekday() >= 5  # 5 = Saturday, 6 = Sunday
        first_hour = 10 if is_weekend else 17
        for field_id in range(1, len(FIELDS) + 1):
            for hour in range(first_hour, 22):
                start = date.replace(hour=hour)
                end = start + timedelta(hours=1)
                # About 30% of slots are already booked by someone.
                status = "booked" if rnd.random() < 0.3 else "free"
                conn.execute(
                    "INSERT INTO slots (field_id, start_time, end_time, status) VALUES (?, ?, ?, ?)",
                    (field_id, fmt(start), fmt(end), status),
                )

    # --- open games ---
    # (field_id, days from tomorrow, hour, organizer_id, name, level, joined)
    games = [
        (1, 0, 19, 2, "Evening kickabout", "intermediate", 7),
        (2, 1, 20, 3, "Lozenets evening game", "beginner", 10),
        (1, 2, 18, 4, "Fast and friendly", "advanced", 4),
        (3, 3, 19, 2, "Lyulin small game", "beginner", 6),
    ]
    now = datetime.now()
    for field_id, day, hour, organizer_id, name, level, joined in games:
        start = fmt((tomorrow + timedelta(days=day)).replace(hour=hour))
        slot = conn.execute(
            "SELECT id FROM slots WHERE field_id = ? AND start_time = ?", (field_id, start)
        ).fetchone()
        capacity = conn.execute("SELECT capacity FROM fields WHERE id = ?", (field_id,)).fetchone()[0]
        # Default deadline: 24 hours before the start.
        deadline = datetime.strptime(start, TIME_FORMAT) - timedelta(hours=24)
        # The first game has a deadline in a few minutes - useful to demo
        # automatic cancellation later (step 7).
        if day == 0:
            deadline = now + timedelta(minutes=5)

        conn.execute("UPDATE slots SET status = 'open_game' WHERE id = ?", (slot["id"],))
        cur = conn.execute(
            "INSERT INTO games (slot_id, organizer_id, name, level, capacity, joined, deadline) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (slot["id"], organizer_id, name, level, capacity, joined, fmt(deadline)),
        )
        # The organizer's booking holds all the already joined seats
        # (the organizer plus their friends).
        conn.execute(
            "INSERT INTO bookings (user_id, slot_id, game_id, seats) VALUES (?, ?, ?, ?)",
            (organizer_id, slot["id"], cur.lastrowid, joined),
        )

    conn.commit()
    conn.close()
    print("Database created:", DB_PATH)


if __name__ == "__main__":
    seed()
