from fastapi import APIRouter, Request, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi_redis_session import getSession
from httpx import AsyncClient
from datetime import date
from urllib.parse import urlencode

from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from common.db.database import get_db
from common.config.services_paths import USER_SERVICE_URL, HOTEL_SERVICE_URL
from ..repositories import booking_repository

from typing import List, Optional
from pydantic import BaseModel

_TRUST_LEVEL_FOR_AUTO_CONFIRMATION = 2

router = APIRouter()

class CreateBookingPayload(BaseModel):
    room_ids: List[int]
    arrival_date: date
    departure_date: date
    phone_number: str
    save_phone: Optional[bool] = False
    book_without_confirmation: Optional[bool] = False

class UpdateBookingStatusPayload(BaseModel):
    status: str

async def get_user_data_from_service(user_id: int) -> Optional[dict]:
    try:
        async with AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return None

async def update_user_data_in_service(user_id: int, updates: dict) -> bool:
    try:
        async with AsyncClient() as client:
            response = await client.patch(f"{USER_SERVICE_URL}/users/{user_id}", json=updates)
            response.raise_for_status()
            return True
    except Exception as e:
        return False

def generate_auth_urls(base_url: str, redirect_path: str, booking_ids: List[int]) -> dict:
    params = {"redirect_url": redirect_path}
    if booking_ids:
        params["guest_bookings"] = ",".join(map(str, booking_ids))
    encoded_params = urlencode(params)
    return {
        "login_url": f"{base_url}/login?{encoded_params}",
        "register_url": f"{base_url}/registration?{encoded_params}"
    }


@router.post("/bookings/cancel/{booking_id}")
async def cancel_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db)
):
    session = getSession(request=request, sessionStorage=session_storage)
    user_id = session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Для скасування бронювання потрібно увійти в акаунт.")

    booking = booking_repository.get_booking_by_id(db, booking_id)

    if not booking or booking.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронювання не знайдено або у вас немає прав на його скасування.")

    if booking.status not in ["Розглядається", "Підтверджено"]:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Неможливо скасувати бронювання зі статусом '{booking.status}'.")

    user_data = await get_user_data_from_service(user_id)
    if not user_data:
        session.set("booking_error", "Не вдалося отримати дані користувача. Спробуйте пізніше.")
        return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

    trust_level = user_data.get("trust_level", 0)
    if trust_level == 0:
        session.set("booking_error", "Ваш рівень довіри не дозволяє скасовувати бронювання онлайн. Будь ласка, зв'яжіться з нами.")
        return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

    consecutive_cancellations = user_data.get("consecutive_cancellations", 0)
    new_trust_level = trust_level
    new_consecutive_cancellations = consecutive_cancellations + 1
    update_payload = {"consecutive_cancellations": new_consecutive_cancellations}

    if trust_level == 1:
        new_trust_level = 0
        update_payload["trust_level"] = new_trust_level
        update_payload["consecutive_cancellations"] = 0
    elif trust_level == 2 and new_consecutive_cancellations >= 2:
        new_trust_level = 1
        update_payload["trust_level"] = new_trust_level
        update_payload["consecutive_cancellations"] = 0
    elif trust_level == 3 and new_consecutive_cancellations >= 3:
        new_trust_level = 1
        update_payload["trust_level"] = new_trust_level
        update_payload["consecutive_cancellations"] = 0

    update_success = await update_user_data_in_service(user_id, update_payload)
    if not update_success:
        session.set("booking_error", "Не вдалося оновити ваш рівень довіри. Спробуйте скасувати бронювання пізніше.")
        return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

    booking_repository.update_booking_status(db, booking_id, "Скасовано")
    
    message = "Бронювання успішно скасовано."
    if new_trust_level < trust_level:
        message += f" Увага, ваш рівень довіри було знижено до {new_trust_level}."
    session.set("booking_success", message)

    return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

@router.patch("/admin/bookings/{booking_id}/status")
async def update_booking_status_by_admin(
    booking_id: int,
    payload: UpdateBookingStatusPayload,
    db: Session = Depends(get_db)
):
    booking_to_update = booking_repository.get_booking_by_id(db, booking_id)
    if not booking_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронювання не знайдено.")

    booking_repository.update_booking_status(db, booking_id, payload.status)
    user_id = booking_to_update.user_id
    if not user_id:
        return JSONResponse(content={"success": True, "message": "Статус гостьового бронювання оновлено."})

    if payload.status == "Завершено":
        user_data = await get_user_data_from_service(user_id)
        if not user_data:
            return JSONResponse(status_code=503, content={"success": False, "message": "Статус оновлено, але не вдалося оновити рівень довіри."})

        completed_count = booking_repository.count_bookings_by_status(db, user_id, "Завершено")
        current_trust_level = user_data.get("trust_level", 0)
        new_trust_level = current_trust_level

        if completed_count >= 10: new_trust_level = 3
        elif completed_count >= 5: new_trust_level = 2
        elif completed_count >= 2: new_trust_level = 1
        
        update_payload = {}
        if new_trust_level > current_trust_level:
            update_payload["trust_level"] = new_trust_level

        if completed_count > 0 and completed_count % 2 == 0:
            if user_data.get("consecutive_cancellations", 0) > 0:
                 update_payload["consecutive_cancellations"] = 0

        if update_payload:
            await update_user_data_in_service(user_id, update_payload)

    return JSONResponse(content={"success": True, "message": f"Статус бронювання оновлено. Рівень довіри користувача перевірено."})

@router.get("/my-bookings")
async def get_my_bookings_page(
    request: Request,
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None),
    phone_filter: Optional[str] = Query(None)
):
    session = getSession(request=request, sessionStorage=session_storage)
    user_id = session.get("user_id")
    is_authorized = bool(user_id)
    is_admin = session.get("is_admin", False)
    
    guest_booking_ids = session.get("guest_booking_ids", [])
    sync_redirect_url = f"{HOTEL_SERVICE_URL}/auth/sync"
    auth_urls = generate_auth_urls(USER_SERVICE_URL, sync_redirect_url, guest_booking_ids)
    
    bookings = []
    trust_level = 0

    if is_admin:
        bookings = booking_repository.get_all_bookings_with_filters(db, status_filter, phone_filter)
    elif is_authorized:
        bookings = booking_repository.get_bookings_by_user_id(db, user_id)
        user_data = await get_user_data_from_service(user_id)
        if user_data:
            trust_level = user_data.get("trust_level", 0)

    context = {
        "request": request,
        "my_bookings": bookings,
        "is_authorized": is_authorized,
        "is_admin": is_admin,
        "trust_level": trust_level,
        "status_filter": status_filter,
        "phone_filter": phone_filter,
        "success_message": session.pop("booking_success", None),
        "booking_error": session.pop("booking_error", None),
        "login_url": auth_urls["login_url"],
        "register_url": auth_urls["register_url"],
        "USER_SERVICE_URL": USER_SERVICE_URL
    }
    return templates.TemplateResponse("my-bookings.html", context)

@router.get("/auth/sync")
async def sync_guest_bookings(
    request: Request,
    guest_bookings: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    session = getSession(request=request, sessionStorage=session_storage)
    user_id = session.get("user_id")

    if not user_id:
        return RedirectResponse(url=f"{USER_SERVICE_URL}/login")

    if guest_bookings:
        try:
            booking_ids_to_sync = [int(id_str) for id_str in guest_bookings.split(',')]
            updated_count = booking_repository.associate_bookings_to_user_by_ids(db, booking_ids_to_sync, user_id)
            if updated_count > 0:
                session.set("booking_success", f"Ваші гостьові бронювання (кількість: {updated_count}) було успішно прив\'язано до акаунту.")
        except (ValueError, TypeError):
            pass

    session.pop("guest_booking_ids", None)
    return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/bookings/create_json")
async def create_booking_json(request: Request, payload: CreateBookingPayload, db: Session = Depends(get_db)):
    session = getSession(request=request, sessionStorage=session_storage)
    user_id = session.get("user_id")

    if not booking_repository.are_rooms_available(db, payload.room_ids, payload.arrival_date, payload.departure_date):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"success": False, "message": "На жаль, один або декілька з вибраних номерів вже зайняті на ці дати."}
        )

    booking_status = "Розглядається"
    if user_id:
        user_data = await get_user_data_from_service(user_id)
        if user_data:
            trust_level = user_data.get("trust_level", 0)
            if trust_level >= _TRUST_LEVEL_FOR_AUTO_CONFIRMATION:
                booking_status = "Підтверджено"

    new_booking = booking_repository.add_booking(
        db=db, 
        phone_number=payload.phone_number,
        room_ids=payload.room_ids, 
        arrival_date=payload.arrival_date, 
        departure_date=payload.departure_date,
        status=booking_status,
        user_id=user_id
    )

    if not user_id and session:
        guest_bookings = session.get("guest_booking_ids", [])
        if new_booking.id not in guest_bookings:
            guest_bookings.append(new_booking.id)
        session.set("guest_booking_ids", guest_bookings)
        session.set("phone_number", payload.phone_number)

    message = "Бронювання успішно створено! Очікуйте на підтвердження."
    if booking_status == "Підтверджено":
        message = "Ваше бронювання було автоматично підтверджено завдяки високому рівню довіри!"

    return JSONResponse(content={"success": True, "message": message})

@router.get("/bookings")
async def get_booking_confirmation_page(
    request: Request,
    db: Session = Depends(get_db),
    room_ids: Optional[List[int]] = Query(None),
    arrival_date: Optional[date] = Query(None),
    departure_date: Optional[date] = Query(None)
):
    session = getSession(request=request, sessionStorage=session_storage)

    if not all([room_ids, arrival_date, departure_date]):
        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)
    
    if not booking_repository.are_rooms_available(db, room_ids, arrival_date, departure_date):
        session.set("booking_error", "На жаль, один або декілька з вибраних номерів вже зайняті. Будь ласка, виберіть інші номери або дати.")
        return RedirectResponse(url="/rooms", status_code=status.HTTP_303_SEE_OTHER)

    selected_rooms = booking_repository.get_rooms_by_ids(db, room_ids)
    total_price = sum(room.price for room in selected_rooms)

    user_id = session.get("user_id")
    guest_booking_ids = session.get("guest_booking_ids", [])
    last_guest_phone = session.get("phone_number", "")
    is_authorized = bool(user_id)
    user_phone = ""
    trust_level = 0

    sync_redirect_url = f"{HOTEL_SERVICE_URL}/auth/sync"
    auth_urls = generate_auth_urls(USER_SERVICE_URL, sync_redirect_url, guest_booking_ids)

    if is_authorized:
        user_data = await get_user_data_from_service(user_id)
        if user_data:
            user_phone = user_data.get("phone_number", "")
            trust_level = user_data.get("trust_level", 0)

    context = {
        "request": request,
        "selected_rooms": selected_rooms,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "total_price": total_price,
        "is_authorized": is_authorized,
        "phone_number": user_phone or last_guest_phone,
        "trust_level": trust_level,
        "login_url": auth_urls["login_url"],
        "register_url": auth_urls["register_url"],
        "USER_SERVICE_URL": USER_SERVICE_URL
    }
    return templates.TemplateResponse("booking.html", context)