from fastapi import FastAPI
import uvicorn

from routers import core_router
from config import settings
from logger import logger

api = FastAPI(docs_url=None)

api.include_router(core_router)

if __name__ == "__main__":
    logger.info("OV-Node is starting...")
    uvicorn.run("app:api", host="0.0.0.0", port=settings.service_port, reload=True)
