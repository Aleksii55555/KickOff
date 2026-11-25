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
