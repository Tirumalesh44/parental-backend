from sqlalchemy import Column, Integer, String, Float
from database import Base

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, nullable=False)
    sexual_score = Column(Float, nullable=False)
    violent_score = Column(Float, nullable=False)
    categories = Column(String, nullable=False)
