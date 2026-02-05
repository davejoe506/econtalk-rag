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
    print("Error: OPENAI_API_KEY not found.")
    print("Please ensure your .env file exists and contains the key.")
    exit(1)

# Initialize clients
try:
    q_client = QdrantClient(url=QDRANT_URL)
    # Test connection to ensure Docker is running
    q_client.get_collections()
    o_client = OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"\nConnection error: {e}")
    print("Make sure your Docker container is running.")
    exit(1)

# --- Helper functions (RAG logic) ---
def get_embedding(text):
    text = text.replace("\n", " ")
    return o_client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def retrieve_context(query, top_k=15):
    """
    Searches the vector database for the top_k most relevant chunks.
    """
    print(f"Searching for: '{query}'...")
    query_vector = get_embedding(query)
    response = q_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k
    )
    
    # Access the points from the response object
    hits = response.points
    
    # Format the results into a single string for LLM
    context_parts = []
    for hit in hits:
        meta = hit.payload['metadata']
        text = hit.payload['text']
        context_parts.append(f"--- EPISODE: {meta['title']} ({meta['date']}) ---\n{text}\n")
    
    return "\n".join(context_parts)

def generate_answer(question):
    """
    1. Retrieves context.
    2. Sends context and question to LLM.
    3. Returns answer.
    """
    # 1. Build the context string
    context_text = retrieve_context(question)
    
    if not context_text:
        return "I couldn't find any relevant episodes to answer that question."

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

def main():
    print("Welcome to the EconTalk RAG Chatbot! (Type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        
        print("\nAI is thinking...")
        try:
            answer = generate_answer(user_input)
            print(f"\nEconTalk Bot:\n{answer}")
        except Exception as e:
            print(f"Error generating answer: {e}")
            
        print("-" * 50)

if __name__ == "__main__":
    main()