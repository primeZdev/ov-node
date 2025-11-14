from fastapi import Header, HTTPException, status

from core.config import settings
from core.logger import logger


async def check_api_key(key: str = Header(...)) -> str:
    """Check if the provided API key is valid."""
    if key != settings.api_key:
        logger.warning(f"Invalid API key: [{key}]")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return key
