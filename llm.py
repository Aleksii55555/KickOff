"""
llm.py - the ONLY file that talks to the AI provider (Groq).

If we change the provider later (e.g. for the demo), we change only this file.
The rest of the project just calls `call_model(...)`.

What this file adds on top of a plain API call:
1. Timeout      - we never wait forever for an answer.
2. Retry        - if Groq says "too many requests" (rate limit), the server
                  has a hiccup, or the model produced a broken tool call,
                  we wait a bit and try again (2s, 4s, ...).
3. Clear errors - instead of a crash with a long traceback, we raise
                  LLMError with a short message we can show to the user.
4. Cost         - we count the tokens of every call and calculate the price.
"""

import os
import time

import groq
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT", "30"))
MAX_ATTEMPTS = 3  # 1 normal try + 2 retries

# Price in USD per 1 million tokens (Groq price list for gpt-oss-120b).
# Groq has a free tier, but we still show what a request WOULD cost.
PRICE_INPUT_PER_MILLION = 0.15
PRICE_OUTPUT_PER_MILLION = 0.60

# max_retries=0: we do the retries ourselves below, so we can see and
# explain exactly what happens.
client = groq.Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    timeout=TIMEOUT_SECONDS,
    max_retries=0,
)


class LLMError(Exception):
    """An error with a short, user-friendly message."""


class Usage:
    """Counts tokens over one turn (one turn can call the model several times)."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def add(self, response_usage):
        if response_usage is None:
            return
        self.input_tokens += response_usage.prompt_tokens
        self.output_tokens += response_usage.completion_tokens
        self.calls += 1

    def cost_usd(self):
        return (
            self.input_tokens * PRICE_INPUT_PER_MILLION
            + self.output_tokens * PRICE_OUTPUT_PER_MILLION
        ) / 1_000_000

    def summary(self):
        return (
            f"{self.calls} AI calls, {self.input_tokens} input + {self.output_tokens} output tokens, "
            f"~${self.cost_usd():.5f}"
        )


def _wait_seconds(attempt, error):
    """How long to wait before the next try: 2s, 4s, 8s...

    If Groq tells us how long to wait (the 'retry-after' header), we use that.
    """
    response = getattr(error, "response", None)
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), 30)
            except ValueError:
                pass
    return 2 ** attempt


def call_model(messages, tools, usage, allow_tools=True):
    """Send the conversation to the model and return its message.

    messages:    the conversation (system prompt included)
    tools:       the tool descriptions from tools.py
    usage:       a Usage object - tokens of this call are added to it
    allow_tools: False = the model must answer with text (used when the
                 tool limit is reached)
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto" if allow_tools else "none",
            )
            usage.add(response.usage)
            return response.choices[0].message

        # --- errors where trying again can help ---
        except groq.RateLimitError as error:
            problem = "Too many requests to the AI (rate limit)."
            last_error = error
        except groq.APITimeoutError as error:
            problem = f"The AI did not answer in {TIMEOUT_SECONDS:.0f} seconds."
            last_error = error
        except groq.APIConnectionError as error:
            problem = "No connection to the AI service. Check your internet."
            last_error = error
        except groq.InternalServerError as error:
            problem = "The AI service has a temporary problem."
            last_error = error
        except groq.BadRequestError as error:
            # Groq returns 'tool_use_failed' when the model wrote a broken
            # tool call (invalid output). Asking again usually fixes it.
            if "tool_use_failed" in str(error):
                problem = "The AI produced an invalid tool call."
                last_error = error
            else:
                raise LLMError(f"Invalid request to the AI: {error}") from error

        # --- errors where trying again will NOT help ---
        except groq.AuthenticationError as error:
            raise LLMError("Wrong or missing GROQ_API_KEY in the .env file.") from error
        except groq.NotFoundError as error:
            raise LLMError(f"The model '{MODEL}' does not exist. Check GROQ_MODEL in .env.") from error
        except groq.APIStatusError as error:
            raise LLMError(f"AI service error {error.status_code}.") from error

        if attempt < MAX_ATTEMPTS:
            wait = _wait_seconds(attempt, last_error)
            print(f"   [retry] {problem} Trying again in {wait:.0f}s ({attempt}/{MAX_ATTEMPTS - 1})...")
            time.sleep(wait)

    raise LLMError(f"{problem} Please try again in a minute.") from last_error
