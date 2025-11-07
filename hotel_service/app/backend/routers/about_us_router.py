from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi_redis_session import getSession
from ..config.jinja_template_config import templates
from common.config.redis_session_config import session_storage
from common.config.services_paths import USER_SERVICE_URL

router = APIRouter()

@router.get("/about_us", response_class=HTMLResponse)
async def get_about_us(request: Request):
    return templates.TemplateResponse("about_us.html", {"request": request, "USER_SERVICE_URL": USER_SERVICE_URL})

    
