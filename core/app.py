from fastapi import FastAPI
import uvicorn

from routers import core_router
from config import settings
from logger import logger
from version import __version__

api = FastAPI(title="OV Node",
            version=__version__,
            docs_url="/doc" if settings.doc else None)

api.include_router(core_router)

if __name__ == "__main__":
    logger.info("OV-Node is starting...")
    uvicorn.run("app:api", host="0.0.0.0", port=settings.service_port, reload=True)
