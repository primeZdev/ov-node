from fastapi import FastAPI

from core.routers import core_router
from core.config import settings

api = FastAPI(title="OV Node", docs_url="/doc" if settings.doc else None)

api.include_router(core_router)
