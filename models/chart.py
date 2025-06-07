from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base
import uuid

class ChartElement(Base):
    """
    Model representing a chart, graph, or table extracted from a document.
    """
    __tablename__ = 'chart_elements'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    document_id = Column(String(36), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chart_type = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    data_points = Column(JSONB, nullable=True)
    source_page = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=False)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    relationships = relationship("ChartRelationship", back_populates="chart", cascade="all, delete-orphan")
    deal = relationship("Deal", back_populates="charts")
    document = relationship("Document", back_populates="charts")

    def __repr__(self):
        return f"<ChartElement(id='{self.id}', chart_type='{self.chart_type}', confidence_score={self.confidence_score})>"

    def to_dict(self):
        """
        Convert the chart to a dictionary representation.
        """
        return {
            'id': self.id,
            'deal_id': self.deal_id,
            'document_id': self.document_id,
            'chart_type': self.chart_type,
            'title': self.title,
            'description': self.description,
            'data_points': self.data_points,
            'source_page': self.source_page,
            'confidence_score': self.confidence_score,
            'metadata': self.metadata,
            'relationships': [rel.to_dict() for rel in self.relationships],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ChartRelationship(Base):
    """
    Model representing a relationship between a chart and related text.
    """
    __tablename__ = 'chart_relationships'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chart_id = Column(String(36), ForeignKey('chart_elements.id', ondelete='CASCADE'), nullable=False)
    related_text = Column(Text, nullable=False)
    relationship_type = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    chart = relationship("ChartElement", back_populates="relationships")

    def __repr__(self):
        return f"<ChartRelationship(id='{self.id}', relationship_type='{self.relationship_type}', confidence_score={self.confidence_score})>"

    def to_dict(self):
        """
        Convert the relationship to a dictionary representation.
        """
        return {
            'id': self.id,
            'chart_id': self.chart_id,
            'related_text': self.related_text,
            'relationship_type': self.relationship_type,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 