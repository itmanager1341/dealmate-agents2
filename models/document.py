# Relationships
deal = relationship("Deal", back_populates="documents")
quotes = relationship("DocumentQuote", back_populates="document", cascade="all, delete-orphan")
charts = relationship("ChartElement", back_populates="document", cascade="all, delete-orphan") 