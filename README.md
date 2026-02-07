# EconTalk RAG: AI-Powered Podcast Search

**An AI research assistant that allows users to chat with 15+ years of the [EconTalk](https://www.econtalk.org/) podcast archives.**

This project uses Retrieval-Augmented Generation (RAG) to ground LLM answers in actual transcript data, allowing for precise, cited responses to questions about economics, philosophy, and modern life.

---

## Table of Contents
* [Project Context](#-project-context)
* [Tech Stack](#-tech-stack)
* [Project Structure](#-project-structure)
* [Installation & Setup](#-installation--setup)
* [Building the Database](#-building-the-database)
* [Usage](#-usage)
* [Challenges, Current Limitations, & Future Work](#-challenges-current-limitations--future-work)
* [Sample Questions to Try](#-sample-questions-to-try)

---

## Project Context
EconTalk, hosted by Russ Roberts, has been running weekly since 2006. With over 1000+ episodes, it represents a massive unstructured dataset of economic thought. Standard keyword search fails to capture the nuance of these conversations.

This project scrapes the entire archive, chunks the transcripts into semantic vectors, and stores them in a Vector Database (Qdrant). When a user asks a question, the system retrieves the most relevant segments and feeds them to GPT-4 to generate an answer based *only* on the text provided.

## Tech Stack
* **Language:** Python 3.10+
* **Data Pipeline:** Pandas, BeautifulSoup, Playwright (Scraping)
* **Vector Database:** Qdrant (Dockerized)
* **AI/LLM:** OpenAI API (Embeddings: `text-embedding-3-small`, Chat: `gpt-4o`)
* **Frontend:** Streamlit
* **Utilities:** `python-dotenv`, `tqdm`

---

## Project Structure

```text
econtalk-rag/
│
├── .env                    # API keys (not committed)
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
│
├── data/                   # Data artifacts (ignored by Git)
│   ├── raw/                # Raw scraped JSON files
│   ├── clean/              # Processed/parsed transcripts
│   ├── econtalk_chunks.jsonl   # Semantic chunks ready for embedding
│   └── econtalk_vectors.jsonl  # Final vectors with metadata
│
├── scripts/                # Data engineering pipeline
│   ├── 01_fetch_feed.py    # Inventory: get episode list from RSS
│   ├── 02_scrape.py        # Extraction: download transcripts
│   ├── 03_clean.py         # Transformation: parse HTML & identify speakers
│   ├── 04_chunk.py         # Chunking: split text with overlap
│   ├── 05_embed.py         # Embedding: generate vectors via OpenAI
│   ├── 06_load_db.py       # Loading: incorporate into Qdrant
│   └── run_pipeline.py     # Master script to run all steps
│
├── app.py                  # Web interface (Streamlit)
└── rag_app.py              # CLI interface
```

---

## Installation & Setup

1. **Prerequisites**
* Python 3.10 or higher
* Docker Desktop (for running Qdrant)
* OpenAI API Key

2. **Environment Setup**<br/>
Clone the repo and create a virtual environment:

```bash
git clone [https://github.com/yourusername/econtalk-rag.git](https://github.com/yourusername/econtalk-rag.git)
cd econtalk-rag

python -m venv venv
source venv/bin/activate
```

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Install dependencies:

```bash
pip install -r requirements.txt
playwright install
```

3. **Configuration**  
Create a .env file in the root directory:

```
OPENAI_API_KEY=sk-proj-your-key-here
```

4. **Start the Database**  
Launch Qdrant using Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    -d qdrant/qdrant
```

---

## Building the Database
You can run the entire pipeline at once using the master script:

```bash
python scripts/run_pipeline.py
```

Or run the individual steps manually:
1. **Inventory:** 'python scripts/01_fetch_feed.py'
2. **Scrape:** 'python scripts/02_scrape.py'
3. **Clean:** 'python scripts/03_clean.py'
4. **Chunk:** 'python scripts/04_chunk.py'
5. **Embed:** 'python scripts/05_embed.py' (Note: Incurs OpenAI API costs)
6. **Load:** 'python scripts/06_load_db.py'

---

## Usage

### Web Interface ###
Launch the interactive dashboard to chat with the data and view sources.

```bash
streamlit run app.py
```

### CLI Clickbot ###
Run a quick test in your terminal.

```bash
streamlit run rag_app.py
```

---

## Challenges, Current Limitations & Future Work

### Challenges & Current Limitations ###
* **Transcript Availability:** Due to inconsistent speaker labeling and lower audio/transcript quality in the show's early years, the dataset is strictly limited to episodes released on or after January 23, 2012.
* **Static Database:** The database is currently a snapshot. It does not automatically update when new episodes are released on Mondays.
* **Cost:** Re-embedding the entire corpus can cost $5-$10 USD. Incremental updates are needed to scale efficiently.

### Future Work ###
* **Hybrid Search:** Implement Qdrant's sparse vectors (BM25) alongside dense vectors. This would allow the system to match specific keywords (e.g., "Coase Theorem") even if the semantic meaning is slightly off.
* **Automated Cron Job:** Create a GitHub Action or Airflow DAG to run '01_fetch_feed.py'weekly, identify new episodes, and run the pipeline only for those new files.
* **Audio RAG:** Use OpenAI's Whisper model to re-transcribe the oldest episodes for better accuracy and timestamping.
* **Open Source Models:** Experiment with running the embedding and chat steps locally using Ollama (Llama 3 or Mistral) to remove API costs and increase privacy.

---

## Sample Questions to Try

* *What does Mike Munger say about voting?*
* *How does Russ Roberts define 'The Wild'?*
* *Summarize the debate on the minimum wage from the 2015 episodes.*
* *What did Sam Altman say about the future of AI?*