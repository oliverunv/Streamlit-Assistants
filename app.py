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


# Set up page
st.set_page_config(page_title="Security Council Repertoire Assistant", layout="wide")

# Dynamic values from secrets
openai_api_key = st.secrets["OPENAI_API_KEY"]
assistant_id = st.secrets["ASSISTANT_ID"]
app_title = st.secrets.get("APP_TITLE", "💬 UNSC Repertoire Assistant")
app_caption = st.secrets.get("APP_CAPTION", "🌐 An AI-powered chatbot to retrieve information from the Repertoire of Practice of the Security Council")

# Override the placeholder title
st.title(app_title)
st.caption(app_caption)

client = OpenAI(api_key=openai_api_key)

# Initialize session state
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ask me anything about Children and Armed Conflict!"}]

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

# Simulate sticky footer at the bottom of the page
footer = """
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #f0f2f6;
    text-align: center;
    padding: 0.5rem;
    font-size: 0.8rem;
    color: gray;
    z-index: 100;
}
</style>
<div class="footer">
    Built by Oliver Unverdorben · Powered by OpenAI · © 2024
</div>
"""
st.markdown(footer, unsafe_allow_html=True)

