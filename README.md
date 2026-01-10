# Book-Finder
 A robust data pipeline to extract, clean, and store book information (titles, descriptions, genres) to provide a high-quality dataset for an ML-powered semantic search system.

Plausible Repo structure :

book-finder/
│
├── ingestion/
│   └── ingest.py
│
├── transformation/
│   └── clean.py
│
├── storage/
│   └── db.py
│
├── api/
│   └── main.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── logs/
│   └── llm_usage.md
│
├── requirements.txt
└── README.md