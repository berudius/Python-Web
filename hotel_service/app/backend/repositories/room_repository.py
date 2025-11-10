from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from ..models.Room import Room, PhysicalRoom

def add_room(
    db: Session, 
    price: float, 
    description: str, 
    type: str, 
    guest_capacity: int, 
    facilities: List[str],
    room_numbers: List[str]  # <-- ДОДАНО: список номерів (напр., ["101", "102"])
) -> Room:
    
    # 1. Створюємо "модель номеру"
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

    
    # 2. Створюємо "Фізичні номери" і прив'язуємо їх
    created_physical_rooms = []
    for number in room_numbers:
        new_physical_room = PhysicalRoom(
            room_model_id=new_room_model.id,
            room_number=number,
            is_booked=False # За замовчуванням вільні
        )
        created_physical_rooms.append(new_physical_room)
    

    db.add_all(created_physical_rooms)
    db.commit()
    
    db.refresh(new_room_model) # Оновлюємо, щоб отримати зв'язок
    return new_room_model

def get_room_by_id(db: Session, room_id: int) -> Optional[Room]:
    # Оновлюємо, щоб одразу завантажити інвентар
    return db.query(Room).options(
        joinedload(Room.physical_rooms)
    ).filter(Room.id == room_id).first()

def get_all_rooms(db: Session) -> List[Room]:
    # ---- ВИПРАВЛЕНО ----
    # 1. Забираємо дубльований запит
    # 2. Додаємо joinedload, щоб уникнути N+1 проблеми
    #    (це завантажує всі physical_rooms одним JOIN-запитом)
    rooms = db.query(Room).options(
        joinedload(Room.physical_rooms) 
    ).all()
    
    print(f"КІЛЬКІСТЬ ТИПІВ КІМНАТ З БД: {len(rooms)}")
    return rooms # <-- ВИПРАВЛЕНО: повертаємо 'rooms'

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


