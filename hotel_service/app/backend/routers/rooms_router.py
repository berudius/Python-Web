from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException

from common.config.redis_session_config import session_storage
from fastapi_redis_session import getSession

from sqlalchemy.orm import Session
from common.db.database import get_db

from ..config.jinja_template_config import templates
from ..repositories import room_repository, room_image_repository, image_storage_repository 
from common.config.services_paths import USER_SERVICE_URL
from typing import List, Any, Dict, Optional

router = APIRouter()

@router.get("/rooms")
async def get_rooms(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        is_admin = session and session.get("user_role") == "admin"
        # 1. Отримуємо всі "Типи номерів" разом з їх "Фізичними номерами"
        # (Завдяки joinedload в get_all_rooms, це ефективно)
        all_room_types = room_repository.get_all_rooms(db)
        
        room_contexts = []
        for room_type in all_room_types:
            
            # 2. Розраховуємо доступність
            physical_rooms = room_type.physical_rooms
            total_count = len(physical_rooms)
            available_count = sum(1 for pr in physical_rooms if not pr.is_booked)
            
            # 3. ЛОГІКА ФІЛЬТРАЦІЇ:
            # Якщо це не адмін і вільних номерів 0, не показуємо цей тип
            if not is_admin and available_count == 0:
                continue

            # 4. Готуємо дані (як і раніше)
            room_dict = {
                "id": room_type.id,
                "price": room_type.price,
                "description": room_type.description,
                "type": room_type.type,
                "guest_capacity": room_type.guest_capacity,
                "facilities": room_type.facilities
            }
            
            image_urls = room_image_repository.get_images_urls_of_room(db, room_type.id)
            
            # 5. Додаємо НОВІ ДАНІ в контекст
            room_contexts.append({
                "data": room_type,      
                "json": room_dict,     
                "images": image_urls,  
                "physical_rooms": physical_rooms, # <-- НОВЕ: для "карти" адміна
                "total_count": total_count,       # <-- НОВЕ: (напр. 5)
                "available_count": available_count  # <-- НОВЕ: (напр. 2)
            })

        # 6. Готуємо загальний контекст
        context = {
            "request": request,
            "room_contexts": room_contexts 
        }

        # 7. Додаємо дані сесії (як і раніше)
        if session and session.get("user_id"):
            context["is_authorized"] = True
            context["is_admin"] = is_admin
        else:
            context["is_authorized"] = False
            context["is_admin"] = False
            context["USER_SERVICE_URL"] = USER_SERVICE_URL
        
        return templates.TemplateResponse("rooms.html", context)
    
    except Exception as e:
        import logging
        logging.error(f"ПОМИЛКА в get_rooms: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )
    

@router.post("/rooms")
async def create_room(
    request: Request,
    db: Session = Depends(get_db),
    price: float = Form(...),
    description: str= Form(...),
    type: str= Form(...),
    guest_capacity: int= Form(...),
    facilities: List[str]= Form(...),
    images: List[UploadFile] = Form(...),
    room_numbers_str: str = Form(..., alias="room_numbers") # <-- НОВЕ ПОЛЕ
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)

        if session and session.get("user_role") == "admin":
            # Парсимо рядок з номерами
            room_numbers = [num.strip() for num in room_numbers_str.split(',') if num.strip()]
            if not room_numbers:
                 raise HTTPException(
                     status_code=status.HTTP_400_BAD_REQUEST, 
                     detail="Ви повинні вказати хоча б один номер кімнати."
                 )

            added_room = room_repository.add_room(
                db, price, description, type, 
                guest_capacity, facilities, room_numbers # <-- Передаємо список
            )
            
            image_urls = image_storage_repository.save_images(images)
            room_image_repository.add_images_to_room(db, added_room.id, image_urls)
        
        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )

# 2. НОВИЙ ЕНДПОІНТ: для редагування кімнати
@router.post("/rooms/edit/{room_id}")
async def edit_room(
    request: Request,
    room_id: int,
    db: Session = Depends(get_db),
    price: float = Form(...),
    description: str= Form(...),
    type: str= Form(...),
    guest_capacity: int= Form(...),
    # "facilities" може прийти як пустий список, тому робимо його Optional
    facilities: Optional[List[str]] = Form(None) 
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        # Перевірка, чи це адмін
        if not session or session.get("user_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Доступ заборонено"
            )
        
        # "facilities" з форми приходить як None, якщо жодного не надіслано
        # Перетворюємо None на пустий список
        facilities_list = facilities or []
        
        # Готуємо словник з оновленими даними
        update_data: Dict[str, Any] = {
            "price": price,
            "description": description,
            "type": type,
            "guest_capacity": guest_capacity,
            "facilities": facilities_list
        }
        
        # Викликаємо репозиторій для оновлення
        room_repository.update_room(db, room_id, update_data)
        
        # Повертаємо користувача назад на сторінку
        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Помилка при оновленні: {str(e)}"
        )

# 3. НОВИЙ ЕНДПОІНТ: для видалення кімнати
@router.post("/rooms/delete/{room_id}")
async def delete_room(
    request: Request,
    room_id: int,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        # Перевірка, чи це адмін
        if not session or session.get("user_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Доступ заборонено"
            )
        
        # Повна логіка видалення:
        
        # 1. Отримуємо URL всіх зображень, які треба видалити з диска
        image_urls = room_image_repository.get_images_urls_of_room(db, room_id)
        
        # 2. Видаляємо записи про зображення з БД (з таблиці room_images)
        room_image_repository.delete_images_by_room_id(db, room_id)
        
        # 3. Фізично видаляємо файли зображень з диска
        for url in image_urls:
            image_storage_repository.remove_image(url)
            
        # 4. Видаляємо саму кімнату з БД (з таблиці rooms)
        room_repository.delete_room_by_id(db, room_id)

        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Помилка при видаленні: {str(e)}"
        )

