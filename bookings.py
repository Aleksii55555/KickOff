"""
bookings.py - functions that READ data about fields, slots and games.

Later (step 2) the AI will call these functions as "tools".
They only read - they never change anything in the database.

Every function returns a list of plain dictionaries, because that is easy
to turn into JSON and send to the AI.
"""

from datetime import datetime, timedelta

from database import get_connection

TIME_FORMAT = "%Y-%m-%d %H:%M"
MAX_RESULTS = 10


def _to_dicts(rows):
    """Turn database rows into dictionaries and add the day name.

    The AI is bad at working out the weekday from a date, so we add it
    ourselves: '2026-11-27 19:00' -> 'Friday'.
    """
    result = []
    for row in rows:
        item = dict(row)
        start = datetime.strptime(item["start_time"], TIME_FORMAT)
        item["day"] = start.strftime("%A")
        result.append(item)
    return result


def _default_dates(date_from, date_to):
    """If no dates are given, search from today for the next 7 days."""
    today = datetime.now().strftime("%Y-%m-%d")
    if date_from is None:
        date_from = today
    if date_to is None:
        start = datetime.strptime(date_from, "%Y-%m-%d")
        date_to = (start + timedelta(days=7)).strftime("%Y-%m-%d")
    return date_from, date_to


def search_free_slots(date_from=None, date_to=None, earliest_hour=0, latest_hour=23, field_name=None):
    """Find free slots to book a WHOLE field.

    date_from, date_to: 'YYYY-MM-DD' (both included). Optional.
    earliest_hour, latest_hour: only slots that START between these hours.
    field_name: optional, part of the field's name, e.g. 'Mladost'.
    """
    date_from, date_to = _default_dates(date_from, date_to)
    now = datetime.now().strftime(TIME_FORMAT)

    sql = """
        SELECT slots.id AS slot_id, fields.name AS field, fields.address,
               slots.start_time, slots.end_time, fields.price_per_hour AS price
        FROM slots
        JOIN fields ON fields.id = slots.field_id
        WHERE slots.status = 'free'
          AND slots.start_time > ?                      -- not in the past
          AND date(slots.start_time) BETWEEN ? AND ?
          AND CAST(strftime('%H', slots.start_time) AS INTEGER) BETWEEN ? AND ?
    """
    params = [now, date_from, date_to, earliest_hour, latest_hour]

    if field_name:
        sql += " AND fields.name LIKE ?"
        params.append(f"%{field_name}%")

    sql += " ORDER BY slots.start_time LIMIT ?"
    params.append(MAX_RESULTS)

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return _to_dicts(rows)


def search_open_games(players=1, date_from=None, date_to=None, earliest_hour=0, latest_hour=23):
    """Find open games that still have room for `players` people."""
    date_from, date_to = _default_dates(date_from, date_to)
    now = datetime.now().strftime(TIME_FORMAT)

    sql = """
        SELECT games.id AS game_id, games.name, games.level, fields.name AS field,
               slots.start_time, slots.end_time,
               games.joined, games.capacity,
               games.capacity - games.joined AS free_places,
               games.deadline
        FROM games
        JOIN slots ON slots.id = games.slot_id
        JOIN fields ON fields.id = slots.field_id
        WHERE games.status = 'open'
          AND games.deadline > ?                        -- still collecting players
          AND games.capacity - games.joined >= ?        -- enough room for the group
          AND date(slots.start_time) BETWEEN ? AND ?
          AND CAST(strftime('%H', slots.start_time) AS INTEGER) BETWEEN ? AND ?
        ORDER BY slots.start_time
        LIMIT ?
    """
    params = [now, players, date_from, date_to, earliest_hour, latest_hour, MAX_RESULTS]

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return _to_dicts(rows)


def get_my_bookings(user_id):
    """All active bookings of one user."""
    sql = """
        SELECT bookings.id AS booking_id, fields.name AS field,
               slots.start_time, slots.end_time, bookings.seats,
               games.name AS game_name, games.joined, games.capacity, games.status AS game_status
        FROM bookings
        JOIN slots ON slots.id = bookings.slot_id
        JOIN fields ON fields.id = slots.field_id
        LEFT JOIN games ON games.id = bookings.game_id
        WHERE bookings.user_id = ? AND bookings.status = 'active'
        ORDER BY slots.start_time
    """
    conn = get_connection()
    rows = conn.execute(sql, (user_id,)).fetchall()
    conn.close()
    return _to_dicts(rows)
