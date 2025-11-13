from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
import psutil
from schema.all_schemas import User, ResponseModel, SetSettingsModel
from auth.auth import check_api_key
from service.user_managment import (
    create_user_on_server,
    delete_user_on_server,
    download_ovpn_file,
)
from setting.core import change_config
from service.openvpn_monitor import (
    get_openvpn_health,
    check_and_fix_openvpn_service,
    openvpn_monitor
)


router = APIRouter(prefix="/sync", tags=["node_sync"])


@router.post("/get-status", response_model=ResponseModel)
async def get_status(request: SetSettingsModel, api_key: str = Depends(check_api_key)):
    """Get the current status of the node and set ovpn settings"""
    if request.set_new_setting:
        change_settings = change_config(request)
        if not change_settings:
            return ResponseModel(success=False, msg="Failed to change settings")

    status = {"status": "running"}
    cpu_usage = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    status.update(
        {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_info.percent,
        }
    )
    return ResponseModel(
        success=True, msg="Node status retrieved successfully", data=status
    )


@router.post("/create-user", response_model=ResponseModel)
async def create_user(user: User, api_key: str = Depends(check_api_key)):
    success = create_user_on_server(user.name)
    if success:
        return ResponseModel(
            success=True,
            msg="User created successfully",
            data={"client_name": user.name},
        )
    return ResponseModel(success=False, msg="Failed to create user")


@router.post("/delete-user", response_model=ResponseModel)
async def delete_user(user: User, api_key: str = Depends(check_api_key)):
    result = delete_user_on_server(user.name)
    if result:
        return ResponseModel(
            success=True,
            msg="User deleted successfully",
            data={"client_name": user.name},
        )
    return ResponseModel(success=False, msg="Failed to delete user")


@router.get("/download/ovpn/{client_name}")
async def download_ovpn(client_name: str, api_key: str = Depends(check_api_key)):
    response = await download_ovpn_file(client_name)
    if response:
        return FileResponse(
            path=response,
            filename=f"{client_name}.ovpn",
            media_type="application/x-openvpn-profile",
        )
    else:
        return ResponseModel(success=False, msg="OVPN file not found", data=None)


@router.get("/openvpn/health", response_model=ResponseModel)
async def openvpn_health(api_key: str = Depends(check_api_key)):
    """Get OpenVPN service health status"""
    health = get_openvpn_health()
    return ResponseModel(
        success=health["healthy"],
        msg="OpenVPN health check completed",
        data=health
    )


@router.post("/openvpn/fix", response_model=ResponseModel)
async def openvpn_fix(api_key: str = Depends(check_api_key)):
    """Automatically detect and fix OpenVPN service issues"""
    result = check_and_fix_openvpn_service()
    return ResponseModel(
        success=result["success"],
        msg="OpenVPN auto-fix completed",
        data=result
    )


@router.get("/openvpn/status", response_model=ResponseModel)
async def openvpn_status(api_key: str = Depends(check_api_key)):
    """Get detailed OpenVPN service status"""
    status = openvpn_monitor.check_service_status()
    port, protocol = openvpn_monitor.get_config_port_protocol()
    port_open = openvpn_monitor.check_port_listening(port, protocol)
    
    data = {
        "service_status": status,
        "port": port,
        "protocol": protocol,
        "port_open": port_open
    }
    
    return ResponseModel(
        success=True,
        msg="OpenVPN status retrieved",
        data=data
    )


@router.post("/openvpn/restart", response_model=ResponseModel)
async def openvpn_restart(api_key: str = Depends(check_api_key)):
    """Restart OpenVPN service"""
    success = openvpn_monitor.restart_service()
    return ResponseModel(
        success=success,
        msg="OpenVPN restart completed" if success else "Failed to restart OpenVPN",
        data={"restarted": success}
    )

