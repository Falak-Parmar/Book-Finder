# Transformation LLM Log

## [2026-01-16] Phase 3 Start: Cleaning and Loading
**Goal**: Transform raw JSON data into structured DB records.

**Logic**:
- Read `data/processed/books_raw_enriched.json`.
- For each record:
  - Extract `Title`, `Author` (prefer API data if available, else local CSV).
  - Extract `ISBN` (from API `isbn` array, take first).
  - Extract `Description` (from API, note: API usually returns `key` for works, need to ensure we have the description. *Correction*: The search API often doesn't return the full description. If it's missing, we might keep it null or valid if we fetched details. *Note*: `ingest.py` currently calls `search.json`. Search results usually don't have full descriptions. I might need to do a secondary fetch for description if critical, but for now I'll use what's available or leave blank as per "Transformation" step which says "Clean... remove HTML").
  - Extract `Cover` (use `cover_i` to build URL: `https://covers.openlibrary.org/b/id/{cover_i}-L.jpg`).
- **Action**: Load into `books.db` using `storage.db.upsert_book`.
