import pandas as pd
import json
import os
import time
import random
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import datetime
import pytz

# --- Path configuration ---
# Get absolute path of the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to the script (Go up one level (..) to root, then into 'data')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Input: the episode list CSV file (from 01_fetch_feed.py)
INPUT_CSV = os.path.join(DATA_DIR, "econtalk_episode_list.csv")

# Output: the raw transcript JSON files
OUTPUT_DIR = os.path.join(DATA_DIR, "raw")

# Cutoff date configuration
CUTOFF_DATE = datetime(2012, 1, 23, tzinfo=pytz.UTC)

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_existing_urls():
    """Scans the output directory to see which URLs have already scraped."""
    existing_urls = set()
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(OUTPUT_DIR, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "url" in data:
                        existing_urls.add(data["url"])
            except:
                pass # Ignore corrupted files
    return existing_urls

def scrape_episode(context, url, title, published_date):
    """Scrapes a single episode page for the transcript."""
    page = context.new_page()
    
    # Set User-Agent to match a real browser (crucial for bypassing 403)
    page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    })

    try:
        # Navigate
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Parse content
        content_html = page.content()
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # --- Extract transcript ---
        transcript_text = ""
        # Strategy 1: Standard 'audio-highlight' class
        transcript_div = soup.find('div', class_='audio-highlight')
        
        if not transcript_div:
            # Strategy 2: Look for header "AUDIO TRANSCRIPT"
            header = soup.find(string=lambda text: text and "AUDIO TRANSCRIPT" in text)
            if header:
                transcript_div = header.find_parent().find_next('div')
        
        if transcript_div:
            transcript_text = transcript_div.get_text(separator='\n', strip=True)
        else:
            # If no transcript is found, we log it but don't crash
            print(f"  Warning: No transcript text found for: {title}")
            page.close()
            return None

        # --- Extract Date ---
        # We use the RSS date if available, otherwise try to extract from text
        final_date = published_date
        if not final_date or str(final_date) == "nan": 
            # Try to grab it from the transcript text if RSS didn't have it
            date_match = re.search(r"Recording date: (.*?)]", transcript_text)
            if date_match:
                final_date = date_match.group(1)
            else:
                date_tag = soup.find('time')
                if date_tag:
                    final_date = date_tag.get_text(strip=True)

        # Build the Data Object
        data = {
            "url": url,
            "title": title,
            "date": str(final_date), # Ensure it's a string
            "content": transcript_text
        }
        
        page.close()
        return data

    except Exception as e:
        print(f"  Error: Failed processing {url}: {e}")
        page.close()
        return None

def main():
    # 1. Load the CSV
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Could not find {INPUT_CSV}. Make sure it is in this folder.")
        return

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} episodes from CSV.")

    # 2. Check what is already done
    existing_urls = get_existing_urls()
    print(f"Found {len(existing_urls)} episodes already scraped in folder.")

    # --- 3. Filter by date ---
    print(f"Filtering for episodes on or after {CUTOFF_DATE.date()}...")
    
    # Helper to parse date for filtering
    def is_recent_enough(date_str):
        try:
            dt = parser.parse(str(date_str))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            return dt >= CUTOFF_DATE
        except:
            return False

    # Prefer 'date' column (YYYY-MM-DD), fallback to 'published'
    date_col = 'date' if 'date' in df.columns else 'published'
    
    # Create filtered list
    df_filtered = df[df[date_col].apply(is_recent_enough)].copy()
    
    print(f"Kept {len(df_filtered)} episodes after date filtering.")

    # 4. Filter out episodes already on disk
    df_filtered['normalized_url'] = df_filtered['url'].astype(str).str.strip().str.rstrip('/')
    pending_episodes = df_filtered[~df_filtered['url'].isin(existing_urls)]
    
    print(f"Starting scrape for {len(pending_episodes)} new pending episodes...")
    print("-" * 40)

    # 5. Start the browser loop
    with sync_playwright() as p:
        # Launch browser (headless is faster, but set False if you want to watch)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Iterate through pending episodes
        for index, row in pending_episodes.iterrows():
            url = row['url']
            title = row['title']
            # Use 'date' if available, else 'published'
            published = row.get('date', row.get('published')) 
            
            # Create a safe filename from the URL slug
            slug = url.strip('/').split('/')[-1]
            if not slug: 
                slug = f"episode_{index}"
            filename = f"{OUTPUT_DIR}/{slug}.json"

            print(f"Scraping ({index}/{len(df)}): {title[:30]}...")

            # Run the scraper function
            result = scrape_episode(context, url, title, published)

            if result:
                # Save immediately to disk
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"  -> Saved to {filename}")
            else:
                print(f"  -> Skipped (No transcript or error)")

            # Polite sleep (random 2-4 seconds) to avoid getting banned
            time.sleep(random.uniform(2, 4))

        browser.close()
        print("-" * 40)
        print("Batch scrape complete.")

if __name__ == "__main__":
    main()