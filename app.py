"""
app.py - the KickOff website (a simple chat page).

Run:
    py -m streamlit run app.py
It opens in the browser at http://localhost:8501

How Streamlit works (the important part):
- The whole file runs from top to bottom EVERY time the user does something
  (sends a message, clicks a button).
- Normal variables are lost between runs. What must be remembered (the
  conversation) is kept in `st.session_state`, a dictionary that survives.
"""

import streamlit as st

from assistant import ask_assistant
from llm import LLMError, Usage

CURRENT_USER_ID = 1  # "Alex" - a user switcher comes later

st.set_page_config(page_title="KickOff", page_icon="⚽")
st.title("⚽ KickOff")
st.caption("AI assistant for booking football fields")

# The conversation, kept between runs. It also contains the tool calls and
# tool results, which the AI needs but we do not show on the page.
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.button("New chat"):
    st.session_state.messages = []

# 1. Show the conversation so far (only user questions and AI answers).
for message in st.session_state.messages:
    is_text = message["role"] in ("user", "assistant") and not message.get("tool_calls")
    if is_text:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 2. Wait for a new message from the user.
user_text = st.chat_input("E.g. We are 12, any free field on Friday evening?")

if user_text:
    with st.chat_message("user"):
        st.markdown(user_text)

    messages = st.session_state.messages
    length_before = len(messages)
    messages.append({"role": "user", "content": user_text})
    usage = Usage()

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching..."):
                answer = ask_assistant(messages, usage, CURRENT_USER_ID)
            st.markdown(answer)
        except LLMError as error:
            # A problem we know how to explain (rate limit, timeout, wrong key...)
            st.error(str(error))
            del messages[length_before:]  # forget this failed turn
        except Exception as error:
            st.error(f"Unexpected error: {error}")
            del messages[length_before:]

    # Cost of this answer, small and grey under the chat.
    st.caption(f"💰 {usage.summary()}")
