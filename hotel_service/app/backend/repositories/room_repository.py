from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from ..models.Room import Room, PhysicalRoom

def add_room(
    db: Session, 
    price: float, 
    description: str, 
    type: str, 
    guest_capacity: int, 
    facilities: List[str],
    room_numbers: List[str]
) -> Room:
    new_room_model = Room(
        price=price,
        description=description,
        type=type,
        guest_capacity=guest_capacity,
        facilities=facilities
    )
    db.add(new_room_model)
    db.commit()
    db.refresh(new_room_model)

    created_physical_rooms = []
    for number in room_numbers:
        new_physical_room = PhysicalRoom(
            room_model_id=new_room_model.id,
            room_number=number,
            is_booked=False
        )
        created_physical_rooms.append(new_physical_room)
    
    db.add_all(created_physical_rooms)
    db.commit()
    db.refresh(new_room_model)
    return new_room_model

def get_room_by_id(db: Session, room_id: int) -> Optional[Room]:
    return db.query(Room).options(
        joinedload(Room.physical_rooms)
    ).filter(Room.id == room_id).first()

def get_all_facilities(db: Session) -> List[str]:
    """Повертає список всіх унікальних зручностей, що існують в базі даних."""
    # Ця реалізація розгортає масив JSON і знаходить унікальні значення.
    # Вона специфічна для PostgreSQL.
    all_facilities = db.query(func.json_array_elements_text(Room.facilities)).distinct().all()
    return [facility for facility, in all_facilities]

def get_filtered_rooms(
    db: Session,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_guests: Optional[int] = None,
    facilities: Optional[List[str]] = None
) -> List[Room]:
    """
    Повертає список моделей номерів з урахуванням фільтрів.
    Ефективно завантажує пов'язані фізичні номери.
    """
    query = db.query(Room).options(joinedload(Room.physical_rooms))
    
    if min_price is not None:
        query = query.filter(Room.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Room.price <= max_price)
        
    if min_guests is not None:
        query = query.filter(Room.guest_capacity >= min_guests)
    
    if facilities:
        # Для PostgreSQL використовується оператор `contains` (`@>`).
        # Він перевіряє, чи JSON-масив `facilities` в базі даних містить всі 
        # елементи зі списку, переданого в запиті.
        query = query.filter(Room.facilities.contains(facilities))
        
    return query.all()

def update_room(db: Session, room_id: int, update_data: Dict[str, Any]) -> Optional[Room]:
    room = db.query(Room).filter(Room.id == room_id).first()
    if room:
        for key, value in update_data.items():
            if hasattr(room, key):
                setattr(room, key, value)
        db.commit()
        db.refresh(room)
    return room

def delete_room_by_id(db: Session, room_id: int) -> int:
    deleted_count = db.query(Room).filter(Room.id == room_id).delete(synchronize_session=False)
    db.commit()
    return deleted_count

def get_rooms_by_ids(db: Session, room_ids: List[int]) -> List[Room]:
    if not room_ids:
        return []
    return db.query(Room).filter(Room.id.in_(room_ids)).all()