from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
import psutil
from core.schema.all_schemas import User, ResponseModel, SetSettingsModel
from core.auth.auth import check_api_key
from core.service.user_managment import (
    create_user_on_server,
    change_user_status as change_user_status_on_server,
    delete_user_on_server,
    download_ovpn_file,
)
from core.setting.core import change_config


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


@router.post("/change-user-status", response_model=ResponseModel)
async def change_user_status(user: User, api_key: str = Depends(check_api_key)):
    result = change_user_status_on_server(user.name, user.status)
    if result:
        return ResponseModel(
            success=True,
            msg="User status changed successfully",
            data={"client_name": user.name},
        )
    return ResponseModel(success=False, msg="Failed to change user status")


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
