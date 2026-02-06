import argparse
import json
import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add current directory to sys.path to allow importing db
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import db

DEFAULT_INPUT_FILE = "data/processed/google_deduped.jsonl"

def ingest_to_db(input_file):
    print(f"Ingesting from {input_file} into database...")
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # Ensure tables exist
    db.Base.metadata.create_all(bind=db.engine)
    
    session = db.SessionLocal()
    
    added_count = 0
    skipped_count = 0
    
    # Pre-fetch existing IDs for fast deduplication
    print("Pre-fetching existing records to optimize incremental update...")
    existing_isbns = set()
    existing_google_ids = set()
    try:
        # Fetch only necessary columns
        results = session.query(db.Book.isbn_13, db.Book.google_id).all()
        for r_isbn, r_gid in results:
            if r_isbn:
                existing_isbns.add(r_isbn)
            if r_gid:
                existing_google_ids.add(r_gid)
        print(f"Loaded {len(existing_isbns)} ISBNs and {len(existing_google_ids)} Google IDs from DB.")
    except Exception as e:
        print(f"Error fetching existing records: {e}")
        session.close()
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    # Check if exists by ISBN_13
                    isbn_13 = data.get("isbn_13")
                    if isbn_13 and isbn_13 in existing_isbns:
                        skipped_count += 1
                        continue
                    
                    # Also check by Google ID
                    g_id = data.get("google_id")
                    if g_id and g_id in existing_google_ids:
                        skipped_count += 1
                        continue
                    
                    # Convert list authors to string if needed.
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
                    
                    # Update local sets to catch duplicates within the same file
                    if isbn_13:
                        existing_isbns.add(isbn_13)
                    if g_id:
                        existing_google_ids.add(g_id)
                    
                    # Commit in batches of 100 
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
    parser = argparse.ArgumentParser(description="Ingest Deduplicated Data into Database")
    parser.add_argument("--input", default=DEFAULT_INPUT_FILE, help="Path to deduplicated JSONL file")
    
    args = parser.parse_args()
    ingest_to_db(args.input)
