# from sqlalchemy import Column, Integer, String, Float
# from database import Base

# class Detection(Base):
#     __tablename__ = "detections"

#     id = Column(Integer, primary_key=True, index=True)
#     timestamp = Column(String, index=True)
#     sexual_score = Column(Float)
#     violent_score = Column(Float)
#     categories = Column(String)
# models.py - SQLAlchemy model for Detection
from sqlalchemy import Column, Integer, String, Float
from database import Base
import json

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    sexual_score = Column(Float)
    violent_score = Column(Float)
    categories = Column(String)  # JSON string