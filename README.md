# Book Finder — Big Data Engineering  
### End-to-End ETL Pipeline + Google Books Enrichment + FastAPI Service  
**Phase 1 Data Engineering Project**

---

## 1. Introduction & Motivation

Modern semantic search systems rely on **clean, structured, and enriched data**.  
Our university library records (OPAC) are often:

- Sparse (basic title/author only)
- Missing rich metadata (descriptions, categories, thumbnails)
- Inconsistent for machine learning tasks

This project addresses those challenges by building a **production-style data pipeline**
that transforms raw accession registers into a **queryable, enriched database**, and exposes
the data through a **FAST API** for downstream applications such as:

- Semantic search (Phase 2)
- Recommendation systems
- Library analytics dashboards

The project follows **real-world data engineering principles**:
- Clear separation of pipeline stages
- Deterministic and resume-safe processing
- CLI-driven configuration
- Database-backed persistence
- API-based data access

---

## 2. High-Level Capabilities

This system provides:

- **Robust Ingestion**: Asynchronous fetching from Google Books API
- **Smart Synchronization**: Altcha-aware scraping of Koha OPAC
- **Data Transformation**: Deduplication, normalization, and cleaning
- **Persistent Storage**: SQLAlchemy + SQLite architecture
- **Pipeline Orchestration**: Unified controller for all stages
- **FastAPI Service**: REST interface for browsing and triggering syncs
- **Fully Self-Documenting CLI**: `--help` support for every script

---

## 3. Project Structure & Responsibilities

Each folder has **one clear responsibility**, mirroring how production pipelines are organized.

```
Book-Finder/
│
├── api/
│   └── serving.py          # FastAPI service & DB models
├── data/
│   ├── raw/                # CSVs and BibTeX files
│   ├── processed/          # Intermediate JSONL files
├── ingestion/
│   └── ingestion.py        # Async Google Books fetcher
├── logs/
│   └── project_log.md      # Technical development log
├── analysis/
│   └── metrics_analysis.py # Data quality reporting
├── storage/
│   └── storage.py          # Database loading logic
├── Transformation/
│   └── transformation.py   # Cleaning & Deduplication
├── main.py                 # Pipeline Orchestrator
├── sync_pipeline.py        # OPAC Synchronization
└── README.md
```

This structure ensures:
- Clear data lineage
- Easy debugging
- Independent execution of each stage

---

## 4. 🔽 Pipeline Architecture (End-to-End Flow)

The pipeline is **linear, deterministic, and restartable**.

```
┌──────────────────────┐
┌──────────────────────┐
│   Raw CSV Registers  │     │   OPAC (Koha)        │
│  (Existing Data)     │     │   (New Arrivals)     │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           ▼                            ▼
┌───────────────────────────────────────────────────┐
│ SYNC & MERGE                                      │
│ - Crawl New Arrivals (Altcha-aware)               │
│ - Merge with Accession Register                   │
│ - Detect Incremental Changes                      │
└──────────────────────────┬────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────┐
│ INGESTION (Google Books)                          │
│ - Async I/O (aiohttp)                             │
│ - Rate Limiting & Backoff                         │
│ - Fetch Metadata (ISBN, Desc, Thumbnails)         │
└──────────────────────────┬────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────┐
│ TRANSFORMATION                                    │
│ - Normalize Titles/Authors                        │
│ - Deduplicate (ISBN > Google ID > Title match)    │
│ - Merge Metadata Conflicts                        │
└──────────────────────────┬────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────┐
│ STORAGE                                           │
│ - JSONL → SQLite                                  │
│ - SQLAlchemy ORM                                  │
│ - Integrity Checks                                │
└──────────────────────────┬────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────┐
│ FASTAPI SERVICE                                   │
│ - Browse & Paginate                               │
│ - Search (Title/Author/ISBN)                      │
│ - Trigger Pipeline Sync                           │
└───────────────────────────────────────────────────┘
```

---

## 5. Running the Complete Pipeline

To execute **all ETL stages in order**, run:

```bash
python main.py
```

You can also skip specific stages or set limits:
```bash
python main.py --skip-sync --ingest-limit 100
```

### Final Artifact

```
book_finder.db
```

This database becomes the **single source of truth** for the API.

---

## 6. Detailed Stage Explanations

---

### 6.1 Sync Stage (`sync_pipeline.py`)

**Goal:**  
Keep the local dataset aligned with the physical library's "New Arrivals".

**Key Design Choices**
- **Altcha-Awareness**: Detects anti-bot protection and degrades gracefully (warns user instead of crashing).
- **Incremental Logic**: Checks for new IDs against existing CSV to minimize redundant processing.
- **BibTeX Parsing**: Converts library standard format to project CSV schema.

**Default Run**
```bash
python sync_pipeline.py
```

---

### 6.2 Ingestion Stage (`ingestion.py`)

**Goal:**  
Enrich sparse CSV records with rich metadata from Google Books.

**Key Design Choices**
- **Asyncio + Aiohttp**: High-throughput fetching.
- **Semaphore Handling**: Limits concurrency to prevent IP bans.
- **Resumable State**: Skips already processed IDs in `output` JSONL.

**Default Run**
```bash
python ingestion/ingestion.py --limit 100
```

**Custom Input / Output**
```bash
python ingestion/ingestion.py \
  --input "data/raw/custom_list.csv" \
  --output "data/processed/my_enrichment.jsonl"
```

---

### 6.3 Transformation Stage (`transformation.py`)

**Goal:**  
Clean, normalize, and deduplicate the noisy API results.

**Operations**
- **Step 1 (Transform)**: Merges CSV metadata (Book No, Publisher) with Google Metadata.
- **Step 2 (Dedup)**: Resolves duplicates using a hierarchy: `ISBN-13` > `Google ID` > `Title+Author`.

**Why this matters:**  
API results often return the same book for slightly different queries. This stage ensures uniqueness.

**Default Run**
```bash
python Transformation/transformation.py
```

---

### 6.4 Storage Stage (`storage.py`)

**Goal:**  
Persist final records into a structured Relational Database.

**Design Choices**
- **SQLAlchemy**: ORM-based access for future portability (e.g., to PostgreSQL).
- **Batch Commits**: Improves write performance.
- **Integrity Handling**: Skips duplicates at the database level if pre-checks fail.

**Default Run**
```bash
python storage/storage.py
```

---

## 7. FastAPI Service

The FastAPI layer provides **read-only access** to the final dataset and **control access** to the pipeline.

### Start API Server

```bash
python api/serving.py --reload
```

### Key Endpoints

- `GET /books/` – Paginated book listing  
- `GET /books/{isbn}` – ISBN lookup  
- `GET /search/?q=term` – Partial match search  
- `GET /sync/` – Trigger background pipeline run  

**Swagger UI:**  
http://127.0.0.1:8000/docs

---

## 8. Pipeline Statistics

All statistics can be reproduced using `analysis/metrics_analysis.py` or the `analysis/project_metrics.ipynb` notebook.

### 8.1 Data Flow Summary

| Stage | Input Records | Output Records | Success Rate |
|------|--------------:|---------------:|-------------:|
| **Source (CSV)** | 36,358 | - | - |
| **Ingestion** | ~36,358 | 33,502 | **92.1%** |
| **Transformation** | 33,502 | 26,173 | **78.1%** (Dedup) |
| **Final DB** | 26,173 | 26,173 | **100%** |

### 8.2 Enrichment Quality

| Metric | Value |
|------|------:|
| **Total Source Records** | **36,358** |
| **Successful Matches** | **33,502** |
| **Final Unique Books** | **26,173** |
| **Database Size** | **~41 MB** |

**Observation**
> The pipeline successfully enriches over 90% of the library catalog, proving the effectiveness of the fuzzy matching strategy used during ingestion.

---

## 9. Data Dictionary (Core Fields)

| Field | Description |
|------|------------|
| `id` | Internal DB Primary Key |
| `isbn_13` | 13-digit ISBN (Primary Identifier) |
| `title` | Book Title (from Google Books) |
| `authors` | Comma-separated list of authors |
| `description` | Full text summary/blurb |
| `categories` | Genre/Subject tags |
| `thumbnail` | URL to cover image |
| `average_rating` | Google Books rating |
| `book_no` | Original Library Call Number |

---

## 10. Design Philosophy

This project emphasizes:

- **Separation of concerns**: Each module does one thing well.
- **Fail-Safe Operation**: Network errors or API limits do not crash the pipeline.
- **Reproducibility**: Everything is code-defined and scriptable.
- **Transparency**: Extensive logging (`logs/project_log.md`) tracks all decisions.

---

## 11. Conclusion

This project demonstrates a **complete, production-style data pipeline**:

- Quantifiable data-quality improvements  
- Deterministic ETL stages  
- Resume-safe enrichment  
- Persistent storage  
- API-based data access  

It bridges the gap between 'operational' library lists and 'analytical' datasets, forming a strong foundation for **Phase 2: Semantic Search**.

---

## Authors

**202518053 : Falak Parmar**  
**202518035 : Aditya Jana**  

DA-IICT — Big Data Engineering
