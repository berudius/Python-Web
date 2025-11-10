from fastapi import APIRouter, HTTPException, status, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session
from common.db.database import get_db
from ..repositories.user_repository import get_user_by_login, get_user_by_id, create_user, authenticate_user

from fastapi_redis_session import setSession, getSession, deleteSession
from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from common.config.services_paths import HOTEL_SERVICE_URL

router = APIRouter()

@router.get("/registration", response_class=HTMLResponse)
async def register_get(request: Request):
    session = getSession(request, sessionStorage=session_storage)
    if session:
        if session.get("user_id"):
            return RedirectResponse(url=f"{HOTEL_SERVICE_URL}/")
        else:
            return RedirectResponse(url=f"/logout")
    return templates.TemplateResponse("registration.html", {"request": request, "HOTEL_SERVICE_URL": HOTEL_SERVICE_URL})

@router.post("/registration", response_class=HTMLResponse)
async def register_post(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    session = getSession(request, sessionStorage=session_storage)
    if session:
        if session.get("user_id"):
            return RedirectResponse(url=f"{HOTEL_SERVICE_URL}/")
        else:
            return RedirectResponse(url=f"/logout")

    user = get_user_by_login(db, login)
    if user:
        return templates.TemplateResponse("registration.html", {"request": request, "error": "Користувач із таким login вже існує", "HOTEL_SERVICE_URL": HOTEL_SERVICE_URL})
    create_user(db, login, password)
    return templates.TemplateResponse("login.html", {"request": request, "msg": "Реєстрація пройшла успішно. Увійдіть.", "HOTEL_SERVICE_URL": HOTEL_SERVICE_URL})

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    session = getSession(request, sessionStorage=session_storage)
    if session:
        if session.get("user_id"):
            return RedirectResponse(url=f"{HOTEL_SERVICE_URL}/")
        else:
            return RedirectResponse(url=f"/logout")
    return templates.TemplateResponse("login.html", {"request": request, "HOTEL_SERVICE_URL": HOTEL_SERVICE_URL})

@router.post("/login")
async def login_post(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    session = getSession(request, sessionStorage=session_storage)
    if session:
        if session.get("user_id"):
            return RedirectResponse(url=f"{HOTEL_SERVICE_URL}/")
        else:
            return RedirectResponse(url=f"/logout")

    user = authenticate_user(db, login, password)

    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Невірний логін або пароль", "HOTEL_SERVICE_URL": HOTEL_SERVICE_URL})

    redirect_url = None
    if user.role == "admin":
        redirect_url = f"{HOTEL_SERVICE_URL}/"
    else:
        redirect_url = f"{HOTEL_SERVICE_URL}/"
    
    response = RedirectResponse(url=redirect_url, status_code=303)

    setSession(
        response,
        {"user_id": user.id, "user_role": user.role, "trust_level": user.trust_level},
        sessionStorage=session_storage
    )

    return response
    
    

@router.get("/users/{user_id}")
async def get_user(
    user_id:int,
    db: Session = Depends(get_db)
):
    user = get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    user_data = {
        "id": user.id,
        "login": user.login,
        "role": user.role,
        "phone_number": user.phone_number,
        "trust_level": user.trust_level
    }

    return user_data


@router.get("/logout")
async def logout(request: Request):
    session = getSession(request, sessionStorage=session_storage)
    if session:
        deleteSession(sessionId=request.cookies.get("ssid"), sessionStorage=session_storage)
    return RedirectResponse(url=f"/login")

