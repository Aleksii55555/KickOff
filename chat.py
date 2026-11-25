"""
chat.py - talk to the KickOff assistant in the terminal.

Run:
    py chat.py
Type 'exit' to quit.

The assistant logic is in assistant.py, the AI calls are in llm.py.
"""

import sys

from assistant import ask_assistant
from llm import MODEL, LLMError, Usage

CURRENT_USER_ID = 1  # "Alex"

# Read typed or piped text as UTF-8, so Cyrillic input works on Windows too.
sys.stdin.reconfigure(encoding="utf-8", errors="replace")


def main():
    print(f"KickOff assistant (model: {MODEL}). Type 'exit' to quit.\n")
    messages = []  # the whole conversation, so the AI remembers context

    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in ("exit", "quit"):
            break
        if not user_text:
            continue

        length_before = len(messages)
        messages.append({"role": "user", "content": user_text})
        usage = Usage()
        try:
            answer = ask_assistant(messages, usage, CURRENT_USER_ID)
            print(f"\nKickOff: {answer}")
        except LLMError as error:
            # A problem we know how to explain (rate limit, timeout, wrong key...)
            print(f"\n[error] {error}")
            del messages[length_before:]  # forget this whole failed turn
        except Exception as error:
            # Anything unexpected - show it, but keep the chat running.
            print(f"\n[unexpected error] {type(error).__name__}: {error}")
            del messages[length_before:]
        print(f"   [cost] {usage.summary()}\n")


if __name__ == "__main__":
    main()
