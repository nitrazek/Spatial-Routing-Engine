import os
from sqlalchemy import text
from sqlmodel import create_engine, Session, SQLModel

class DatabaseManager:
    DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres")
    
    engine = create_engine(DB_URL, echo=False, pool_pre_ping=True)

    @classmethod
    def create_db_and_tables(cls):
        with cls.get_session() as session:
            session.exec(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            session.exec(text("CREATE EXTENSION IF NOT EXISTS pgrouting"))
            session.commit()
        
        SQLModel.metadata.create_all(cls.engine)
        print("Database initialized: Extensions and tables are ready.")

    @classmethod
    def get_session(cls):
        return Session(cls.engine)