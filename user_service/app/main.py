from fastapi import FastAPI
from user_service.app.backend.routers import auth_router
from common.db.database import Base, engine
from common.docker.redis_launcher import run_redis
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Lifespan event in user_service triggered ---")
    Base.metadata.create_all(bind=engine)
    run_redis()
    
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router.router)

