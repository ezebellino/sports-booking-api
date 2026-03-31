from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.user import User


engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()
email = "admin@example.com"

user = db.query(User).filter(User.email == email).first()
if not user:
    raise SystemExit(f"No existe un usuario con email {email}")

user.role = "admin"
db.commit()
print(f"{email} ahora es admin")
