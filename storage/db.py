from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# The database file location relative to the project root
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

if __name__ == "__main__":
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Database initialized (SQLAlchemy).")
