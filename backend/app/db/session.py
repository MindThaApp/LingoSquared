from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

class Base(DeclarativeBase): pass
engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=20, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
def get_db():
    with SessionLocal() as db: yield db
