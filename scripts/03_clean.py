import json
import re
import os
import glob
from dateutil import parser
from datetime import datetime
import pytz

# --- Path configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Input: the raw transcript JSON files (from 02_scrape.py)
INPUT_DIR = os.path.join(DATA_DIR, "raw")

# Output: the cleaned JSON files
OUTPUT_DIR = os.path.join(DATA_DIR, "clean")

# Dates for "Era" logic
ERA_START_DATE = datetime(2012, 1, 23, tzinfo=pytz.UTC)
ERA_NEW_FORMAT_DATE = datetime(2016, 8, 29, tzinfo=pytz.UTC)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def parse_date(date_str):
    try:
        dt = parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt
    except:
        return None

def clean_transcript_new_era(lines):
    """Cleaning logic for modern episodes (Starting 8/29/2016)."""
    cleaned_dialogue = []
    current_speaker = "Narrator/Intro"
    current_text_buffer = []
    
    timestamp_pattern = re.compile(r'^\d{1,2}:\d{2}$') 
    speaker_pattern = re.compile(r'^([A-Za-z \.\-]+):$') 
    ignore_phrases = ["Time", "Podcast Episode Highlights", "Hide Highlights"]

    for line in lines:
        line = line.strip()
        if not line: continue
        if line in ignore_phrases: continue
        if timestamp_pattern.match(line): continue

        speaker_match = speaker_pattern.match(line)
        if speaker_match:
            if current_text_buffer:
                cleaned_dialogue.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text_buffer)
                })
                current_text_buffer = []
            current_speaker = speaker_match.group(1)
            continue

        line = re.sub(r'\[.*?\]', '', line) 
        current_text_buffer.append(line)

    if current_text_buffer:
        cleaned_dialogue.append({
            "speaker": current_speaker,
            "text": " ".join(current_text_buffer)
        })
        
    return cleaned_dialogue

def clean_transcript_old_era(lines):
    """Cleaning logic for episodes between 1/23/2012 & 8/29/2016."""
    cleaned_dialogue = []
    current_speaker = "Narrator/Intro"
    current_text_buffer = []
    
    speaker_inline_pattern = re.compile(r'^(Russ|Guest|Roberts|[A-Z][a-z]+ [A-Z][a-z]+): (.*)')
    full_text = " ".join(lines)
    full_text = re.sub(r'(Russ:|Guest:|Roberts:)', r'\n\1', full_text)
    
    split_lines = full_text.split('\n')

    for line in split_lines:
        line = line.strip()
        if not line: continue
        
        if "Time Podcast Episode Highlights" in line: continue
        
        match = speaker_inline_pattern.match(line)
        
        if match:
            if current_text_buffer:
                cleaned_dialogue.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text_buffer).strip()
                })
                current_text_buffer = []
            
            current_speaker = match.group(1)
            content = match.group(2)
            content = re.sub(r'\[.*?\]', '', content) 
            current_text_buffer.append(content)
            
        else:
            line = re.sub(r'\[.*?\]', '', line)
            current_text_buffer.append(line)

    if current_text_buffer:
        cleaned_dialogue.append({
            "speaker": current_speaker,
            "text": " ".join(current_text_buffer).strip()
        })

    return cleaned_dialogue

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except:
        return

    # --- 1. Identify era ---
    date_obj = parse_date(raw_data.get("date"))
    if not date_obj or date_obj < ERA_START_DATE:
        return 

    raw_text = raw_data.get("content", "")
    lines = raw_text.split('\n') if isinstance(raw_text, str) else []

    # --- 2. Select strategy ---
    if date_obj < ERA_NEW_FORMAT_DATE:
        cleaned_dialogue = clean_transcript_old_era(lines)
    else:
        cleaned_dialogue = clean_transcript_new_era(lines)

    # --- 3. Extract guest name ---
    raw_title = raw_data.get("title", "")
    clean_title = raw_title.replace(" - Econlib", "").strip()
    guest_name = "Unknown"
    
    if " with " in clean_title:
        guest_name = clean_title.split(" with ")[-1].strip()
    elif " on " in clean_title:
        guest_name = clean_title.split(" on ")[0].strip()
    
    # --- 4. Standardize speaker names ---
    for turn in cleaned_dialogue:
        speaker = turn['speaker']
        
        # Map "Guest" -> Actual Name
        if speaker == "Guest":
            turn['speaker'] = guest_name
            
        # Map "Russ" or "Roberts" -> "Russ Roberts"
        elif speaker in ["Russ", "Roberts"]:
            turn['speaker'] = "Russ Roberts"

    # --- 5. Save ---
    clean_data = {
        "meta": {
            "title": clean_title,
            "guest": guest_name,
            "date": str(raw_data.get("date")),
            "url": raw_data.get("url")
        },
        "transcript": cleaned_dialogue
    }

    filename = os.path.basename(file_path)
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)

def main():
    files = glob.glob(f"{INPUT_DIR}/*.json")
    print(f"Processing {len(files)} files...")
    
    for i, file_path in enumerate(files):
        process_file(file_path)
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}...")
            
    print(f"Done. Clean files saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()