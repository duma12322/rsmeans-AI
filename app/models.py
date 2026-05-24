from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db import Base


class Division(Base):
    __tablename__ = "divisions"

    id = Column(Integer, primary_key=True, index=True)
    division_number = Column(Integer)
    division_name = Column(String)


class RSMeansItem(Base):
    __tablename__ = "rsmeans_items"

    id = Column(Integer, primary_key=True, index=True)
    division_id = Column(Integer, ForeignKey("divisions.id"))
    item_code = Column(String)
    title = Column(String)
    description = Column(Text)