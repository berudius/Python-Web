from sqlalchemy import Column, Integer, Double, String, JSON
from sqlalchemy.orm import relationship
from common.db.database import Base
from ..models.assosiations import booking_room_association


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    price = Column(Double, nullable=False)
    description = Column (String(400), nullable=False)
    type = Column(String(50), nullable=False)
    guest_capacity = Column(Integer, nullable=False)
    facilities = Column(JSON, nullable=True, default=[])

    images =  relationship("RoomImage", back_populates="room", cascade="all, delete-orphan")

    bookings = relationship("Booking", secondary=booking_room_association, back_populates="rooms")
