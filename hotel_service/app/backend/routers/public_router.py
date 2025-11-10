from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse

from common.config.redis_session_config import session_storage
from fastapi_redis_session import getSession

from ..config.jinja_template_config import templates
from common.config.services_paths import USER_SERVICE_URL


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def register_get(request: Request):
    session = getSession(request, sessionStorage=session_storage)
    if session and session.get("user_id"):
        return templates.TemplateResponse("public.html", {"request": request, "is_authorized":True})
    return templates.TemplateResponse("public.html", {"request": request, "is_authorized":False, "USER_SERVICE_URL":USER_SERVICE_URL})