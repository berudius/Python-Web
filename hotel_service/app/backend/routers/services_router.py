from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from common.config.redis_session_config import session_storage
from fastapi_redis_session import getSession

from ..config.jinja_template_config import templates


router = APIRouter()

@router.get("/services", response_class=HTMLResponse)
async def get_services_page(request: Request):
    return templates.TemplateResponse(
        "services.html", 
        {"request": request}
    )