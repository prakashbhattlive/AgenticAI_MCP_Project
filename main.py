import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import List, Optional, Generator

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise RuntimeError(
        "Missing required DB credentials. "
        "Set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME in a .env file."
    )

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text)  # store vector as string, later cast to vector


Base.metadata.create_all(bind=engine)

app = FastAPI(title="MCP Document Server")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DocumentIn(BaseModel):
    title: str
    content: str
    embedding: Optional[str] = None


class DocumentOut(BaseModel):
    id: int
    title: str
    content: str
    embedding: Optional[str] = None

    class Config:
        from_attributes = True


@app.post("/documents/", response_model=DocumentOut, status_code=201)
def add_document(doc: DocumentIn, db: Session = Depends(get_db)):
    """Create a new document"""
    new_doc = Document(
        title=doc.title,
        content=doc.content,
        embedding=doc.embedding
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc


@app.get("/documents/", response_model=List[DocumentOut])
def list_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all documents with pagination"""
    documents = db.query(Document).offset(skip).limit(limit).all()
    return documents


@app.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    """Get a specific document by ID"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.put("/documents/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: int, doc: DocumentIn, db: Session = Depends(get_db)):
    """Update an existing document"""
    existing_doc = db.query(Document).filter(Document.id == doc_id).first()
    if not existing_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    existing_doc.title = doc.title
    existing_doc.content = doc.content
    if doc.embedding is not None:
        existing_doc.embedding = doc.embedding
    
    db.commit()
    db.refresh(existing_doc)
    return existing_doc


@app.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """Delete a document"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(document)
    db.commit()
    return None


@app.get("/documents/search/title/{query}")
def search_by_title(query: str, db: Session = Depends(get_db)):
    """Search documents by title"""
    documents = db.query(Document).filter(
        Document.title.ilike(f"%{query}%")
    ).all()
    return documents


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MCP Document Server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)