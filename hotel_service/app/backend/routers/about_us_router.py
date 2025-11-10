from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..config.jinja_template_config import templates
from fastapi_redis_session import getSession
from common.config.redis_session_config import session_storage
from common.config.services_paths import USER_SERVICE_URL

router = APIRouter()

@router.get("/about_us", response_class=HTMLResponse)
async def get_abous_us(request: Request):
    session = getSession(request=request, sessionStorage=session_storage)
    if session and session.get("user_id"):
        return templates.TemplateResponse("about_us.html", {"request":request, "is_authorized":True})
    return templates.TemplateResponse("about_us.html", {"request":request, "is_authorized":False, "USER_SERVICE_URL":USER_SERVICE_URL})
    