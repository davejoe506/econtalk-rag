import json
import os
import glob

# --- Path configuration ---
# Get absolute path of the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to the script (Go up one level (..) to root, then into 'data')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Input: the cleaned JSON files (from 03_clean.py)
INPUT_DIR = os.path.join(DATA_DIR, "clean")

# Output: the final JSONL file for Qdrant
OUTPUT_FILE = os.path.join(DATA_DIR, "econtalk_chunks.jsonl")

# Target chunk size (in characters).
# 1500 chars is roughly 300-400 tokens, a sweet spot for RAG
TARGET_CHUNK_SIZE = 1500 
OVERLAP_TURNS = 1 # how many previous turns to keep for context

def create_chunks_for_episode(data):
    chunks = []
    meta = data['meta']
    transcript = data['transcript']
    
    # Check if transcript is empty
    if not transcript:
        return []

    current_chunk_turns = []
    current_char_count = 0
    
    # Iterate through the dialogue turns
    for i, turn in enumerate(transcript):
        speaker = turn['speaker']
        text = turn['text']
        
        # Create a formatted string: "Speaker Name: Text"
        formatted_turn = f"{speaker}: {text}"
        
        current_chunk_turns.append(formatted_turn)
        current_char_count += len(formatted_turn)
        
        # If target size is hit, seal chunk
        if current_char_count >= TARGET_CHUNK_SIZE:
            
            # 1. Join turns into one block of text
            chunk_text = "\n\n".join(current_chunk_turns)
            
            # 2. Add rich context (Title + Date) to the top of the chunk (helping embedding model understand the topic immediately)
            contextualized_text = (
                f"Podcast: {meta['title']}\n"
                f"Date: {meta['date']}\n"
                f"Guest: {meta['guest']}\n\n"
                f"{chunk_text}"
            )
            
            # 3. Create chunk object
            chunk_record = {
                "id": f"{meta['url']}_{len(chunks)}", # unique ID
                "text": contextualized_text,           # the content to embed
                "metadata": meta                       # original metadata for filtering later
            }
            chunks.append(chunk_record)
            
            # 4. Reset for next chunk (with overlap)
            # Keep the last N turns to maintain flow
            overlap = current_chunk_turns[-OVERLAP_TURNS:]
            current_chunk_turns = overlap
            current_char_count = sum(len(t) for t in overlap)

    # Take care of last leftover chunk
    if current_chunk_turns:
        chunk_text = "\n\n".join(current_chunk_turns)
        contextualized_text = (
            f"Podcast: {meta['title']}\n"
            f"Date: {meta['date']}\n"
            f"Guest: {meta['guest']}\n\n"
            f"{chunk_text}"
        )
        chunk_record = {
            "id": f"{meta['url']}_{len(chunks)}",
            "text": contextualized_text,
            "metadata": meta
        }
        chunks.append(chunk_record)

    return chunks

def main():
    files = glob.glob(f"{INPUT_DIR}/*.json")
    print(f"Chunking {len(files)} episodes...")
    
    total_chunks = 0
    
    # Open output file in Write mode
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                episode_chunks = create_chunks_for_episode(data)
                
                for chunk in episode_chunks:
                    # Write each chunk as a separate line (JSONL format)
                    out_f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
                    total_chunks += 1
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    print(f"Done. Generated {total_chunks} chunks.")
    print(f"Saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()