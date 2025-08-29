# models.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from TEST.database import Base

class Tracking(Base):
    __tablename__ = "trackings"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(255), index=True, nullable=False)
    courier_code = Column(String(100), index=True, nullable=False)
    status = Column(String(100), nullable=True)
    last_event = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Tracking(id={self.id}, tracking_number='{self.tracking_number}', courier='{self.courier_code}', status='{self.status}')>"