<<<<<<< HEAD
📚 Book Finder — Big Data Engineering Project

Overview

This project is part of the Big Data Engineering course at DA-IICT. The objective is to design and implement a robust data engineering pipeline that transforms sparse university library records into a high-quality, enriched dataset suitable for powering an ML-based semantic book search system.

The motivating use case is:

A user should be able to search for “a story about a lonely robot in space” and retrieve relevant books, even if those exact words do not appear in the original library metadata.

This repository implements Phase 1 (Data Engineer role) of the overall project.

⸻
=======
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
>>>>>>> 67eac781ebcd4f5da0b98c564eea6660b70a0f86

Problem Context & Motivation

<<<<<<< HEAD
University library datasets are typically operational, not analytical:
	•	Titles and authors are present
	•	Rich metadata (ISBNs, descriptions, subjects, thumbnails) is missing
	•	Records are inconsistent and difficult to use for downstream ML tasks
=======
```bash
├── ingestion/       # Async Google Books enrichment
├── transformation/  # Data cleaning & deduplication
├── storage/         # SQLite schema & loaders
├── api/             # FastAPI service (serving.py)
├── data/            # RAW, PROCESSED, and DB files
├── sync_pipeline.py # OPAC Synchronization logic
└── main.py          # Orchestration entry point
```
>>>>>>> 67eac781ebcd4f5da0b98c564eea6660b70a0f86

At DA-IICT, the library accession register CSV contains only:
	•	Accession metadata
	•	Title
	•	Author / Editor
	•	Publisher, Year, Pages

<<<<<<< HEAD
This project bridges that gap by:
	1.	Treating the DA-IICT CSV as the ground-truth scope
	2.	Enriching each record using external public APIs (Google Books)
	3.	Cleaning, deduplicating, and normalizing the data
	4.	Exposing the curated dataset via a FastAPI service for future ML use

⸻

High-Level Architecture

The pipeline is designed as four explicit stages, mirroring real-world data engineering systems:
	1.	Ingestion – Collect raw data from multiple sources
	2.	Transformation – Clean, normalize, and deduplicate
	3.	Storage – Persist curated data in a relational database
	4.	Serving – Expose data through stable APIs

Each stage is implemented as a separate module, enabling clarity, testability, and extensibility.

⸻

Data Sources

Primary Source (Scope Anchor)
	•	DA-IICT Library Accession Register (CSV)
	•	Defines the authoritative list of books
	•	Ensures compliance with the DAU-only scope requirement

Secondary Source (Enrichment)
	•	Google Books API
	•	Used only to enrich existing DA-IICT titles
	•	Provides:
	•	ISBN-10 / ISBN-13
	•	Descriptions / blurbs
	•	Subjects / categories
	•	Thumbnails and language metadata

No new books are introduced from APIs—only metadata augmentation is performed.

⸻

Detailed Pipeline Design

1. Sync Layer (sync_pipeline.py)

Purpose:
Handle synchronization with the library’s OPAC system and manage incremental updates.

What it does:
	•	Crawls the Koha OPAC “New Arrivals” shelf
	•	Dynamically identifies shelf IDs
	•	Downloads BibTeX records where possible

Key Challenge:
	•	The OPAC uses Altcha, a proof-of-work security mechanism that blocks automated scraping

Design Decision:
	•	Detect security blocks gracefully
	•	Fall back to existing records instead of corrupting the pipeline
	•	Log warnings rather than failing hard

This ensures the pipeline remains fault-tolerant.

⸻

2. Ingestion Layer (ingestion.py)

Purpose:
Fetch rich metadata for DA-IICT books using external APIs.

Key Design Choices:
	•	Asynchronous requests using aiohttp
	•	Concurrency control via asyncio.Semaphore
	•	Exponential backoff with jitter to handle HTTP 429 rate limits
	•	Incremental ingestion using JSONL logs to avoid re-fetching data

Why async?
	•	The CSV contains ~26,000 records
	•	Synchronous API calls would be prohibitively slow and rate-limited

Output:
	•	Line-delimited JSON (.jsonl) files containing raw enriched metadata

⸻

3. Transformation Layer (transformation.py)

Purpose:
Resolve real-world “dirty data” issues and prepare the dataset for storage.

Operations performed:
	•	Unicode normalization (handling non-standard characters)
	•	Title and author normalization
	•	Removal of placeholder / empty descriptions
	•	Deduplication using:
	•	ISBN-13 (preferred)
	•	Google Books ID (fallback)

Conflict Resolution Strategy:
	•	Prefer records with valid ISBNs
	•	Merge metadata instead of duplicating rows

This stage converts raw API responses into a clean, analytical dataset.

⸻

4. Storage Layer (storage.py, db.py)

Purpose:
Persist curated data in a structured, queryable format.

Technology:
	•	SQLite
	•	SQLAlchemy ORM

Why SQLite?
	•	Lightweight and portable
	•	No external database dependency
	•	Ideal for coursework and reproducibility

Schema Highlights:
	•	books table
	•	Indexed columns on isbn_13 and title
	•	Enforced schema integrity

⸻

5. Serving Layer (serving.py)

Purpose:
Expose the curated dataset to downstream consumers (Phase 2: Data Scientist role).

Implemented using:
	•	FastAPI

Endpoints:
	•	GET /books – Paginated access to enriched books
	•	GET /books/{isbn} – ISBN-based lookup
	•	GET /search – Partial title/author search
	•	GET /sync – Trigger pipeline execution without stopping the API

Design Principle:
Separation of concerns — the API does not perform ingestion logic directly; it orchestrates it.

⸻

Orchestration (main.py)

main.py acts as the control plane of the system:

Execution order:
	1.	Run OPAC sync
	2.	Identify new or updated records
	3.	Trigger incremental ingestion
	4.	Apply transformations
	5.	Update SQLite database

This ensures:
	•	Idempotency
	•	Recoverability
	•	Minimal redundant computation

⸻

LLM Usage & Transparency

LLMs were used as assistive tools, not black boxes.

All interactions are logged in:

logs/project_log.md

Each entry records:
	•	Purpose of the prompt
	•	Tool used
	•	Summary of response
	•	How the output was applied

This satisfies the project’s LLM policy and ensures full transparency.

⸻

How to Run

Install Dependencies

pip install -r requirements.txt

Run Full Pipeline

python main.py

Start API Server

python serving.py

Visit API docs at:

http://127.0.0.1:8000/docs


⸻

Learning Outcomes

Through this project, we gained hands-on experience with:
	•	Designing end-to-end data pipelines
	•	Asynchronous ingestion at scale
	•	API rate-limit handling
	•	Schema design and relational storage
	•	Serving data for ML workloads

Most importantly, the project demonstrates how engineering decisions directly affect the usability of downstream machine learning systems.

⸻

Future Work (Phase 2)
	•	Generate embeddings from book descriptions
	•	Implement semantic search
	•	Rank results based on query relevance
	•	Build a lightweight frontend

⸻

Authors

DA-IICT — Big Data Engineering Project
=======
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
>>>>>>> 67eac781ebcd4f5da0b98c564eea6660b70a0f86
