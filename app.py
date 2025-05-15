import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

def clean_text_content(content_blocks):
    """Remove file citation annotations and their markers from the assistant response."""
    cleaned_text = ""
    for block in content_blocks:
        if block.type == "text" and hasattr(block.text, "annotations"):
            text_value = block.text.value
            for annotation in block.text.annotations:
                if annotation.type == "file_citation":
                    text_value = text_value.replace(annotation.text, "")
            cleaned_text += text_value
        elif block.type == "text":
            cleaned_text += block.text.value
    return cleaned_text.strip()

load_dotenv()
st.set_page_config(page_title="Security Council Repertoire Assistant", layout="wide")


# Dynamic values from secrets
APP_TITLE = st.secrets.get("APP_TITLE", "💬 UNSC Repertoire Assistant")
APP_CAPTION = st.secrets.get("APP_CAPTION", "🌐 An AI-powered chatbot to retrieve information from the Repertoire of Practice of the Security Council")
ASSISTANT_ID = st.secrets["ASSISTANT_ID"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Set up page
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption(APP_CAPTION)

# Initialize OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize session state
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ask me anything about the Repertoire!"}]

# Show past messages
for message in st.session_state.messages:
    st.chat_message(message["role"]).markdown(message["content"])

# Input prompt
if prompt := st.chat_input("Your message"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Add user message to thread
    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=prompt)
    run = client.beta.threads.runs.create_and_poll(thread_id=st.session_state.thread_id, assistant_id=assistant_id)

    # Get response
    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
        for msg in messages:
            if msg.role == "assistant":
                reply = clean_text_content(msg.content)
                st.chat_message("assistant").markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                break
    else:
        st.error("⚠️ Assistant is still processing. Try again.")
