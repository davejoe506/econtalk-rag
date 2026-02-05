import json
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm

# --- Path configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Input: the final vector JSONL file (from 05_embed.py)
INPUT_FILE = os.path.join(DATA_DIR, "econtalk_vectors.jsonl")

# Qdrant configuration
COLLECTION_NAME = "econtalk_episodes"
VECTOR_SIZE = 1536 
BATCH_SIZE = 500
QDRANT_URL = "http://localhost:6333"

def load_data():
    # 1. Check for input file
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find {INPUT_FILE}")
        print("Did you run '05_embed.py'?")
        return

    # 2. Connect to Qdrant (with error handling)
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    try:
        client = QdrantClient(url=QDRANT_URL)
        # Test connection
        client.get_collections()
    except Exception as e:
        print("\nConnection failed.")
        print(f"Could not connect to Qdrant at {QDRANT_URL}.")
        print("Is your Docker container running?")
        print("Try running: docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        return

    # 3. Reset collection (full refresh)
    if client.collection_exists(collection_name=COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'.")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Created fresh collection '{COLLECTION_NAME}'.")

    # 4. Read and upload
    points = []
    
    # Count lines for progress bar
    total_lines = sum(1 for _ in open(INPUT_FILE, 'r', encoding='utf-8'))
    print(f"Uploading {total_lines} vectors...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(tqdm(f, total=total_lines)):
            try:
                record = json.loads(line)
                
                # Check for errors in the record
                if "embedding" not in record or not record["embedding"]:
                    continue

                point = PointStruct(
                    id=i, 
                    vector=record['embedding'],
                    payload={
                        "text": record['text'],
                        "metadata": record['metadata'],
                        "source_id": record['id']
                    }
                )
                points.append(point)

                # Batch upload
                if len(points) >= BATCH_SIZE:
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        wait=False,
                        points=points
                    )
                    points = []
            except json.JSONDecodeError:
                continue

    # Upload remaining points
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points
        )

    print("\Done. Data loaded into Docker container.")
    print("View your data at: http://localhost:6333/dashboard")

if __name__ == "__main__":
    load_data()