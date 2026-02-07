import sys
import os
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.getcwd())

from storage import db
from ml.embeddings import EmbeddingManager

def prepare_book_text(book):
    """
    Combines book fields into a single string for embedding.
    """
    parts = []
    if book.title:
        parts.append(f"Title: {book.title}")
    if book.subtitle:
        parts.append(f"Subtitle: {book.subtitle}")
    if book.authors:
        parts.append(f"Authors: {book.authors}")
    if book.categories:
        parts.append(f"Categories: {book.categories}")
    if book.description:
        parts.append(f"Description: {book.description}")
    
    return " | ".join(parts)

import argparse

def index_all_books(batch_size=100, limit=None):
    print("Initializing Database and Embedding Manager...")
    session = db.SessionLocal()
    manager = EmbeddingManager()
    
    print("Fetching books from SQLite...")
    if limit:
        books = session.query(db.Book).limit(limit).all()
    else:
        books = session.query(db.Book).all()
    print(f"Found {len(books)} books.")
    
    ids = []
    texts = []
    metadatas = []
    
    for i, book in enumerate(books):
        # We use ISBN_13 or Google ID as a stable identifier in ChromaDB
        doc_id = book.isbn_13 or book.google_id or str(book.id)
        text = prepare_book_text(book)
        
        # Meta information to help reconstruct or filter
        meta = {
            "book_id": book.id,
            "title": book.title or "",
            "isbn_13": book.isbn_13 or ""
        }
        
        ids.append(doc_id)
        texts.append(text)
        metadatas.append(meta)
        
        # Upsert in batches
        if len(ids) >= batch_size:
            print(f"Indexing batch {i+1}/{len(books)}...")
            manager.add_to_index(ids, texts, metadatas)
            ids = []
            texts = []
            metadatas = []
            
    # Remaining
    if ids:
        print(f"Indexing final batch...")
        manager.add_to_index(ids, texts, metadatas)
        
    print("Indexing complete.")
    session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index Books for Semantic Search")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of records to index per batch")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of books to index (for testing)")
    
    args = parser.parse_args()
    
    index_all_books(batch_size=args.batch_size, limit=args.limit)
