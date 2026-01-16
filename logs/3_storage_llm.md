# Storage LLM Log

## [2026-01-16] Phase 2 Start: Database Implementation
**Goal**: Create a SQLite database to store book records.

**Schema Design**:
- Table: `books`
- Columns:
  - `id`: Primary Key (Auto-increment)
  - `local_id`: Original CSV ID (to bridge back to source)
  - `title`: Text
  - `author`: Text
  - `isbn`: Text (nullable)
  - `description`: Text (nullable)
  - `genre`: Text (nullable)
  - `cover_image`: Text (URL)
  - `openlibrary_key`: Text (nullable)

**Implementation**:
- Using `sqlite3` (standard library).
- Providing `init_db()` to create tables.
- Providing `upsert_book()` to insert or update records (based on `local_id` or `openlibrary_key`).
