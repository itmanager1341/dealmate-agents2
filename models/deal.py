# Relationships
documents = relationship("Document", back_populates="deal", cascade="all, delete-orphan")
quotes = relationship("DocumentQuote", back_populates="deal", cascade="all, delete-orphan")
charts = relationship("ChartElement", back_populates="deal", cascade="all, delete-orphan") 