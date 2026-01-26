from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, or_
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os

# --- Database Setup ---
# Assuming the server is run from the project root
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/books.db"

# connect_args={"check_same_thread": False} is needed only for SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    subtitle = Column(String, nullable=True)
    authors = Column(String)  # Stored as comma-separated string
    isbn_13 = Column(String, unique=True, index=True)
    isbn_10 = Column(String, nullable=True)
    categories = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    thumbnail = Column(String, nullable=True)
    published_date = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    google_id = Column(String, unique=True, index=True)
    preview_link = Column(String, nullable=True)
    
    # Merged CSV Columns
    edition_volume = Column(String, nullable=True)
    publisher_info = Column(String, nullable=True)
    book_no = Column(String, nullable=True)

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

app = FastAPI(title="Book Finder API")

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
    # Use 127.0.0.1 for local dev to avoid some binding issues
    uvicorn.run(app, host="127.0.0.1", port=8000)
