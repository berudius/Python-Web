from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from httpx import AsyncClient

from sqlalchemy.orm import Session
from common.db.database import get_db

from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from fastapi_redis_session import getSession, deleteSession
from common.config.services_paths import USER_SERVICE_URL

router = APIRouter()

@router.get("/autentificated_user_page", response_class=HTMLResponse)
async def autentificated_user_page(request: Request, db: Session = Depends(get_db)):
    session = getSession(request, sessionStorage=session_storage)
    
    if not session or not session.get("user_id"):
        return RedirectResponse(url="/public")
    if session.get("user_role") == "admin":
        return RedirectResponse(url="/admin_page")
    
    user_id = session.get("user_id")
    client = AsyncClient()
    responce = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")

    if responce.status_code != 200:
        deleteSession(request, sessionStorage=session_storage)
        return RedirectResponse(url=f"{USER_SERVICE_URL}/login")
    
    user_data = responce.json()

    return templates.TemplateResponse(
        "autentificated_user_page.html",
        { "request": request,
          "user_login": user_data["login"],
          "user_role": user_data["role"],
          "USER_SERVICE_URL": USER_SERVICE_URL
        }
    )