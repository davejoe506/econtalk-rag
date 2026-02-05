import streamlit as st
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from openai import OpenAI

# --- 1. Load secrets & config ---
# Load environment variables from the .env file
load_dotenv()

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "econtalk_episodes"
API_KEY = os.getenv("OPENAI_API_KEY")

# Check if key exists
if not API_KEY:
    st.error("Error: OPENAI_API_KEY not found. Please ensure your .env file exists and contains the key.")
    st.stop()

# --- 2. Initialize clients ---
@st.cache_resource
def get_clients():
    try:
        q_client = QdrantClient(url=QDRANT_URL)
        # Test connection to ensure Docker is running
        q_client.get_collections()
        o_client = OpenAI(api_key=API_KEY)
        return q_client, o_client
    except Exception as e:
        st.error(f"Connection error: {e}")
        st.error("Make sure your Docker container is running.")
        st.stop()

q_client, o_client = get_clients()

# --- 3. Helper functions (RAG logic) ---
def get_embedding(text):
    text = text.replace("\n", " ")
    return o_client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def retrieve_context(query, top_k=15):
    """
    Searches the vector database for the top_k most relevant chunks and returns them as objects.
    """
    query_vector = get_embedding(query)
    response = q_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k
    )
    
    # 'query_points' returns a response object; list the points inside it
    return response.points

def generate_rag_response(question, hits):
    """
    Generates an answer based on the provided hits.
    """
    # 1. Build the context string
    context_parts = []
    for hit in hits:
        meta = hit.payload['metadata']
        text = hit.payload['text']
        context_parts.append(f"--- EPISODE: {meta['title']} ({meta['date']}) ---\n{text}\n")
    
    context_text = "\n".join(context_parts)
    
    # 2. Build the prompt
    system_prompt = """
You are an expert research assistant for the 'EconTalk' podcast archives. 

Your Role:
Answer the user's question using ONLY the provided Context (podcast transcripts).

Guidelines:
1. CITATION IS MANDATORY: Always attribute ideas to the specific guest or episode.
2. REASONABLE INFERENCE: If an author is discussing their own book, you may treat that as the book being "recommended" or "featured."
3. NO OUTSIDE KNOWLEDGE: Do not use external training data.
4. TONE: Intellectual, curious, and charitable.
"""
    
    # 3. Call LLM
    response = o_client.chat.completions.create(
        model="gpt-4o", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content

# --- 4. Streamlit UI ---
st.set_page_config(page_title="EconTalk RAG", page_icon="🎙️")
st.title("🎙️ EconTalk RAG Explorer")
st.markdown("Ask questions about economics, philosophy, and life based on the EconTalk archives.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input listener
if prompt := st.chat_input("What did Mike Munger say about voting?"):
    
    # 1. Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Process (RAG pipeline)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            # A. Retrieve
            hits = retrieve_context(prompt)
            
            # B. Generate
            if not hits:
                response = "I couldn't find any relevant episodes."
            else:
                response = generate_rag_response(prompt, hits)
            
            # C. Display answer
            message_placeholder.markdown(response)
            
            # D. Show sources
            with st.expander("View Source Episodes"):
                for i, hit in enumerate(hits):
                    meta = hit.payload['metadata']
                    score = hit.score
                    st.markdown(f"**{i+1}. {meta['title']}** (Score: {score:.4f})")
                    st.caption(f"Date: {meta['date']}")
                    st.text(hit.payload['text'][:200] + "...") # Show preview
                    st.markdown("---")

            # Save to history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            message_placeholder.error(f"Error: {e}")