from fastapi_redis_session import SessionStorage, basicConfig

basicConfig(redisURL="redis://localhost:6379/0", expireTime=3600)
session_storage = SessionStorage()
