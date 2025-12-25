
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise RuntimeError(
        "Missing required DB credentials. "
        "Set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME in a .env file."
    )

DATABASE_URL = (f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text)
    content = Column(Text)
    embedding = Column(Text)  # we’ll store vector as string, later cast to vector

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MCP Server")

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DocumentIn(BaseModel):
    title: str
    content: str

@app.post("/documents/")
def add_document(doc: DocumentIn, db: Session = Depends(get_db)):