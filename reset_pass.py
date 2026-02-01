from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()
u = db.query(User).filter(User.email == "admin@example.com").first()
u.hashed_password = get_password_hash("TuPassFuerte123")
db.commit()
print("ok")
