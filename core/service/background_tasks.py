"""
Background tasks for monitoring and maintaining OpenVPN service
"""

import asyncio
from datetime import datetime
from logger import logger
from service.openvpn_monitor import openvpn_monitor


async def periodic_health_check():
    """
    Periodically check OpenVPN service health and auto-fix if needed
    Runs every 5 minutes
    """
    while True:
        try:
            logger.info("Running periodic OpenVPN health check...")
            
            # Check health
            health = openvpn_monitor.health_check()
            
            if not health["healthy"]:
                logger.warning(f"OpenVPN is unhealthy: {health['issues']}")
                
                # Attempt auto-fix
                logger.info("Attempting auto-fix...")
                fix_result = openvpn_monitor.auto_fix_and_restart()
                
                if fix_result["success"]:
                    logger.info("Auto-fix successful, OpenVPN is now healthy")
                else:
                    logger.error(f"Auto-fix failed: {fix_result}")
            else:
                logger.info("OpenVPN is healthy")
            
        except Exception as e:
            logger.error(f"Error in periodic health check: {e}")
        
        # Wait 5 minutes before next check
        await asyncio.sleep(300)


async def start_background_tasks():
    """Start all background monitoring tasks"""
    logger.info("Starting background monitoring tasks...")
    
    # Create task for periodic health check
    asyncio.create_task(periodic_health_check())
    
    logger.info("Background tasks started")
