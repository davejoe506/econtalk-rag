import pandas as pd
import feedparser
from dateutil import parser
from datetime import datetime
import pytz
import os

def get_rss_episodes():
    rss_urls = [
        "https://feeds.simplecast.com/wgl4xEgL"  # Main Feed (2006-Now)
        # "https://files.libertyfund.org/econtalk/EconTalk2022.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2021.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2020.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2019.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2018.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2017.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2016.xml",
        # "https://files.libertyfund.org/econtalk/EconTalk2015.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2014.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2013.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2012.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2011.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2010.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2009.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2008.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2007.xml", 
        # "https://files.libertyfund.org/econtalk/EconTalk2006.xml" 
    ]
    
    print(f"Fetching from {len(rss_urls)} RSS sources...")
    
    all_episodes = []
    seen_urls = set()
    
    for url in rss_urls:
        print(f"Processing: {url}")
        try:
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                link = entry.link
                raw_date = entry.get("published")
                
                # --- 1. PARSE DATE ---
                try:
                    # Convert messy string "Mon, 19 Jan..." to a real Date Object
                    dt_object = parser.parse(raw_date)
                    
                    # Ensure it is UTC
                    if dt_object.tzinfo is None:
                        dt_object = dt_object.replace(tzinfo=pytz.UTC)
                    
                    # Create a clean string for the CSV (YYYY-MM-DD)
                    clean_date_str = dt_object.strftime("%Y-%m-%d")

                except Exception as e:
                    print(f"  Warning: Could not parse date for {entry.title}: {e}")
                    clean_date_str = raw_date
                    dt_object = datetime.min.replace(tzinfo=pytz.UTC)

                if link and link not in seen_urls:
                    seen_urls.add(link)
                    all_episodes.append({
                        "title": entry.title,
                        "url": link,
                        "published_raw": raw_date,
                        "date": clean_date_str,
                        "dt_object": dt_object
                    })
                    
        except Exception as e:
            print(f"Failed to process {url}: {e}")

    # Save all combined episodes to a single CSV
    if all_episodes:
        df = pd.DataFrame(all_episodes)
        
        # --- 2. SORT BY DATE (Newest First) ---
        df = df.sort_values(by='dt_object', ascending=False)
        df = df.drop(columns=['dt_object'])

        # Get absolute path of the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Go up one level (..) to root, then into 'data'
        data_dir = os.path.join(script_dir, '..', 'data')
        
        # Create directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Join the path with the filename
        filename = "econtalk_episode_list.csv"
        full_path = os.path.join(data_dir, filename)
        
        df.to_csv(full_path, index=False)
        
        print("-" * 30)
        print(f"Done. Collected {len(df)} unique episodes.")
        print(f"Saved to: {filename}")
        if not df.empty:
            print(f"Date Range: {df['date'].iloc[-1]} to {df['date'].iloc[0]}")
    else:
        print("No episodes found.")

if __name__ == "__main__":
    get_rss_episodes()