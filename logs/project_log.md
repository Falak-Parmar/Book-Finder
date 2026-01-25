# Project Development Log

## [2026-01-16] Initation & Ingestion
### User Prompt:
> "I have a CSV file `Accession Register-Books.csv`. I want to build a system to ingest this, enrich it with OpenLibrary data, store it in a DB, and serve it via API."

### Ingestion Script Development
- **Goal**: Create `ingest.py` to bridge local CSV data with OpenLibrary API.
- **Decisions**:
    - Use `pandas` for efficient CSV reading.
    - Target `https://openlibrary.org/search.json` for flexible search by Title + Author.
    - Implement rate limiting (1 second sleep) to respect OpenLibrary's API etiquette.
    - Fallback Strategy: Title+Author (Strict) -> Short Title+Author -> Title Only.
- **Outcome**: Successful sample run (4/5 hit rate).

## [2026-01-20] Full Scale Migration (OpenAlex)
### User Prompt:
> "Stop whatever you are doing. I found a better API: OpenAlex. It has abstracts and concepts. Switch to that."

### Migration to OpenAlex
- **Issue**: OpenLibrary data was sparse for abstracts. OpenAlex offers "inverted index" abstracts.
- **Action**: 
    - Refactored `ingest.py` to query `https://api.openalex.org/works`.
    - Implemented `reconstruct_abstract` helper to decode inverted indexes.
    - Added `Concepts` -> `Genre` mapping.
    - **Optimization**: Switched to `asyncio` + `aiohttp` with `CONCURRENCY_LIMIT=50`.
    - **Authentication**: Integrated `OPENALEX_API_KEY` to bypass rate limits.
- **Result**: ~36,000 records processed in high-speed mode. Full data saved to `books_raw_enriched.json`.

## [2026-01-20] Transformation & Storage
### User Prompt:
> "What exactly are we doing in Transformation.py?"

### Data Cleaning & Loading
- **Goal**: Transform raw JSON into SQLite.
- **Action**:
    - Refactored `clean.py` to handle OpenAlex schema.
    - Implemented `clean_text` to strip HTML.
    - Logic: `Concepts` (top 5) -> `Genre`.
- **Storage**:
    - Created `books.db` with columns: `id`, `title`, `description`, `genre`, `openlibrary_key` (OpenAlex ID).
    - **Stats**: 36,358 total records. ~2.9k with descriptions. ~4.3k with genres.

## [2026-01-20] Serving API
### User Prompt:
> "Make endpoints for list, search, and details."

### FastAPI Implementation
- **Framework**: FastAPI.
- **Features**:
    - `GET /books`: Pagination.
    - `GET /books?q=...&genre=...`: Semantic/Keyword search (implemented in `db.search_books`).
    - `POST /sync`: Trigger background ingestion.
- **Verification**: Verified via `curl` and `uvicorn`.

## [2026-01-21] Cross-Verification Planning
### User Prompt:
> "Can we verify the data we got from OpenAlex using Google Library api? How long will it take? Can we bypass limits with an API Key?"

### Google Books Verification Plan
- **Goal**: Authenticate accuracy of OpenAlex data.
- **Plan**:
    - Create `verify_google.py`.
    - Support "Sample" (5) or "All" (36k) modes.
    - **Constraint**: Google Books Rate Limit (Public: ~1k/day, Auth: Higher but quota varies).
    - **Advice**: User ADVISED to add `GOOGLE_BOOKS_API_KEY` to environment before running full verification.
- **Outcome**: 
    - Full run hit daily quota limit (~1000 requests).
    - Matched records showed 78% similarity.

## [2026-01-24] Google Enrichment & Deduplication
### User Prompt:
> "Just add the ISBN for now... Make a new jsonl file from the cleaned jsonl with the ISBN."

### ISBN Enrichment
- **Goal**: Append ISBNs to `books_cleaned.jsonl` using Google Books API.
- **Action**:
    - Created `ingestion/append_isbns.py`.
    - Implemented Unauthenticated Bypass (IP-based) to avoid Account Quota limits.
    - **Concurrency**: 50. Supports Resume.
    - **Progress**: ~11,000 / 31,000 processed.
- **Next**: Consolidate, Dedup, and Store.

## Data Transformation - 2026-01-24 21:58:01
- **Task**: Clean `books_enriched.jsonl`
- **Logic**: Removed entries where `found` is False OR (`categories` is [] AND `description` is null).
- **Input File**: `data/processed/books_cleaned_with_isbn.jsonl`
- **Output File**: `data/processed/database_data.jsonl`
- **Stats**:
  - Total Records: 31143
  - Removed Records: 21930
  - Kept Records: 9213

## Data Transformation - 2026-01-25 14:48:40
- **Task**: Create `Google_cleaned.jsonl`
- **Logic**: Merge CSV fields + Filter ISBN + Dedup + Select Columns.
- **Input File**: `data/processed/books_with_isbn.jsonl`
- **Output File**: `data/processed/Google_cleaned.jsonl`
- **Stats**:
  - Total scanned: 31143
  - Removed (No ISBN/Dup): 21930
  - Kept: 9213

## Data Clean Up - 2026-01-25 15:00:00
- **Task**: Deduplicate `Google_cleaned.jsonl`
- **Logic**: Deduplicate by `google_id`.
- **Input File**: `data/processed/Google_cleaned.jsonl`
- **Output File**: `data/processed/google_deduped.jsonl`
- **Stats**:
  - Total Scanned: 31,143
  - Removed (Duplicates): 4,970
  - Kept: 26,173

## Data Transformation - 2026-01-25 15:30:00
- **Task**: Fix Unicode Escaping
- **Logic**: Convert `\uXXXX` sequences to proper text.
- **Input File**: `data/processed/google_deduped.jsonl`
- **Output File**: `data/processed/google_deduped.jsonl` (Overwrite)
- **Stats**:
  - Processed: 26,173 records.

## Storage Implementation - 2026-01-25 15:45:00
- **Task**: Initialize SQLite Database
- **Logic**: Create Schema (Books Table) + Indexing + Data Load.
- **Input File**: `data/processed/google_deduped.jsonl`
- **Output**: `data/books.db`
- **Stats**:
  - Loaded: 26,167 records (6 duplicates removed by DB unique constraint).

