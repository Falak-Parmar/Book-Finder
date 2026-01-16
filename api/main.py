from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

# Add parent to sys path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from storage.db import get_recent_books, get_book_by_id
from ingestion.ingest import ingest_books
from transformation.clean import clean_and_load

app = FastAPI(title="Book Finder API", version="1.0")

class Book(BaseModel):
    id: int
    local_id: str
    title: str
    author: Optional[str]
    isbn: Optional[str]
    description: Optional[str]
    genre: Optional[str]
    cover_image: Optional[str]
    publication_year: Optional[int]

def run_pipeline(sample_size: int = 10):
    print("Background Task: Starting Pipeline...")
    ingest_books(sample_size=sample_size)
    clean_and_load()
    print("Background Task: Pipeline Finished.")

@app.get("/")
def read_root():
    return {"message": "Welcome to Book Finder API. Visit /docs for Swagger UI."}

@app.get("/books", response_model=List[Book])
def get_books(limit: int = 10):
    """Get a list of recently added books."""
    books = get_recent_books(limit)
    return books

@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    """Get details of a specific book."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks, sample_size: int = 5):
    """
    Trigger the ingestion and transformation pipeline in the background.
    """
    background_tasks.add_task(run_pipeline, sample_size)
    return {"message": f"Pipeline triggered with sample_size={sample_size}. check console for progress."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
