# KickOff - build plan

Built step by step. Every step ends with something that runs.
The plan follows the course slides: PoC -> Integration -> Hardening -> Finish.

## Models

| Role | Model | Why |
|---|---|---|
| Chat + tools | Groq `openai/gpt-oss-120b` | Free and fast, good at tool calling |
| Embeddings for RAG | Ollama `bge-m3` (local) | Free, supports Bulgarian, data stays on our PC |

The demo model is decided later. All AI calls live in `llm.py`, so changing the
provider means changing only that one file.
Not used: `bggpt:4b` - no tool calling support in Ollama, too small for an agent.

## Steps

### Phase 1 - PoC (proof of concept)
- [x] **Step 1** - Database (SQLite), test data, read-only search functions.
- [x] **Step 2** - Terminal chat with tool calling (`search_free_slots`, `search_open_games`, `get_my_bookings`).

### Phase 2 - Integration
- [x] **Step 3** - Reliable LLM layer (`llm.py`):
  all Groq calls in one place, timeout + retry with backoff (rate limit!), clear error
  messages instead of freezing, tokens and cost of every turn.
- [x] **Step 4** - Minimal website (Streamlit): only the chat with the assistant,
  cost under each answer, "New chat" button.
- [ ] **Step 5** - Booking with human approval (HITL, enforced by the server):
  `propose_book_field` only creates a pending action -> card with Confirm / Cancel on the
  website -> server checks owner, expiry, free slot, price from DB -> transaction.
  Tool arguments validated with Pydantic.
- [ ] **Step 6** - Website extras: streaming answers, user switcher.
- [ ] **Step 7** - Mode 2: join an open game (atomic `UPDATE ... WHERE joined + n <= capacity`),
  create an open game, cancel a booking.
- [ ] **Step 8** - RAG: Bulgarian documents for each field -> chunks -> `bge-m3` embeddings ->
  Chroma with metadata (field, document, section) -> `search_rules`.
  Answers as structured output `{answer, sources[]}`; "not in the documents" instead of inventing.
- [ ] **Step 9** - Deadlines + notifications: background job every minute confirms full games,
  cancels expired ones, notifies all players. Bell icon in the UI.
- [ ] **Step 10** - Agent behaviour: alternatives when nothing fits (other hour/day/field),
  max 6 tool calls, shorter history (context management), caching.

### Phase 3 - Hardening (graded: security and cost)
- [ ] **Step 11** - Input guardrail (message length, rate limit per user), protection from
  indirect injection (game names: max 40 chars, allowed symbols only), output validation,
  `tests/` with attack and edge-case questions that run automatically.

### Phase 4 - Finish
- [ ] **Step 12** - README with run steps the jury can follow, Docker, data-flow diagram,
  backup demo recording, `DEFENSE.md` with answers: why this model, prompt injection,
  cost of a typical request, limitations and next steps.

## After every step
- Short explanation of the new code in `DEFENSE.md`, so every team member can defend it.
- Commit.

## Files
- `database.py` - connection + table definitions
- `seed.py` - deletes and recreates the database with test data
- `bookings.py` - read-only search functions (used as AI tools)
- `tools.py` - tool descriptions (JSON Schema) for the AI + `run_tool` dispatcher
- `llm.py` - all AI calls: timeout, retries, clear errors, token and cost counting
- `assistant.py` - system prompt + tool calling loop (shared by the terminal and the website)
- `chat.py` - terminal chat: `py chat.py`
- `app.py` - website: `py -m streamlit run app.py` -> http://localhost:8501
- `DEFENSE.md` - explanations and answers for the defence

## Setup
1. `py -m pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and put your keys in it
3. `py seed.py` (creates the database)

Note: use `py`, not `python` - on this PC `python` is a different Python without pip.
