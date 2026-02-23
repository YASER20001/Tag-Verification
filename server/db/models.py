from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_number = Column(String, unique=True, nullable=False, index=True)
    tag_description = Column(Text)
    discipline = Column(String)
    status = Column(String, nullable=False, default="Active")  # Active | Void
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    voided_at = Column(DateTime, nullable=True)
    created_by = Column(String, default="system")


class TagDocumentRelationship(Base):
    __tablename__ = "tag_document_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_number = Column(String, nullable=False, index=True)
    document_number = Column(String, nullable=False, index=True)
    document_title = Column(Text)
    document_revision = Column(String)
    found_at = Column(DateTime, default=datetime.utcnow)
    verification_status = Column(String)  # valid_active, valid_void, not_found, shorthand_detected


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_number = Column(String, nullable=False, index=True)
    document_title = Column(Text)
    document_revision = Column(String)
    filename = Column(String)
    file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    verification_status = Column(String, default="pending")  # pending, pass, issues, approved
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    override_justification = Column(Text, nullable=True)
    tags_found = Column(Integer, default=0)
    tags_valid = Column(Integer, default=0)
    tags_void = Column(Integer, default=0)
    tags_not_found = Column(Integer, default=0)
    tags_shorthand = Column(Integer, default=0)
