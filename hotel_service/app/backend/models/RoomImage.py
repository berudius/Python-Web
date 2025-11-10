from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from common.db.database import Base

class RoomImage(Base):
    __tablename__ = "room_images"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    url = Column(String(500), nullable=False, unique=True) 
    room = relationship("Room", back_populates="images")