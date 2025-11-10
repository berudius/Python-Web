from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, Query
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
    db: Session = Depends(get_db),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_guests: Optional[int] = Query(None),
    facilities: Optional[List[str]] = Query(None),
    partial: bool = Query(False)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        is_admin = session and session.get("user_role") == "admin"

        filtered_room_types = room_repository.get_filtered_rooms(
            db, min_price, max_price, min_guests, facilities
        )
        
        room_contexts = []
        for room_type in filtered_room_types:
            physical_rooms = room_type.physical_rooms
            total_count = len(physical_rooms)
            available_count = sum(1 for pr in physical_rooms if not pr.is_booked)
            
            if not is_admin and available_count == 0:
                continue

            room_dict = {
                "id": room_type.id,
                "price": room_type.price,
                "description": room_type.description,
                "type": room_type.type,
                "guest_capacity": room_type.guest_capacity,
                "facilities": room_type.facilities
            }
            
            image_urls = room_image_repository.get_images_urls_of_room(db, room_type.id)
            
            room_contexts.append({
                "data": room_type,      
                "json": room_dict,     
                "images": image_urls,  
                "physical_rooms": physical_rooms,
                "total_count": total_count,
                "available_count": available_count
            })

        context = {
            "request": request,
            "room_contexts": room_contexts,
            "is_authorized": session and session.get("user_id") is not None,
            "is_admin": is_admin,
            "USER_SERVICE_URL": USER_SERVICE_URL,
            "min_price": min_price,
            "max_price": max_price,
            "min_guests": min_guests,
            "selected_facilities": facilities or []
        }

        if partial:
            return templates.TemplateResponse("_room_list_partial.html", context)
        
        all_facilities = room_repository.get_all_facilities(db)
        context["all_facilities"] = all_facilities
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
    room_numbers_str: str = Form(..., alias="room_numbers")
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)

        if session and session.get("user_role") == "admin":
            room_numbers = [num.strip() for num in room_numbers_str.split(',') if num.strip()]
            if not room_numbers:
                 raise HTTPException(
                     status_code=status.HTTP_400_BAD_REQUEST, 
                     detail="Ви повинні вказати хоча б один номер кімнати."
                 )

            added_room = room_repository.add_room(
                db, price, description, type, 
                guest_capacity, facilities, room_numbers
            )
            
            image_urls = image_storage_repository.save_images(images)
            room_image_repository.add_images_to_room(db, added_room.id, image_urls)
        
        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )

@router.post("/rooms/edit/{room_id}")
async def edit_room(
    request: Request,
    room_id: int,
    db: Session = Depends(get_db),
    price: float = Form(...),
    description: str= Form(...),
    type: str= Form(...),
    guest_capacity: int= Form(...),
    facilities: Optional[List[str]] = Form(None)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        if not session or session.get("user_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Доступ заборонено"
            )
        
        facilities_list = facilities or []
        
        update_data: Dict[str, Any] = {
            "price": price,
            "description": description,
            "type": type,
            "guest_capacity": guest_capacity,
            "facilities": facilities_list
        }
        
        room_repository.update_room(db, room_id, update_data)
        
        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Помилка при оновленні: {str(e)}"
        )

@router.post("/rooms/delete/{room_id}")
async def delete_room(
    request: Request,
    room_id: int,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        if not session or session.get("user_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Доступ заборонено"
            )
        
        image_urls = room_image_repository.get_images_urls_of_room(db, room_id)
        room_image_repository.delete_images_by_room_id(db, room_id)
        
        for url in image_urls:
            image_storage_repository.remove_image(url)
            
        room_repository.delete_room_by_id(db, room_id)

        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Помилка при видаленні: {str(e)}"
        )

