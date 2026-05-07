import os
from sqlmodel import create_engine, Session, SQLModel

class DatabaseManager:
    DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres")
    
    engine = create_engine(DB_URL, echo=False)

    @classmethod
    def create_db_and_tables(cls):
        SQLModel.metadata.create_all(cls.engine)

    @classmethod
    def get_session(cls):
        return Session(cls.engine)