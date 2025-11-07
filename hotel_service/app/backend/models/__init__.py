# Важливо спочатку імпортувати Base
from common.db.database import Base
from .Room import Room
from .Booking import Booking, booking_room_association
from .RoomImage import RoomImage
