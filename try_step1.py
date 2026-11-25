"""
try_step1.py - a quick manual check for step 1 (no AI yet).

Run:
    python seed.py
    python try_step1.py
"""

from bookings import get_my_bookings, search_free_slots, search_open_games


def show(title, rows):
    print()
    print("=" * 60)
    print(title, f"({len(rows)} results)")
    print("=" * 60)
    for row in rows:
        print(row)


show("Free slots, evenings 19:00-21:00", search_free_slots(earliest_hour=19, latest_hour=21))
show("Free slots at 'Lozenets'", search_free_slots(field_name="Lozenets"))
show("Open games with room for 3 players", search_open_games(players=3))
show("Open games with room for 6 players", search_open_games(players=6))
show("Bookings of user 2 (Maria)", get_my_bookings(user_id=2))
