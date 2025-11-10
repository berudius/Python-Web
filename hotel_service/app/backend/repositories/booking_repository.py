from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import date
from ..models.Booking import Booking
from ..models.Room import Room

def add_booking(
    db: Session, 
    phone_number: str,
    room_ids: List[int], 
    arrival_date: date, 
    departure_date: date,
    status: str,
    user_id: Optional[int]
) -> Booking:
    rooms_to_book = db.query(Room).filter(Room.id.in_(room_ids)).all()
    new_booking = Booking(
        user_id=user_id,
        phone_number=phone_number,
        arrival_date=arrival_date,
        departure_date=departure_date,
        rooms=rooms_to_book,
        status=status
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(Booking.id == booking_id).first()

def get_bookings_by_ids(db: Session, booking_ids: List[int]) -> List[Booking]:
    if not booking_ids:
        return []
    return db.query(Booking).filter(Booking.id.in_(booking_ids)).order_by(Booking.arrival_date.desc()).all()

def get_bookings_by_user_id(db: Session, user_id: int) -> List[Booking]:
    return db.query(Booking).filter(Booking.user_id == user_id).order_by(Booking.arrival_date.desc()).all()

def get_bookings_by_phone(db: Session, phone_number: str) -> List[Booking]:
    return db.query(Booking).filter(Booking.phone_number == phone_number).order_by(Booking.arrival_date.desc()).all()

def get_all_bookings(db: Session) -> List[Booking]:
    return db.query(Booking).order_by(Booking.arrival_date.desc()).all()

def update_booking(db: Session, booking_id: int, update_data: Dict[str, Any]) -> Optional[Booking]:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking: return None
    room_ids = update_data.pop('room_ids', None)
    if room_ids is not None:
        rooms_to_book = db.query(Room).filter(Room.id.in_(room_ids)).all()
        booking.rooms = rooms_to_book
    for key, value in update_data.items():
        if hasattr(booking, key): setattr(booking, key, value)
    db.commit()
    db.refresh(booking)
    return booking

def delete_booking_by_id(db: Session, booking_id: int):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.rooms = []
        db.commit()
        db.query(Booking).filter(Booking.id == booking_id).delete(synchronize_session=False)
        db.commit()
        return True
    return False

def update_booking_status(db: Session, booking_id: int, new_status: str) -> Optional[Booking]:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.status = new_status
        db.commit()
        db.refresh(booking)
    return booking

def count_bookings_by_status(db: Session, user_id: int, status: str) -> int:
    return db.query(Booking).filter(Booking.user_id == user_id, Booking.status == status).count()

def check_conflicting_bookings(db: Session, room_ids: List[int], arrival_date: date, departure_date: date) -> List[int]:
    conflicting_bookings = db.query(Booking).join(Booking.rooms).filter(
        and_(
            Room.id.in_(room_ids),
            Booking.status.in_(["Підтверджено", "Розглядається"]),
            Booking.arrival_date < departure_date,
            Booking.departure_date > arrival_date
        )
    ).all()
    conflicting_room_ids = {room.id for booking in conflicting_bookings for room in booking.rooms if room.id in room_ids}
    return list(conflicting_room_ids)

def associate_bookings_to_user_by_ids(db: Session, booking_ids: List[int], user_id: int) -> int:
    """
    Прив'язує список бронювань за їх ID до вказаного user_id.
    Повертає кількість оновлених бронювань.
    """
    if not booking_ids:
        return 0

    query = db.query(Booking).filter(
        Booking.id.in_(booking_ids),
        Booking.user_id.is_(None) # Оновлюємо тільки гостьові бронювання
    )
    
    updated_count = query.update({"user_id": user_id}, synchronize_session=False)
    db.commit()
    return updated_count
