# Book-Finder Pipeline

A high-performance data engineering pipeline designed to ingest, clean, enrich, and store book metadata for semantic search applications. This system processes library accession registers, enriches them with Google Books API data, and consolidates them into a clean SQLite database.

## 🚀 Pipeline Overview

The pipeline consists of three main phases:

### 1. Ingestion (`ingestion/`)
- **`ingestion/ingest_google.py`**: Fetches metadata (Title, Description, Authors, Thumbnails) from Google Books API based on the legacy CSV input.
- **`ingestion/append_isbns.py`**: Cross-references records to fetch industry-standard ISBNs (ISBN-13/ISBN-10) for accurate identification.

### 2. Transformation (`transformation/`)
- **`transformation/transform_books.py`**: Merges API data with raw CSV fields (Publisher, Edition, Book No).
- **`transformation/deduplicate.py`**: Removes duplicate entries based on unique `google_id` to ensure dataset integrity.
- **`transformation/fix_unicode.py`**: post-processing script to unescape unicode characters (e.g., `\u0026` -> `&`) for human-readable text.

### 3. Storage (`storage/`)
- **`storage/db.py`**: Initializes the SQLite schema and loads the final processed JSONL data.
- **Database**: `data/books.db`
    - **Table**: `books`
    - **Count**: 26,167 unique records.
    - **Schema**:
        - `id` (PK)
        - `title`, `subtitle`, `authors`
        - `description`, `categories`
        - `isbn_13` (Indexed, Unique), `isbn_10`
        - `google_id` (Indexed)
        - `thumbnail`, `preview_link`
        - `published_date`, `page_count`
        - `edition_volume`, `publisher_info`, `book_no` (from CSV)

## 📂 Project Structure

```
book-finder/
├── ingestion/
│   ├── ingest_google.py      # Google Books API Fetcher
│   └── append_isbns.py       # ISBN Enrichment
├── transformation/
│   ├── transform_books.py    # Data Merge Logic
│   ├── deduplicate.py        # ID-based Deduplication
│   └── fix_unicode.py        # Text Cleaning
├── storage/
│   └── db.py                 # SQLite Loader
├── data/
│   ├── processed/
│   │   └── google_deduped.jsonl  # FINAL processed dataset
│   └── books.db                  # FINAL database
├── logs/
│   └── project_log.md        # Detailed Development Log
└── requirements.txt
```

## 📊 Dataset Statistics
- **Total Input Scanned**: 31,143 records.
- **Duplicates Removed**: 4,970.
- **Final DB Count**: 26,167.

## 🛠 Usage

To rebuild the database from the processed file:
```bash
python3 storage/db.py
```

To query the data:
```bash
sqlite3 data/books.db "SELECT title, authors FROM books LIMIT 5;"
```