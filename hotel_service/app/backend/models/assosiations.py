from sqlalchemy import Column, Integer, Table, ForeignKey
from common.db.database import Base

# Таблиця зв'язку Many-to-Many між Booking та Room
booking_room_association = Table(
    'booking_room_association',
    Base.metadata,
    Column('booking_id', Integer, ForeignKey('bookings.id'), primary_key=True),
    Column('room_id', Integer, ForeignKey('rooms.id'), primary_key=True)
)