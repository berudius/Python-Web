from fastapi import APIRouter, Request, Depends, Form,  status
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi_redis_session import getSession
from httpx import AsyncClient, HTTPStatusError


from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from common.db.database import get_db
from common.config.services_paths import USER_SERVICE_URL

from ..repositories import booking_repository, room_repository

from datetime import date
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class RoomDetailsRequest(BaseModel):
    room_ids: List[int]

class CreateBookingPayload(BaseModel):
    room_ids: List[int]
    arrival_date: date
    departure_date: date
    phone_number: Optional[str] = None
    use_different_phone: bool = False
    save_phone: bool = False
    book_without_confirmation: bool = False

# --- Внутрішня HELPER-функція для отримання даних користувача ---

async def get_user_data_from_service(user_id: int) -> Optional[dict]:
    """Отримує дані користувача з мікросервісу User."""
    try:
        async with AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
            response.raise_for_status()
            return response.json()
    except Exception:
        return None
#
# 1. GET /bookings (Відображення сторінки бронювань)
#
#
# 1. GET /bookings (Відображення сторінки бронювань)
#
@router.get("/bookings")
async def get_booking_confirmation_page(
    request: Request,
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        user_id = None
        phone_from_session = None
        trust_level = 0
        is_authorized = False

        if session:
            user_id = session.get("user_id")
            phone_from_session = session.get("phone_number")
        
        if user_id:
            is_authorized = True
            # Намагаємося отримати дані з User-Service
            user_data = await get_user_data_from_service(user_id)
            
            if user_data:
                trust_level = user_data.get("trust_level", 0)
                db_phone = user_data.get("phone_number")
                
                # Якщо в сесії номера немає, а в БД є - синхронізуємо
                if not phone_from_session and db_phone:
                    phone_from_session = db_phone
                    session.set("phone_number", db_phone)

        context = {
            "request": request,
            "is_authorized": is_authorized,
            "phone_number": phone_from_session,
            "trust_level": trust_level
        }
        
        return templates.TemplateResponse("booking.html", context)

    except Exception as e:
        print("PIZDOS" + e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/api/rooms/details")
async def get_room_details_for_booking(
    payload: RoomDetailsRequest,
    db: Session = Depends(get_db)
):
    try:
        # (Потрібно реалізувати цей метод в репозиторії)
        rooms = room_repository.get_rooms_by_ids(db, payload.room_ids)
        
        # Повертаємо у форматі, зручному для JS
        rooms_data = [{
            "id": room.id,
            "type": room.type,
            "price": room.price,
            "guest_capacity": room.guest_capacity
        } for room in rooms]
        
        return JSONResponse(content=rooms_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))  

@router.post("/bookings/create_json")
async def create_booking_json(
    request: Request,
    payload: CreateBookingPayload,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        user_id = None
        phone_to_use = None
        booking_status = "Розглядається" # Статус за замовчуванням
        
        if session:
            user_id = session.get("user_id")

        if user_id:
            # --- ЛОГІКА АВТОРИЗОВАНОГО КОРИСТУВАЧА ---
            user_id_to_use = user_id
            user_data = await get_user_data_from_service(user_id)
            db_phone = user_data.get("phone_number") if user_data else None
            trust_level = user_data.get("trust_level", 0) if user_data else 0

            if payload.use_different_phone:
                # 1. Використовує інший номер
                phone_to_use = payload.phone_number
            elif db_phone:
                # 2. Використовує номер з БД
                phone_to_use = db_phone
            else:
                # 3. Номера в БД немає, беремо з форми
                phone_to_use = payload.phone_number
                
                if payload.save_phone and phone_to_use:
                    # Оновлюємо профіль користувача
                    try:
                        async with AsyncClient() as client:
                            await client.patch(
                                f"{USER_SERVICE_URL}/users/{user_id}", 
                                json={"phone_number": phone_to_use}
                            )
                        session.set("phone_number", phone_to_use)
                    except Exception:
                        pass # Не блокуємо бронювання, якщо сервіс впав

            # Логіка статусу для довірених
            if trust_level > 0 and payload.book_without_confirmation:
                booking_status = "Підтверджено"

        else:
            # --- ЛОГІКА ГОСТЯ ---
            user_id_to_use = None
            # Якщо в сесії є номер (гість повернувся), беремо його
            phone_to_use = session.get("phone_number") if session else None
            
            # Якщо в сесії немає, беремо з форми
            if not phone_to_use:
                phone_to_use = payload.phone_number
            
            # Якщо гість ввів номер, зберігаємо його в сесію
            if phone_to_use and session:
                session.set("phone_number", phone_to_use)

        # --- Валідація та Створення ---
        if not phone_to_use:
            raise HTTPException(status_code=400, detail="Мобільний номер є обов'язковим")
        
        if payload.departure_date <= payload.arrival_date:
            raise HTTPException(status_code=400, detail="Дата виїзду має бути пізнішою за дату заїзду")

        booking_repository.add_booking(
            db=db,
            user_id=user_id_to_use,
            phone_number=phone_to_use,
            room_ids=payload.room_ids,
            arrival_date=payload.arrival_date,
            departure_date=payload.departure_date,
            status=booking_status # Передаємо новий статус
        )
        
        # --- Повертаємо JSON відповідь ---
        if user_id:
            message = f"Бронювання успішно створено! Статус: {booking_status}"
        else:
            message = "Бронювання прийнято! Наш менеджер невдовзі зв'яжеться з вами для підтвердження."

        return JSONResponse(content={"success": True, "message": message})

    except Exception as e:
        detail = str(e.detail) if isinstance(e, HTTPException) else str(e)
        return JSONResponse(status_code=400, content={"success": False, "detail": detail})

# --- 4. НОВИЙ ЕНДПОІНТ: GET /my-bookings (Перегляд існуючих) ---

@router.get("/my-bookings")
async def get_my_bookings_page(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        context = {"request": request, "my_bookings": []}
        
        user_id = session.get("user_id") if session else None
        
        if session:
            context["success_message"] = session.pop("booking_success")

        if not user_id:
            context["message"] = "Будь ласка, увійдіть, щоб переглянути ваші бронювання."
            return templates.TemplateResponse("my-bookings.html", context)

        context["my_bookings"] = booking_repository.get_bookings_by_user_id(db, user_id)
        
        # (Тут можна додати форматування дат, якщо потрібно)
        
        return templates.TemplateResponse("my-bookings.html", context)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 5. НОВИЙ ЕНДПОІНТ: POST /bookings/cancel/{id} (Для користувача) ---

@router.post("/bookings/cancel/{booking_id}")
async def cancel_my_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        user_id = session.get("user_id") if session else None

        if not user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        booking = booking_repository.get_booking_by_id(db, booking_id)
        if not booking or booking.user_id != user_id:
            raise HTTPException(status_code=403, detail="Це не ваше бронювання")

        if booking.status != "Розглядається":
            raise HTTPException(status_code=400, detail="Неможливо скасувати бронювання, яке вже підтверджено або скасовано")

        # (Потрібен метод в репозиторії)
        booking_repository.update_booking_status(db, booking_id, "Скасовано")
        
        if session:
            session.set("booking_success", "Бронювання успішно скасовано.")
            
        return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        detail = str(e.detail) if isinstance(e, HTTPException) else str(e)
        raise HTTPException(status_code=400, detail=f"Помилка скасування: {detail}")

# --- 6. НОВІ АДМІН-ЕНДПОІНТИ ---

@router.get("/admin/panel")
async def get_admin_panel(
    request: Request,
    db: Session = Depends(get_db)
):
    # (Тут має бути перевірка на admin role)
    session = getSession(request=request, sessionStorage=session_storage)
    if not session or session.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")
        
    context = {
        "request": request,
        "success_message": session.pop("admin_success"),
        "all_bookings": booking_repository.get_all_bookings(db),
        "all_users": user_repository.get_all_users(db) # (Потрібен user_repository)
    }
    return templates.TemplateResponse("admin-panel.html", context)

@router.post("/admin/bookings/status/{booking_id}")
async def admin_update_booking_status(
    request: Request,
    booking_id: int,
    new_status: str = Form(...),
    db: Session = Depends(get_db)
):
    session = getSession(request=request, sessionStorage=session_storage)
    if not session or session.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")
    
    booking_repository.update_booking_status(db, booking_id, new_status)
    session.set("admin_success", f"Статус бронювання #{booking_id} оновлено на '{new_status}'")
    return RedirectResponse(url="/admin/panel", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/users/trust/{user_id}")
async def admin_update_user_trust(
    request: Request,
    user_id: int,
    trust_level: int = Form(...),
):
    session = getSession(request=request, sessionStorage=session_storage)
    if not session or session.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")

    # Оновлюємо через мікросервіс
    try:
        async with AsyncClient() as client:
            await client.patch(
                f"{USER_SERVICE_URL}/users/{user_id}", 
                json={"trust_level": trust_level}
            )
        session.set("admin_success", f"Рівень довіри для User ID #{user_id} оновлено на {trust_level}")
    except Exception as e:
        session.set("admin_success", f"Помилка оновлення User ID #{user_id}: {e}")
        
    return RedirectResponse(url="/admin/panel", status_code=status.HTTP_303_SEE_OTHER)

#
# 3. POST /bookings/edit/{booking_id} (Редагування бронювання)
#
@router.post("/bookings/edit/{booking_id}")
async def edit_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db),
    # Отримуємо нові дані з форми
    arrival_date: date = Form(...),
    departure_date: date = Form(...)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        # --- Блок перевірки сесії ---
        user_id = None
        user_role = None

        if session:
            user_id = session.get("user_id")
            user_role = session.get("user_role")
        # --- Кінець блоку ---

        # 1. Перевірка, чи користувач взагалі авторизований
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Тільки авторизовані користувачі можуть редагувати бронювання. Будь ласка, увійдіть."
            )

        # 2. Отримуємо бронювання
        booking = booking_repository.get_booking_by_id(db, booking_id)
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронювання не знайдено")

        # 3. Перевірка прав доступу (Авторизація)
        # (Ми тут, отже user_id і session існують)
        is_admin = user_role == "admin"
        is_owner = booking.user_id == user_id
        
        if not (is_admin or is_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="У вас немає прав на редагування цього бронювання"
            )

        # 4. Валідація дат
        if departure_date <= arrival_date:
            raise ValueError("Дата виїзду має бути пізнішою за дату заїзду")
        
        # 5. Готуємо дані та оновлюємо
        update_data = {
            "arrival_date": arrival_date,
            "departure_date": departure_date
        }
        
        # Припускаємо, що ваш репозиторій сам обробляє логіку
        # перевірки конфліктів дат при оновленні
        booking_repository.update_booking(db, booking_id, update_data)

        # 6. Встановлюємо повідомлення та робимо редірект
        session.set("booking_success", "Бронювання успішно оновлено.")
        return RedirectResponse(url="//my-bookings", status_code=status.HTTP_303_SEE_OTHER)

    except ValueError as e:
        # Відловлюємо помилку валідації дат
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        # Загальний обробник
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Помилка при оновленні бронювання: {str(e)}"
        )

@router.post("/bookings/delete/{booking_id}")
async def delete_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db)
):
    try:
        session = getSession(request=request, sessionStorage=session_storage)
        
        # --- ВИПРАВЛЕННЯ ---
        user_id = None
        user_role = None

        if session:
            user_id = session.get("user_id")
            user_role = session.get("user_role")
        # --- КІНЕЦЬ ВИПРАВЛЕННЯ ---

        # 1. Перевірка, чи користувач авторизований
        if not user_id:
            # (Спрацює якщо session is None або user_id is None)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Тільки авторизовані користувачі можуть видаляти бронювання. Будь ласка, увійдіть."
            )

        # (Сюди ми потрапимо, лише якщо user_id існує, а отже і session існує)
        
        # 2. Отримуємо бронювання
        booking = booking_repository.get_booking_by_id(db, booking_id)
        if not booking:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронювання не знайдено")

        # 3. Перевірка прав доступу
        is_admin = user_role == "admin"
        is_owner = booking.user_id == user_id
        
        if not (is_admin or is_owner):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ заборонено")

        # 4. Видалення
        booking_repository.delete_booking_by_id(db, booking_id)

        session.set("booking_success", "Бронювання успішно скасовано.")
        return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Помилка при видаленні: {str(e)}"
        )