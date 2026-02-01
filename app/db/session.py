from sqlalchemy import create_engine # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import sessionmaker # pyright: ignore[reportMissingImports]
from app.core.config import settings # pyright: ignore[reportMissingImports]

print("Database URL:", settings.DATABASE_URL)  # Debugging line

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
