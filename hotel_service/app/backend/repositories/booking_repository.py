from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date
from ..models.Booking import Booking # Ваша модель Booking
from ..models.Room import Room # Потрібна для зв'язування

def add_booking(
    db: Session, 
    user_id: int, 
    room_ids: List[int], 
    arrival_date: date, 
    departure_date: date
) -> Booking:

    rooms_to_book = db.query(Room).filter(Room.id.in_(room_ids)).all()

    new_booking = Booking(
        user_id=user_id,
        arrival_date=arrival_date,
        departure_date=departure_date,
        rooms=rooms_to_book # SQLAlchemy автоматично обробляє M2M зв'язок
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(Booking.id == booking_id).first()

def get_all_bookings(db: Session) -> List[Booking]:
    return db.query(Booking).all()

def update_booking(
    db: Session, 
    booking_id: int, 
    update_data: Dict[str, Any]
) -> Optional[Booking]:
    """
    Повністю оновлює бронювання.
    
    Може оновлювати прості поля (наприклад, 'arrival_date')
    та M2M зв'язок 'rooms'.
    
    Для оновлення кімнат 'update_data' має містити ключ 'room_ids'
    зі списком ID нових кімнат.
    """
    
    # 1. Знаходимо наше бронювання
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        return None

    # 2. Обробка M2M (Кімнати)
    # .pop() витягує ключ 'room_ids' зі словника і видаляє його.
    # Якщо ключа немає, повертається None.
    room_ids = update_data.pop('room_ids', None)

    # `is not None` дозволяє передати порожній список [], 
    # щоб видалити всі кімнати з бронювання.
    if room_ids is not None:
        # Знаходимо об'єкти кімнат, які відповідають наданим ID
        rooms_to_book = db.query(Room).filter(Room.id.in_(room_ids)).all()
        
        # Призначення нового списку кімнат.
        # SQLAlchemy автоматично оновить асоціативну таблицю.
        booking.rooms = rooms_to_book

    # 3. Обробка простих полів
    # (Після .pop() у 'update_data' залишилися лише прості поля)
    for key, value in update_data.items():
        if hasattr(booking, key):
            setattr(booking, key, value)
            
    # 4. Збереження змін
    db.commit()
    db.refresh(booking)
        
    return booking

def delete_booking_by_id(db: Session, booking_id: int) -> int:
    db.query(Booking).filter(Booking.id == booking_id).delete(synchronize_session=False)
    db.commit()