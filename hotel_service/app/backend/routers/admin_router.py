from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi_redis_session import getSession
from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from common.config.services_paths import USER_SERVICE_URL

router = APIRouter()

@router.get("/admin_page", response_class=HTMLResponse)
async def admin_page(request: Request):
    session = getSession(request, sessionStorage=session_storage)
    if not session:
        print("SESSION ПОХОДУ NULL")
        return RedirectResponse(url="/public")
    elif session.get("user_role") != "admin":
        return RedirectResponse(url="/autentificated_user_page")
    else:
        return templates.TemplateResponse("admin_page.html", {"request": request, "USER_SERVICE_URL": USER_SERVICE_URL})
    
