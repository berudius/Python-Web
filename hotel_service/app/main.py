from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles 

from ..app.backend.routers import  public_router, services_router, about_us_router, rooms_router, booking_router
from ..app.backend.config.statica_config import static_dir_path
from ..app.backend import models
from common.db.database import Base, engine
from common.docker.redis_launcher import run_redis, stop_redis
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    Base.metadata.create_all(bind=engine) 
    run_redis()

    try:
        yield
    finally:
        stop_redis()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=static_dir_path), name="static")

app.include_router(public_router.router)
app.include_router(services_router.router)
app.include_router(about_us_router.router)
app.include_router(rooms_router.router)
app.include_router(booking_router.router)

