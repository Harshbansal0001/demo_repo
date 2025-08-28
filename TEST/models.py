# models.py
from sqlalchemy import Column, Integer, String, JSON, Date, DateTime, func
from TEST.database import Base

class Tracking(Base):
    __tablename__ = "trackings"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String, index=True)
    courier_code = Column(String, index=True)
    date = Column(Date, nullable=True)        # <-- new field for your form date
    order_number = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    copy = Column(String,nullable=True)
    title = Column(String, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
