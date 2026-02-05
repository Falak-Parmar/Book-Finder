import argparse
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os
import sys
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to sys.path
sys.path.append(os.getcwd())

from ml.embeddings import EmbeddingManager

# Add current directory to sys.path to ensure we can import storage
# This handles cases where scripts are run from different contexts
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import from storage.db
from storage.db import Book, SessionLocal, engine, Base

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schemas ---
class BookBase(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    authors: Optional[str] = None
    isbn_13: Optional[str] = None
    isbn_10: Optional[str] = None
    categories: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    published_date: Optional[str] = None
    page_count: Optional[int] = None
    google_id: Optional[str] = None
    preview_link: Optional[str] = None
    edition_volume: Optional[str] = None
    publisher_info: Optional[str] = None
    book_no: Optional[str] = None

class BookResponse(BookBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

# --- API ---
# Initialize DB (creates tables if they don't exist)
Base.metadata.create_all(bind=engine)

# --- Background Indexer ---
def background_lazy_indexer():
    """
    Background task that slowly indexes books into ChromaDB.
    """
    logger.info("Background Lazy Indexer thread started.")
    # Wait a bit for the server to fully start
    time.sleep(10)
    
    from ml.index_books import prepare_book_text
    
    while True:
        try:
            if not embedding_manager:
                logger.warning("Embedding Manager not initialized. Lazy Indexer waiting...")
                time.sleep(60)
                continue

            session = SessionLocal()
            try:
                # 1. Get total count in ChromaDB
                collection_count = embedding_manager.collection.count()
                
                # 2. Get total count in SQLite
                sqlite_count = session.query(Book).count()
                
                if collection_count >= sqlite_count:
                    logger.info(f"Indexing complete ({collection_count}/{sqlite_count}). Thread exiting.")
                    break

                logger.info(f"Indexing progress: {collection_count}/{sqlite_count} books in vector store.")
                
                # 3. Find missing books
                # To be efficient, we'll fetch a batch of books and check if they are in Chroma
                # Since we have 27k books, we'll fetch them in chunks
                batch_limit = 50
                books = session.query(Book).offset(collection_count).limit(batch_limit).all()
                
                if not books:
                    break
                
                ids = []
                texts = []
                metadatas = []
                
                for book in books:
                    doc_id = book.isbn_13 or book.google_id or str(book.id)
                    text = prepare_book_text(book)
                    meta = {
                        "book_id": book.id,
                        "title": book.title or "",
                        "isbn_13": book.isbn_13 or ""
                    }
                    ids.append(doc_id)
                    texts.append(text)
                    metadatas.append(meta)
                
                # 4. Add to index
                embedding_manager.add_to_index(ids, texts, metadatas)
                logger.info(f"Indexed batch of {len(ids)} books.")
                
            finally:
                session.close()
                
            # Sleep for 1 minute between batches to stay under Render CPU/RAM limits
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in Lazy Indexer: {e}")
            time.sleep(60)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the lazy indexer in a background thread
    indexer_thread = threading.Thread(target=background_lazy_indexer, daemon=True)
    indexer_thread.start()
    yield
    # Cleanup code (if any) could go here

app = FastAPI(title="Book Finder API", lifespan=lifespan)

# Initialize Embedding Manager
try:
    embedding_manager = EmbeddingManager()
except Exception as e:
    print(f"Warning: Could not initialize EmbeddingManager: {e}")
    embedding_manager = None

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/books/", response_model=List[BookResponse])
def read_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of books with pagination.
    """
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@app.get("/books/{isbn}", response_model=BookResponse)
def read_book_by_isbn(isbn: str, db: Session = Depends(get_db)):
    """
    Retrieve a specific book by ISBN (13 or 10).
    """
    book = db.query(Book).filter(
        or_(Book.isbn_13 == isbn, Book.isbn_10 == isbn)
    ).first()
    
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.get("/search/", response_model=List[BookResponse])
def search_books(q: str = Query(..., min_length=3), db: Session = Depends(get_db)):
    """
    Search books by title or author.
    """
    search_term = f"%{q}%"
    books = db.query(Book).filter(
        or_(
            Book.title.ilike(search_term),
            Book.authors.ilike(search_term),
            Book.isbn_13 == q
        )
    ).all()
    return books

@app.get("/semantic-search/", response_model=List[BookResponse])
def semantic_search_books(q: str = Query(..., min_length=3), db: Session = Depends(get_db)):
    """
    Search books based on semantic meaning using vector embeddings.
    """
    if not embedding_manager:
        raise HTTPException(status_code=503, detail="Semantic search engine is not initialized.")
    
    try:
        # 1. Search in ChromaDB
        search_results = embedding_manager.search(q, n_results=10)
        
        # 2. Extract identifiers (ISBN-13 or Google ID)
        ids = search_results.get("ids", [[]])[0]
        
        if not ids:
            return []
            
        # 3. Retrieve full book records from SQLite
        # We need to map the IDs back to the books table.
        # Since we stored ISBN-13 or Google ID, we check both.
        books = db.query(Book).filter(
            or_(
                Book.isbn_13.in_(ids),
                Book.google_id.in_(ids)
            )
        ).all()
        
        # Sort results based on the order returned from ChromaDB (similarity score)
        id_to_index = {idx: i for i, idx in enumerate(ids)}
        books.sort(key=lambda b: id_to_index.get(b.isbn_13) if b.isbn_13 in id_to_index else id_to_index.get(b.google_id, 999))
        
        return books
        
    except Exception as e:
        print(f"Error during semantic search: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Search Error: {str(e)}")

@app.get("/sync/")
def sync_data():
    """
    Trigger the main data synchronization pipeline.
    This runs main.py in the background.
    """
    import subprocess
    import threading
    import sys
    
    # Global lock to prevent concurrent syncs
    sync_lock = threading.Lock()
    
    def run_pipeline():
        if not sync_lock.acquire(blocking=False):
            print("Pipeline already running. Skipping trigger.")
            return
        try:
            # Using sys.executable to ensure the same interpreter is used
            subprocess.run([sys.executable, "main.py"], cwd=os.getcwd())
        finally:
            sync_lock.release()
        
    thread = threading.Thread(target=run_pipeline)
    thread.start()
    
    return {"status": "success", "message": "Pipeline triggered in background"}

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Run Book Finder API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    # Use 127.0.0.1 for local dev to avoid some binding issues
    uvicorn.run("serving:app", host=args.host, port=args.port, reload=args.reload)
