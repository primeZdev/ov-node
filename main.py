import uvicorn
from core.config import settings
from core.logger import logger


def main():
    logger.info("Starting OV-Node...")
    uvicorn.run("core.app:api", host="0.0.0.0", port=settings.service_port, reload=True)


if __name__ == "__main__":
    main()
