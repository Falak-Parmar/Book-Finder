import sqlite3
import json
import os

DB_PATH = "data/books.db"

def init_db():
    """Initialize the SQLite database with the new schema."""
    if os.path.exists(DB_PATH):
        # Backup existing DB just in case, or we can overwrite if user wants fresh start.
        # Given "Phase 7: Storage (Final)", let's start fresh for cleanliness.
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # New Schema based on Google_cleaned / google_deduped
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            subtitle TEXT,
            authors TEXT,
            isbn_13 TEXT, 
            isbn_10 TEXT,
            categories TEXT,
            description TEXT,
            thumbnail TEXT,
            published_date TEXT,
            page_count INTEGER,
            google_id TEXT,
            preview_link TEXT,
            
            -- Merged CSV Columns
            edition_volume TEXT,
            publisher_info TEXT,
            book_no TEXT
        )
    """)
    
    # Create Index strictly on isbn_13 for uniqueness (and google_id for lookups)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_isbn_13 ON books(isbn_13)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_google_id ON books(google_id)")
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def load_data(jsonl_path):
    """Load data from JSONL into the database."""
    if not os.path.exists(jsonl_path):
        print(f"File not found: {jsonl_path}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Loading data from {jsonl_path}...")
    
    count = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line)
                
                # Prepare tuple for insertion
                # Handle lists (authors, categories) -> convert to string if not already
                authors = record.get("authors")
                if isinstance(authors, list):
                    authors = ", ".join(authors)
                
                categories = record.get("categories")
                if isinstance(categories, list):
                    categories = ", ".join(categories)

                cursor.execute("""
                    INSERT OR IGNORE INTO books (
                        title, subtitle, authors, isbn_13, isbn_10, 
                        categories, description, thumbnail, published_date, 
                        page_count, google_id, preview_link,
                        edition_volume, publisher_info, book_no
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get("title"),
                    record.get("subtitle"),
                    authors,
                    record.get("isbn_13"),
                    record.get("isbn_10"),
                    categories,
                    record.get("description"),
                    record.get("thumbnail"),
                    record.get("published_date"),
                    record.get("page_count"),
                    record.get("google_id"),
                    record.get("preview_link"),
                    record.get("edition_volume"),
                    record.get("publisher_info"),
                    record.get("book_no")
                ))
                count += 1
                
                if count % 1000 == 0:
                    print(f"Inserted {count}...")
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error inserting record: {e}")

    conn.commit()
    conn.close()
    print(f"Successfully loaded {count} records into {DB_PATH}")

if __name__ == "__main__":
    init_db()
    load_data("data/processed/google_deduped.jsonl")
