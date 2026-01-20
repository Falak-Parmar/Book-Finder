# Ingestion LLM Log

## [2026-01-16] Phase 1 Start: Ingestion Script Development
**Goal**: Create `ingest.py` to bridge local CSV data with OpenLibrary API.

**Decisions**:
- Use `pandas` for efficient CSV reading.
- Target `https://openlibrary.org/search.json` for flexible search by Title + Author.
- Implement rate limiting (1 second sleep) to respect OpenLibrary's API etiquette.
- Limit initial run to a small sample (e.g., 5 rows) for verification.
- Save output to `data/processed/books_raw_enriched.json` to preserve nested API structures before flattening/cleaning in the Transformation phase.

## [2026-01-16] Ingestion Refinement: Improving Search Hit Rate
**Observation**: Initial run with specific `title` + `author` search yielded 0 matches for 5 records. The CSV data has subtitles and specific author formats that might mismatch OpenLibrary's index.

**Action**: Updated `ingest.py` to use a fallback strategy.
1.  **Strict Search**: Title + Author.
2.  **Fallback 1**: Cleaned Title (split by `:`) + Author.
3.  **Fallback 2**: Title Only (broad search).

**Result**: 
- Ran with sample size 5.
- **Success Rate**: 4/5 books found.
- Matches were found using "Short Title + Author" and "Title-only" strategies.
- Enriched data saved to `data/processed/books_raw_enriched.json`.

**Next**: Move to Storage phase to define the schema for persisting these records.

## [2026-01-20] Ingestion Optimization: Asynchronous Processing
**Issue**: The synchronous 1-second delay per book was projected to take over 10 hours for the full dataset (36k records).
**Action**: Refactored `ingest.py` to use `asyncio` and `aiohttp`.
- **Concurrency**: Process 5 requests in parallel using a Semaphore.
- **Benefits**: Significantly higher throughput while maintaining a polite request rate.
- **Status**: Script updated. Initial tests show successful retrieval with strict and fallback matching.
