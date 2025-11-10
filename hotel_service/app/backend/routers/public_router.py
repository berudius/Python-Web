from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi_redis_session import getSession

from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from common.config.services_paths import USER_SERVICE_URL

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_public_page(request: Request):
    session = getSession(request, sessionStorage=session_storage)
    
    is_authorized = session and session.get("user_id") is not None
    is_admin = session and session.get("is_admin") is True

    context = {
        "request": request,
        "is_authorized": is_authorized,
        "is_admin": is_admin,
        "USER_SERVICE_URL": USER_SERVICE_URL
    }
    
    return templates.TemplateResponse("public.html", context)