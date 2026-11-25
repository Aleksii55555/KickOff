"""
tools.py - the "tools" the AI is allowed to use.

Two parts:
1. TOOLS     - a description of every tool in JSON Schema format.
               The AI reads this to know which tools exist and what
               arguments they take.
2. run_tool  - when the AI asks for a tool, this function calls the
               real Python function from bookings.py and returns the result.

Important: user_id is NOT an argument the AI can choose. It comes from
our program (the logged-in user), so the AI can never look at someone
else's bookings.
"""

import json

from bookings import get_my_bookings, search_free_slots, search_open_games

# Arguments that several tools share.
DATE_AND_HOUR_ARGS = {
    "date_from": {"type": "string", "description": "First day to search, format YYYY-MM-DD."},
    "date_to": {"type": "string", "description": "Last day to search (included), format YYYY-MM-DD."},
    "earliest_hour": {"type": "integer", "description": "Earliest start hour, 0-23. E.g. 18 for 'evening'."},
    "latest_hour": {"type": "integer", "description": "Latest start hour, 0-23."},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_free_slots",
            "description": "Find free one-hour slots to book a WHOLE field. "
            "Use when the user already has enough players for a full game.",
            "parameters": {
                "type": "object",
                "properties": {
                    **DATE_AND_HOUR_ARGS,
                    "field_name": {"type": "string", "description": "Optional part of a field name, e.g. 'Mladost'."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_open_games",
            "description": "Find open games where other people are playing and there are free places. "
            "Use when the user is alone or a small group.",
            "parameters": {
                "type": "object",
                "properties": {
                    **DATE_AND_HOUR_ARGS,
                    "players": {"type": "integer", "description": "How many people want to join together. Default 1."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_bookings",
            "description": "Show the current user's active bookings and joined games.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def run_tool(name, arguments_json, user_id):
    """Run the tool the AI asked for and return the result as JSON text.

    If something goes wrong (bad arguments, unknown tool) we return an
    error message as JSON instead of crashing - the AI can read it and
    try again.
    """
    try:
        args = json.loads(arguments_json or "{}")

        if name == "search_free_slots":
            result = search_free_slots(**args)
        elif name == "search_open_games":
            result = search_open_games(**args)
        elif name == "get_my_bookings":
            result = get_my_bookings(user_id)  # user_id from the program, NOT from the AI
        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as error:
        result = {"error": f"The tool failed: {error}"}

    return json.dumps(result, ensure_ascii=False)
