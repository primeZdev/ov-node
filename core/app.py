from fastapi import FastAPI
import uvicorn

from routers import core_router
from config import settings

api = FastAPI()

api.include_router(core_router)

if __name__ == "__main__":
    uvicorn.run("app:api", host="0.0.0.0", port=settings.service_port, reload=True)
