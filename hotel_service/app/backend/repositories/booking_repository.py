from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date
from ..models.Booking import Booking # Ваша модель Booking
from ..models.Room import Room # Потрібна для зв'язування

def add_booking(
    db: Session, 
    phone_number: str,       # phone_number тепер обов'язковий
    room_ids: List[int], 
    arrival_date: date, 
    departure_date: date,
    status: str,
    user_id: Optional[int]   # user_id тепер опціональний
) -> Booking:

    rooms_to_book = db.query(Room).filter(Room.id.in_(room_ids)).all()

    new_booking = Booking(
        user_id=user_id,
        phone_number=phone_number, # Додано
        arrival_date=arrival_date,
        departure_date=departure_date,
        rooms=rooms_to_book,
        status = status
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(Booking.id == booking_id).first()

# --- НОВИЙ МЕТОД ---
def get_bookings_by_user_id(db: Session, user_id: int) -> List[Booking]:
    """Отримує всі бронювання для конкретного ID користувача."""
    return db.query(Booking).filter(Booking.user_id == user_id).order_by(Booking.arrival_date.desc()).all()

# --- НОВИЙ МЕТОД ---
def get_bookings_by_phone(db: Session, phone_number: str) -> List[Booking]:
    """Отримує всі бронювання за номером телефону (для гостей)."""
    return db.query(Booking).filter(Booking.phone_number == phone_number).order_by(Booking.arrival_date.desc()).all()

def get_all_bookings(db: Session) -> List[Booking]:
    """Отримує абсолютно всі бронювання (для адмінів)."""
    return db.query(Booking).order_by(Booking.arrival_date.desc()).all()

def update_booking(
    db: Session, 
    booking_id: int, 
    update_data: Dict[str, Any]
) -> Optional[Booking]:
    """
    Оновлює бронювання.
    Підтримує оновлення:
    - phone_number
    - user_id
    - status
    - arrival_date
    - departure_date
    - room_ids (оновлює пов'язану Many-to-Many таблицю)
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        return None

    # Оновлення кімнат, якщо передано
    room_ids = update_data.pop('room_ids', None)
    if room_ids is not None:
        rooms_to_book = db.query(Room).filter(Room.id.in_(room_ids)).all()
        booking.rooms = rooms_to_book

    # Оновлення інших полів (status, phone_number, user_id, arrival_date, departure_date)
    for key, value in update_data.items():
        if hasattr(booking, key):
            setattr(booking, key, value)
            
    db.commit()
    db.refresh(booking)
        
    return booking
def delete_booking_by_id(db: Session, booking_id: int):
    # По-перше, знайдемо бронювання, щоб розірвати зв'язки M2M
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        # Це очистить зв'язки в асоціативній таблиці
        booking.rooms = [] 
        db.commit()
        
        # Тепер видаляємо саме бронювання
        db.query(Booking).filter(Booking.id == booking_id).delete(synchronize_session=False)
        db.commit()
        return True
    return False

def update_booking_status(db: Session, booking_id: int, new_status: str) -> Optional[Booking]:
    # 1. Знаходимо бронювання в базі даних
    booking_to_update = db.query(Booking).filter(Booking.id == booking_id).first()

    # 2. Якщо бронювання знайдене, оновлюємо його
    if booking_to_update:
        booking_to_update.status = new_status
        db.commit()
        db.refresh(booking_to_update)
        return booking_to_update
    
    # 3. Якщо бронювання не знайдено, повертаємо None
    return None

def count_bookings_by_status(db: Session, user_id: int, status: str) -> int:
    """
    Підраховує кількість бронювань для конкретного користувача
    з певним статусом.
    """
    return db.query(Booking).filter(
        Booking.user_id == user_id,
        Booking.status == status
    ).count()