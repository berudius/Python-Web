from fastapi_redis_session import SessionStorage, basicConfig

redis_url = "redis://:Zox7QWEhVCZ8fG92apaf6aVd0BAdMHT9@redis-19205.c304.europe-west1-2.gce.cloud.redislabs.com:19205/0"

basicConfig(
    redisURL=redis_url,
    expireTime=3600,
)
# basicConfig(redisURL="redis://localhost:6379/0", expireTime=3600)
session_storage = SessionStorage()
