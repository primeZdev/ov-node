from fastapi import FastAPI
import uvicorn

from routers import core_router
from config import settings
from logger import logger
from version import __version__
from setting.core import ensure_openvpn_running
from service.background_tasks import start_background_tasks

api = FastAPI(title="OV Node",
            version=__version__,
            docs_url="/doc" if settings.doc else None)

api.include_router(core_router)

@api.on_event("startup")
async def startup_event():
    """Run initialization tasks on startup"""
    logger.info("Running startup initialization...")
    
    # Ensure OpenVPN service is running correctly
    # This will automatically:
    # - Fix any config issues (missing IPs, etc.)
    # - Enable the service if needed
    # - Start/restart the service
    # - Verify it's running and listening on port
    logger.info("Checking and ensuring OpenVPN service is running...")
    openvpn_ok = ensure_openvpn_running()
    
    if openvpn_ok:
        logger.info("✓ OpenVPN service is healthy and running")
    else:
        logger.error("✗ Failed to ensure OpenVPN is running - check logs for details")
    
    # Start background monitoring tasks
    await start_background_tasks()
    
    logger.info("Startup initialization completed")

if __name__ == "__main__":
    logger.info("OV-Node is starting...")
    # Disable reload in production for stability
    uvicorn.run("app:api", host="0.0.0.0", port=settings.service_port, reload=False)
