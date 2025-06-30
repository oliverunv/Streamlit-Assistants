import os
import streamlit as st
import weaviate
from weaviate.classes.init import Auth
from openai import OpenAI
from dotenv import load_dotenv

# Set up page
st.set_page_config(page_title="Security Council Repertoire Assistant", layout="wide")
st.title("💬 UNSC Repertoire Assistant")
st.caption("🌐 An AI-powered chatbot to retrieve information from the 2022 Repertoire of Practice of the Security Council (26th Supplement)")

# Initialize API clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=st.secrets["WEAVIATE_URL"],
    auth_credentials=Auth.api_key(st.secrets["WEAVIATE_API_KEY"]),
)

# Function to embed user query
def get_embedding(text):
    response = openai_client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# --- Function to retrieve and format context chunks ---
def retrieve_context(query, top_k=10):
    query_vector = get_embedding(query)
    
    collection = client.collections.get("U5a280054_textembedding3small_1536")

    response = collection.query.near_vector(
        near_vector=query_vector,
        limit=top_k,
        return_properties=[
            "text",
            "title",
            "part",
            "section",
            "intro_note",
            "metadata.filename"
        ]
    )

    def format_chunk(obj):
        meta = obj.properties
        header = f"📄 **{meta.get('title', 'Unknown Title')}** (Part {meta.get('part')}, Section {meta.get('section')})"
        doc_ref = f"📁 File: {meta.get('metadata.filename', 'Unknown')}"
        intro_note = f"📝 *Intro note:* {meta.get('intro_note', 'No summary available.')}"
        text = meta.get("text", "")
        return f"{header}\n{doc_ref}\n{intro_note}\n\n{text}"

    context = "\n\n---\n\n".join(format_chunk(obj) for obj in response.objects)
    return context

# --- System prompt ---
system_prompt = """You are an expert assistant trained to provide factual, concise, and strictly neutral responses based only on the content retrieved from the 25th Supplement (2022) of the Repertoire of Practice of the Security Council.

You must follow the structure and language of the Repertoire closely and avoid adding your own interpretations or opinions.

---

**Your Role:**
- Summarize relevant passages retrieved from the Repertoire.
- Use the metadata fields to situate content within the correct structural and legal context.
- Where applicable, highlight the *Part* of the Repertoire the passage comes from, especially if it is relevant to the structure of the UN Charter (e.g., *Part VII: Actions under Chapter VII*).
- When metadata fields reference specific Articles (e.g., *UN Charter Article 2(4)*), use them to clarify the legal framework discussed.
- If no directly relevant content is found, you may point to related sections based on titles or notes, but do **not** speculate or interpret.

---

**Document Structure and Metadata (25th Supplement, 2022):**  
Each paragraph retrieved is enriched with metadata to help identify its place in the Repertoire:

- **Part**: One of the ten main Parts of the Repertoire (e.g., *Part V: Functions and Powers*).  
- **Section**: Subdivision within each Part.  
- **Title**: Title or heading of the section.  
- **Intro Note**: Brief editorial summary of what the section covers.  
- **UN Charter Article**: References to specific Charter provisions discussed in the section.  
- **Rules of Procedure Article**: Relevant procedural rules referenced.  
- **ICJ Statute Article**: If applicable, provisions from the Statute of the International Court of Justice.  
- **Filename**: Source document name (for internal reference only; not shown to users).

---

**Document Parts:**

1. **Part I** Overview of Council Activities (Agenda Items)  
2. **Part II** Provisional Rules of Procedure  
3. **Part III** Purposes and Principles (Charter Chapter I)  
4. **Part IV** Relations with Other UN Organs  
5. **Part V** Functions and Powers (Charter Chapter V)  
6. **Part VI** Pacific Settlement of Disputes (Charter Chapter VI)  
7. **Part VII** Actions under Chapter VII  
8. **Part VIII** Regional Arrangements (Charter Chapter VIII)  
9. **Part IX** Subsidiary Organs: Committees and Other Bodies  
10. **Part X** Subsidiary Organs: Peacekeeping and Peacebuilding

---

**Response Guidelines:**
- Base your answers **only** on the retrieved content and metadata.
- Mention the **Part** and **Section** if they help contextualize the answer.
- Refer to the **UN Charter**, **Rules of Procedure**, or **ICJ Statute** articles where clearly linked via metadata.
- If no relevant content is found, respond:  
  ➤ *“The Repertoire does not provide specific information on this topic.”*

---

**Formatting Rules:**
- Use **paragraph form** for normal responses.
- Use **bullet points** only if listing items, decisions, or provisions.
- **Bold key terms** like *Resolution*, *Agenda item*, *Article*, *Chapter*, or *Section* when mentioned.

---

**What Not To Do:**
- Do not interpret or draw conclusions from the Repertoire.
- Do not refer to external sources.
- Do not speculate about Security Council positions or intent."""

# --- Function to call OpenAI's chat completion ---
def ask_question_with_context(user_input):
    context = retrieve_context(user_input)

    messages = [{"role": "system", "content": system_prompt}] + st.session_state.conversation_history + [
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {user_input}"
        }
    ]

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ask me anything about the 26th Supplement of the Repertoire!"}]
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# --- Display message history ---
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

# --- Chat interaction ---
if prompt := st.chat_input("Your message"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        answer = ask_question_with_context(prompt)
        st.chat_message("assistant").markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        st.session_state.conversation_history.append({"role": "assistant", "content": answer})

    except Exception as e:
        st.error(f"❌ Error: {e}")

client.close()

st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        text-align: center;
        padding: 0.5rem;
        font-size: 0.8rem;
        color: gray;
        z-index: 999;
        background-color: transparent;
        backdrop-filter: blur(2px);
    }
    </style>
    <div class="footer">
        Built by Oliver Unverdorben · Powered by OpenAI · © 2024
    </div>
    """,
    unsafe_allow_html=True
)
