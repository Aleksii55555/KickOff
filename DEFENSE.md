# KickOff - notes for the defence

Short explanations of every part of the code, and answers to questions the jury
is likely to ask. Updated after every step.

---

## Steps 1-2: database, search, tool calling

**How the data is stored.** One SQLite file (`data/kickoff.db`), created by `seed.py`.
Times are text like `"2026-11-27 19:00"` - this format sorts correctly, so SQL can
compare times with `<` and `>`.

**How the AI uses our data (tool calling).**
1. We send the AI the conversation + a description of our tools (`TOOLS` in `tools.py`).
2. The AI does NOT run anything. It only answers "please call `search_free_slots`
   with these arguments".
3. Our code (`run_tool`) runs the real Python function and sends the result back.
4. The AI writes the final answer from the result.

**Why the AI cannot see other users' bookings.** `get_my_bookings` has no `user_id`
argument for the AI. The id comes from our program (`CURRENT_USER_ID`), not from the AI.
Even a successful prompt injection cannot change it.

**Why we add `"day"` to every result.** The model was wrong about weekdays
(called Thursday "Friday"). Python calculates the weekday correctly, so we give it
to the model instead of letting it guess.

---

## Step 3: reliable AI calls (`llm.py`)

**Why one file for all AI calls.** The rest of the code only calls `call_model()`.
To change the provider (e.g. for the demo) we change only `llm.py`.

**What happens when something goes wrong:**

| Problem | What we do | Why |
|---|---|---|
| Rate limit (429) | Wait and retry (up to 2 times). We use Groq's `retry-after` if it sends one, otherwise 2s, 4s | Groq's free tier has limits per minute - it really happens during testing |
| Timeout (no answer in 30s) | Retry | The app must never freeze |
| No internet / server error (5xx) | Retry | Usually temporary |
| Broken tool call from the model (`tool_use_failed`) | Retry | This is "invalid output" - asking again usually fixes it |
| Wrong API key / wrong model name | Stop, clear message | Retrying cannot fix it |
| Anything unexpected | Show the error, keep the chat running | Never crash |

We set `max_retries=0` on the Groq client and wrote the retry loop ourselves,
so we can explain exactly what happens.

**Tool limit.** Max 6 tool calls per turn. After that we call the model with
`tool_choice="none"`, so it MUST answer with text - no endless loop.

**Cost of a typical request.** Every AI call returns how many tokens it used.
We add them up per turn and multiply by the price
(gpt-oss-120b on Groq: $0.15 / 1M input tokens, $0.60 / 1M output tokens).

Measured on a real question ("we are 12, free field Saturday afternoon?"):
- 2 AI calls (1: choose the tool, 2: write the answer)
- ~2,400 input + ~570 output tokens
- **~$0.0007 per question** (Groq's free tier: $0)

Note: the follow-up question cost more input tokens (~4,900), because the whole
conversation is sent every time. Step 9 shortens old history to keep this low.

**How we tested it.** `GROQ_API_KEY=wrong`, `GROQ_MODEL=no-such-model` and
`LLM_TIMEOUT=0.01` - each gives a clear message instead of a crash.

---

## Step 4: minimal website (`app.py`)

**Why Streamlit.** A web page written in plain Python - no HTML, CSS or JavaScript.
Good for a prototype; the whole page is ~60 lines.

**How the code is split now:**

| File | Job |
|---|---|
| `llm.py` | talks to Groq (timeout, retries, cost) |
| `assistant.py` | the "brain": system prompt + tool calling loop |
| `chat.py` | terminal interface |
| `app.py` | website interface |

Both interfaces use the same `ask_assistant()` - the logic is written once.

**How Streamlit works.** The whole `app.py` runs from top to bottom every time the
user sends a message or clicks a button. Normal variables are lost between runs,
so the conversation is kept in `st.session_state` (a dictionary that survives).

**What the page shows.** Only the user's questions and the AI's answers. The tool
calls and tool results are also in the conversation (the AI needs them), but we
skip them when drawing the page.

**Errors.** Same as the terminal: an `LLMError` (rate limit, timeout, wrong key)
is shown as a red box, and the failed turn is removed from the conversation.

**A real bug we found and fixed (good example for the defence).**
Asking about "Долно Малене" crashed the page with
`'charmap' codec can't encode characters`. The cause was not the AI: we print every
tool call to the terminal, and the Windows terminal uses an old encoding (cp1252) with
no Cyrillic letters. Fix: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
in `assistant.py`. Even if a character still cannot be printed, it becomes "?" instead
of a crash.

**The AI knows which fields exist.** The system prompt now lists all fields from the
database. Asked about a place where we have no field, it says so and offers the
fields we have, instead of asking for a day and time.

**Names are stored in Bulgarian, the search ignores the alphabet and case.**
Fields, addresses and games are stored in Bulgarian ("Спорт Парк Лозенец"), so the AI
shows them exactly like that - no translating. One problem: SQLite's `LIKE` ignores
upper/lower case only for Latin letters, so "лозенец" would not find "Лозенец".
Solution: `to_latin()` in `database.py` turns text into lowercase Latin with the
official Bulgarian transliteration table, and is used ONLY for comparing. We register
it in SQLite (`conn.create_function("TO_LATIN", 1, to_latin)`) and compare
`TO_LATIN(fields.name) LIKE '%lozenets%'`. So "Лозенец", "лозенец", "ЛОЗЕНЕЦ" and
"Lozenets" all find the field. This is done in code - we do not rely on the AI.
