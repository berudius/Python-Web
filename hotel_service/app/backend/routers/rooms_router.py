from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException

from common.config.redis_session_config import session_storage
from fastapi_redis_session import getSession

from sqlalchemy.orm import Session
from common.db.database import get_db

from ..config.jinja_template_config import templates
from ..repositories import room_repository, room_image_repository, image_storage_repository 
from typing import List

router = APIRouter()

@router.get("/rooms")
def get_rooms(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)

        rooms = room_repository.get_all_rooms(db)
        rooms_images_url_map = {}
        for room in rooms:
            room_images_urls = room_image_repository.get_images_urls_of_room(db, room.id)
            rooms_images_url_map[room.id] = room_images_urls
        
        if session and session.get("user_role") == "admin":
            return templates.TemplateResponse("rooms.html", {
                "request": request,
                "rooms":rooms,
                "rooms_images_url_map": rooms_images_url_map,
                "is_admin": True
            })

        return templates.TemplateResponse("rooms.html", {
            "request": request,
            "rooms":rooms,
            "rooms_images_url_map": rooms_images_url_map,
            "is_admin": False
        })
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    

@router.post("/rooms")
async def get_rooms(
    request: Request,
    db: Session = Depends(get_db),
    price: float = Form(...),
    description: str= Form(...),
    type: str= Form(...),
    guest_capacity: int= Form(...),
    facilities: List[str]= Form(...),
    images: List[UploadFile] = Form(...)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
    
        if session.get("user_role") == "admin":
            added_room = room_repository.add_room(db, price, description, type, guest_capacity, facilities)
            image_urls = image_storage_repository.save_images(images)
            room_image_repository.add_images_to_room(db, added_room.id, image_urls)
        
        return RedirectResponse(url="/rooms")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )

    

