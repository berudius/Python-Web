from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..config.jinja_template_config import templates

router = APIRouter()

@router.get("/about_us", response_class=HTMLResponse)
async def get_abous_us(request: Request):
    return templates.TemplateResponse("about_us.html", {"request":request})