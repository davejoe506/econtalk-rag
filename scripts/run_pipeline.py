import subprocess
import sys
import os
import time

# --- Configuration ---
PIPELINE_STEPS = [
    "01_fetch_feed.py",
    "02_scrape.py",
    "03_clean.py",
    "04_chunk.py",
    "05_embed.py",
    "06_load_db.py"
]

def run_step(script_name):
    """Runs a single script and checks for errors."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        print(f"Error: Could not find script '{script_name}' at {script_path}")
        sys.exit(1)

    print(f"\n" + "="*50)
    print(f"Running: {script_name}")
    print("="*50)

    try:
        # Run the script and wait for it to finish.
        start_time = time.time()
        subprocess.run(["python", script_path], check=True)
        duration = time.time() - start_time
        print(f"Finished {script_name} in {duration:.2f} seconds.")
        
    except subprocess.CalledProcessError:
        print(f"\nPipeline failed.")
        print(f"Script '{script_name}' encountered an error.")
        sys.exit(1)

def main():
    print("Starting EconTalk RAG Pipeline...")
    print(f"Found {len(PIPELINE_STEPS)} steps to execute.\n")

    for script in PIPELINE_STEPS:
        # Safety check: Ask before spending money
        if "embed" in script:
            print(f"\Warning: The next step is '{script}'.")
            print("   This step interacts with the OpenAI API and will incur costs.")
            user_input = input("   Do you want to proceed? (y/n): ")
            if user_input.lower() != 'y':
                print("Stopping pipeline by user request.")
                sys.exit(0)

        run_step(script)

    print("\n" + "="*50)
    print("Pipeline complete. The database is updated.")
    print("="*50)

if __name__ == "__main__":
    main()