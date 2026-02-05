import json
import os
import time
from openai import OpenAI, RateLimitError
from tqdm import tqdm

from dotenv import load_dotenv

load_dotenv()

# --- Path configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Input: the final JSONL file for Qdrant (from 04_chunk.py)
INPUT_FILE = os.path.join(DATA_DIR, "econtalk_chunks.jsonl")

# Output: the final vector JSONL file
OUTPUT_FILE = os.path.join(DATA_DIR, "econtalk_vectors.jsonl")

BATCH_SIZE = 50

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY not found. Did you create the .env file?")
    exit(1)

client = OpenAI(api_key=api_key)

def get_existing_ids():
    """Scans the output file to see which chunk IDs are already done."""
    existing_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    existing_ids.add(data['id'])
                except:
                    pass
    return existing_ids

def get_embeddings_with_retry(texts, model="text-embedding-3-small"):
    """
    Tries to get embeddings. If it hits a rate limit (429), it waits and tries again automatically."""
    # Normalize text
    texts = [t.replace("\n", " ") for t in texts]
    
    while True:
        try:
            response = client.embeddings.create(input=texts, model=model)
            return [data.embedding for data in response.data]
        
        except RateLimitError:
            print("\nRate limit hit: Pausing for 10 seconds to cool down...")
            time.sleep(10)  # Wait 10 seconds before retrying
            
        except Exception as e:
            print(f"\nCritical error: {e}")
            # For non-rate-limit errors, might want to skip or raise; for now, break to avoid infinite loops on bad data
            return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # 1. Check what's already done
    print("Checking existing progress...")
    existing_ids = get_existing_ids()
    print(f"Found {len(existing_ids)} vectors already saved.")

    # 2. Read all chunks
    print("Reading input chunks...")
    all_chunks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            all_chunks.append(json.loads(line))
            
    # 3. Filter out chunks that are already done
    pending_chunks = [c for c in all_chunks if c['id'] not in existing_ids]
    print(f"Remaining chunks to embed: {len(pending_chunks)}")

    if not pending_chunks:
        print("All chunks are already embedded. You are done.")
        return

    # 4. Process in batches
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as outfile: # 'a' for Append mode
        
        batch_lines = []
        batch_objects = []
        
        # Assume pending_chunks is the list to process
        for i, record in enumerate(tqdm(pending_chunks)):
            batch_lines.append(record['text'])
            batch_objects.append(record)
            
            # Use >= comparison or check if it's the very last item
            if len(batch_lines) >= BATCH_SIZE or i == len(pending_chunks) - 1:
                
                vectors = get_embeddings_with_retry(batch_lines)
                
                if vectors:
                    for j, vector in enumerate(vectors):
                        batch_objects[j]['embedding'] = vector
                        outfile.write(json.dumps(batch_objects[j]) + '\n')
                
                # Reset batch
                batch_lines = []
                batch_objects = []

    print(f"\nDone. Corpus embedding complete.")

if __name__ == "__main__":
    main()