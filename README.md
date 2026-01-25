# Book-Finder Pipeline

A high-performance data engineering pipeline designed to ingest, clean, enrich, and store book metadata for semantic search applications. This system processes library accession registers, enriches them with Google Books API data, consolidates them into a clean SQLite database, and serves them via a FastAPI service.

## 🚀 Pipeline Overview

### 1. Ingestion (`ingestion/`)
- **`ingestion/ingestion.py`**: Unified script to fetch metadata from Google Books API and enrich with ISBNs.
    - Usage: `python ingestion/ingestion.py`

### 2. Transformation (`transformation/`)
- **`transformation/transformation.py`**: Unified script to merge CSV data, deduplicate records, and clean text/unicode.
    - Usage: `python transformation/transformation.py`

### 3. Storage (`storage/`)
- **`storage/db.py`**: Initializes the SQLite schema and loads the processed data.
    - Database: `data/books.db`

### 4. API (`api/`)
- **`api/api.py`**: FastAPI application serving the book data.
    - **Endpoints**:
        - `GET /books/`: List books (paginated).
        - `GET /books/{isbn}`: Get book details by ISBN.
        - `GET /sync/`: Trigger data sync.
    - **Run**: `uvicorn api.api:app --reload`

## 📂 Project Structure

```
book-finder/
├── ingestion/
│   └── ingestion.py          # Unified Ingestion Script
├── transformation/
│   └── transformation.py     # Unified Transformation Script
├── storage/
│   └── db.py                 # SQLite Loader
├── api/
│   ├── api.py                # FastAPI Application
│   ├── database.py           # SQLAlchemy Setup
│   └── schemas.py            # Pydantic Schemas
├── data/
│   ├── processed/
│   │   └── google_deduped.jsonl  # FINAL processed dataset
│   └── books.db                  # FINAL database
├── logs/
│   └── project_log.md        # Development Log
└── requirements.txt
```

## 🛠 Usage

1. **Ingest Data**:
   ```bash
   python ingestion/ingestion.py
   ```

2. **Transform Data**:
   ```bash
   python transformation/transformation.py
   ```

3. **Load Database**:
   ```bash
   python storage/db.py
   ```

4. **Start API Server**:
   ```bash
   uvicorn api.api:app --reload
   ```