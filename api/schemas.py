from pydantic import BaseModel
from typing import Optional

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

    class Config:
        from_attributes = True
