# 📚 Book-Finder Pipeline

A robust, multi-stage data engineering pipeline designed to bridge the gap between physical library records and digital metadata. This project ingests accession registers, enriches them via the Google Books API, and serves the resulting data through a high-performance FastAPI service.

## 🏗️ The "How & Why"

Library data is often fragmented. Our goal was to take raw accession registers (CSV/BibTeX) and transform them into a semantically rich database that could power a modern search application.

### Core Pipeline Logic
1.  **Sync (`sync_pipeline.py`)**: Crawls the Koha OPAC "New Arrivals" shelf. It handles the transition from physical to digital by fetching current shelf IDs and downloading BibTeX records.
2.  **Incremental Ingestion (`ingestion/ingestion.py`)**: Uses a high-concurrency `aiohttp` approach to fetch metadata from Google Books. It prioritizes *new* records by checking against a persistent JSONL log, preventing redundant API calls.
3.  **Transformation (`transformation/`)**: Resolves the "dirty data" problem. It merges raw CSVs with API results, handles complex Unicode characters, and performs strict deduplication based on Google IDs and ISBNs.
4.  **Serving (`api/serving.py`)**: A production-ready FastAPI layer that supports paginated listings, ISBN-based lookups, and real-time pipeline triggering.

## 🛡️ Technical Challenges Overcome

Building this wasn't straightforward. We hit several significant hurdles:

-   **The "Altcha" Security Wall**: The university OPAC implemented a web-security check that occasionaly blocked automated BibTeX downloads. We implemented a bypass-aware sync that detects these blocks and falls back to existing records instead of corrupting the data.
-   **API Rate Limiting (HTTP 429)**: Google Books API is sensitive to concurrent requests. We solved this by implementing an **Asynchronous Semaphore** with exponential backoff, allowing us to process thousands of records without getting banned.
-   **Data Deduplication**: Merging library CSVs with Google data created a mess of overlapping records. We built a custom cleanup utility that prioritizes records with valid ISBNs and rich metadata, ensuring the final database is lean and accurate.

## 📂 Project Structure

```bash
├── ingestion/       # Async Google Books enrichment
├── transformation/  # Data cleaning & deduplication
├── storage/         # SQLite schema & loaders
├── api/             # FastAPI service (serving.py)
├── data/            # RAW, PROCESSED, and DB files
├── sync_pipeline.py # OPAC Synchronization logic
└── main.py          # Orchestration entry point
```

## 🛠 Usage

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Full Pipeline**:
   ```bash
   python main.py
   ```
   *Note: This will automatically sync, ingest new items, transform, and update the DB.*

3. **Start API Server**:
   ```bash
   python api/serving.py
   ```
   *Access the docs at: http://127.0.0.1:8000/docs*