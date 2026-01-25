from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from . import database, schemas

# Initialize DB (creates tables if they don't exist, though we expect them to)
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Book Finder API")

# CORS Configuration
# allowing all origins for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/books/", response_model=List[schemas.BookResponse])
def read_books(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    Retrieve a list of books with pagination.
    """
    books = db.query(database.Book).offset(skip).limit(limit).all()
    return books

@app.get("/books/{isbn}", response_model=schemas.BookResponse)
def read_book_by_isbn(isbn: str, db: Session = Depends(database.get_db)):
    """
    Retrieve a specific book by ISBN (13 or 10).
    """
    book = db.query(database.Book).filter(
        or_(database.Book.isbn_13 == isbn, database.Book.isbn_10 == isbn)
    ).first()
    
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.get("/sync/")
def sync_data():
    """
    Trigger data synchronization (Placeholder).
    """
    return {"status": "success", "message": "Data synchronization triggered (Placeholder)"}
