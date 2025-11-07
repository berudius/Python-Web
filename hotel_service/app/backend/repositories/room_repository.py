from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..models.Room import Room

def add_room(
    db: Session, 
    price: float, 
    description: str, 
    type: str, 
    guest_capacity: int, 
    facilities: List[str]
) -> Room:
    new_room = Room(
        price=price,
        description=description,
        type=type,
        guest_capacity=guest_capacity,
        facilities=facilities
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

def get_room_by_id(db: Session, room_id: int) -> Optional[Room]:
    return db.query(Room).filter(Room.id == room_id).first()

def get_all_rooms(db: Session) -> List[Room]:
    return db.query(Room).all()

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
    db.query(Room).filter(Room.id == room_id).delete(synchronize_session=False)
    db.commit()


