from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base
import uuid

class DocumentQuote(Base):
    """
    Model representing a quote extracted from a document.
    """
    __tablename__ = 'document_quotes'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    document_id = Column(String(36), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    quote_text = Column(Text, nullable=False)
    speaker = Column(String(255), nullable=True)
    speaker_title = Column(String(255), nullable=True)
    context = Column(Text, nullable=True)
    significance_score = Column(Float, nullable=False)
    quote_type = Column(String(50), nullable=False)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    relationships = relationship("QuoteRelationship", back_populates="quote", cascade="all, delete-orphan")
    deal = relationship("Deal", back_populates="quotes")
    document = relationship("Document", back_populates="quotes")

    def __repr__(self):
        return f"<DocumentQuote(id='{self.id}', quote_type='{self.quote_type}', significance_score={self.significance_score})>"

    def to_dict(self):
        """
        Convert the quote to a dictionary representation.
        """
        return {
            'id': self.id,
            'deal_id': self.deal_id,
            'document_id': self.document_id,
            'quote_text': self.quote_text,
            'speaker': self.speaker,
            'speaker_title': self.speaker_title,
            'context': self.context,
            'significance_score': self.significance_score,
            'quote_type': self.quote_type,
            'metadata': self.metadata,
            'relationships': [rel.to_dict() for rel in self.relationships],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class QuoteRelationship(Base):
    """
    Model representing a relationship between a quote and a metric.
    """
    __tablename__ = 'quote_relationships'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_id = Column(String(36), ForeignKey('document_quotes.id', ondelete='CASCADE'), nullable=False)
    related_metric = Column(String(255), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("DocumentQuote", back_populates="relationships")

    def __repr__(self):
        return f"<QuoteRelationship(id='{self.id}', relationship_type='{self.relationship_type}', confidence_score={self.confidence_score})>"

    def to_dict(self):
        """
        Convert the relationship to a dictionary representation.
        """
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'related_metric': self.related_metric,
            'relationship_type': self.relationship_type,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 