from sqlalchemy import Column, Integer, Date, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from common.db.database import Base
from ..models.assosiations import booking_room_association
from datetime import datetime, timezone

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(DateTime, nullable=False, server_default=func.now())
    arrival_date = Column(DateTime, nullable=False)
    departure_date = Column(Date, nullable=False)

    user_id = Column(Integer, nullable=True)
    phone_number = Column((String(20)), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="Розглядається")

    rooms = relationship("Room", secondary=booking_room_association, back_populates="bookings")


