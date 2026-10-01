from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_settings

settings = get_settings()

# Use SQLite for instant operation without external DB
if "sqlite" in settings.DATABASE_URL:
    engine = create_engine(settings.DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
