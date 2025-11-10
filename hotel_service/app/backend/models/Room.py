from sqlalchemy import Column, Integer, Double, String, JSON, ForeignKey, Boolean
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

    physical_rooms = relationship(
        "PhysicalRoom", 
        back_populates="room_model", 
        cascade="all, delete-orphan"
    )

    bookings = relationship("Booking", secondary=booking_room_association, back_populates="rooms")

class PhysicalRoom(Base):
    __tablename__ = "physical_rooms"
    id = Column(Integer, primary_key=True, index=True)
    
    room_model_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    room_number = Column(String(20), nullable=False, unique=True) 
    
    is_booked = Column(Boolean, nullable=False, default=False) 

    room_model = relationship("Room", back_populates="physical_rooms")
