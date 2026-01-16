# Serving LLM Log

## [2026-01-16] Phase 4 Start: FastAPI Implementation
**Goal**: Expose data and pipeline control via REST API.

**Endpoints**:
- `GET /`: Health check.
- `GET /books`: List recently added books. params: `limit` (default 10).
- `GET /books/{id}`: detailed view.
- `POST /sync`: **Trigger Pipeline**.
  - Calls `ingestion.ingest_books(sample_size=None)` (Warning: Long running! For demo maybe keep small).
  - Calls `transformation.clean_and_load()`.
  
**Implementation Details**:
- use `FastAPI` and `uvicorn`.
- `pydantic` models for response documentation (optional but good).
- Error handling for DB access.
