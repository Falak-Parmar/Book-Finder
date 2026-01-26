import json
import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add current directory to sys.path to allow importing db
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import db

INPUT_FILE = "data/processed/google_deduped.jsonl"

def ingest_to_db():
    print(f"Ingesting from {INPUT_FILE} into database...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # Ensure tables exist
    db.Base.metadata.create_all(bind=db.engine)
    
    session = db.SessionLocal()
    
    added_count = 0
    skipped_count = 0
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    # Check if exists by ISBN_13
                    isbn_13 = data.get("isbn_13")
                    
                    if isbn_13:
                        existing = session.query(db.Book).filter(db.Book.isbn_13 == isbn_13).first()
                        if existing:
                            skipped_count += 1
                            continue
                    
                    # Also check by Google ID if ISBN missing (though model enforces unique ISBN_13 if not nullable? Schema says unique=True, index=True. But line 21 in db.py says unique=True. If it's None, unique constraint might treat it differently in SQLite, usually multiple NULLs allowed. But better to check.)
                    # Actually, let's trust ISBN_13 as primary dedup key.
                    
                    # Convert list authors to string if needed. Model says String.
                    authors = data.get("authors")
                    if isinstance(authors, list):
                        authors = ", ".join(authors)
                    
                    # Convert categories list to string
                    categories = data.get("categories")
                    if isinstance(categories, list):
                        categories = ", ".join(categories)

                    new_book = db.Book(
                        title=data.get("title"),
                        subtitle=data.get("subtitle"),
                        authors=authors,
                        isbn_13=isbn_13,
                        isbn_10=data.get("isbn_10"),
                        categories=categories,
                        description=data.get("description"),
                        thumbnail=data.get("thumbnail"),
                        published_date=data.get("published_date"),
                        page_count=data.get("page_count"),
                        google_id=data.get("google_id"),
                        preview_link=data.get("preview_link"),
                        edition_volume=data.get("edition_volume"),
                        publisher_info=data.get("publisher_info"),
                        book_no=data.get("book_no")
                    )
                    
                    session.add(new_book)
                    added_count += 1
                    
                    # Commit in batches or one by one? 
                    # One by one is safer for IntegrityError on unexpected constraint
                    if added_count % 100 == 0:
                         session.commit()

                except json.JSONDecodeError:
                    continue
                except IntegrityError:
                    session.rollback()
                    skipped_count += 1
        
        session.commit()
        print(f"Database ingestion complete.")
        print(f"Added: {added_count}")
        print(f"Skipped (Duplicate): {skipped_count}")

    except Exception as e:
        print(f"Error during database ingestion: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    ingest_to_db()
