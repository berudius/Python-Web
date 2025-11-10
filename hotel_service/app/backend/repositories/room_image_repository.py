from sqlalchemy.orm import Session
from typing import List
from ..models.RoomImage import RoomImage

# Додає як одне фото, так і багато
def add_images_to_room(db: Session, room_id: int, image_urls: List[str]) -> List[RoomImage]:
    new_images = [
        RoomImage(room_id=room_id, url=url) for url in image_urls
    ]
    
    db.add_all(new_images)
    db.commit()
    
    return new_images

# Отримує всі зображення певної кімнати
def get_images_of_room(db: Session, room_id: int) -> List[RoomImage]:
    images = db.query(RoomImage).filter(RoomImage.room_id == room_id).all()
    return images
def get_images_urls_of_room(db: Session, room_id: int) -> List[str]:
    urls = [row.url for row in db.query(RoomImage).filter(RoomImage.room_id == room_id).all()]
    return urls

def delete_images_by_room_id(db: Session, room_id: int):
    db.query(RoomImage)\
      .filter(RoomImage.room_id == room_id)\
      .delete(synchronize_session=False)
    db.commit()

# Видаляє як одне фото, так і багато (через ID)
def delete_images_by_ids(db: Session, image_ids: List[int]):
    db.query(RoomImage)\
        .filter(RoomImage.id.in_(image_ids))\
        .delete(synchronize_session=False)
    db.commit()
