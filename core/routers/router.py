from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
import psutil
import asyncio
import os
from core.schema.all_schemas import (
    User,
    ResponseModel,
    SetSettingsModel,
    LogQueryParams,
)
from core.auth.auth import check_api_key
from core.service.user_managment import (
    create_user_on_server,
    change_user_status as change_user_status_on_server,
    delete_user_on_server,
    download_ovpn_file,
    get_users_usage,
)
from core.setting.core import change_config
from core.logger import LOG_FILE
from core.config import settings

router = APIRouter(prefix="/sync", tags=["node_sync"])


def _get_version() -> str:
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
            return content.split('version = "')[1].split('"')[0]
    except Exception:
        return "unknown"


@router.get("/status", response_model=ResponseModel)
async def get_status(api_key: str = Depends(check_api_key)):
    """Get current node status (read-only)"""
    status = {
        "status": "running",
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "node_version": _get_version(),
        "service_port": settings.service_port,
    }
    return ResponseModel(
        success=True, msg="Node status retrieved successfully", data=status
    )


@router.post("/settings", response_model=ResponseModel)
async def update_settings(
    request: SetSettingsModel, api_key: str = Depends(check_api_key)
):
    """Update OpenVPN settings (port, protocol, tunnel address)"""
    if not request.set_new_setting:
        return ResponseModel(
            success=False, msg="set_new_setting must be true to apply changes"
        )

    change_settings = change_config(request)
    if not change_settings:
        return ResponseModel(success=False, msg="Failed to change settings")

    return ResponseModel(
        success=True,
        msg="Settings updated successfully",
        data={
            "tunnel_address": request.tunnel_address,
            "protocol": request.protocol,
            "ovpn_port": request.ovpn_port,
        },
    )


@router.get("/usage", response_model=ResponseModel)
async def get_all_user_usage(api_key: str = Depends(check_api_key)):
    usages = get_users_usage()
    if usages:
        return ResponseModel(
            success=True, msg="Latest user usage received", data=usages
        )
    return ResponseModel(
        success=True,
        msg="No user is using it.",
    )


@router.post("/user", response_model=ResponseModel)
async def create_user(user: User, api_key: str = Depends(check_api_key)):
    success = create_user_on_server(user.name)
    if success:
        return ResponseModel(
            success=True,
            msg="User created successfully",
            data={"client_name": user.name},
        )
    return ResponseModel(success=False, msg="Failed to create user")


@router.delete("/user/{name}", response_model=ResponseModel)
async def delete_user(name: str, api_key: str = Depends(check_api_key)):
    result = delete_user_on_server(name)
    if result:
        return ResponseModel(
            success=True,
            msg="User deleted successfully",
            data={"client_name": name},
        )
    return ResponseModel(success=False, msg="Failed to delete user")


@router.put("/user", response_model=ResponseModel)
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


def _read_log_lines(
    file_path: str, lines: int, level_filter: str | None = None
) -> list[str]:
    """Read last N lines from log file, optionally filtered by level."""
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
    except Exception:
        return []

    result = []
    for line in reversed(all_lines):
        if level_filter and level_filter.upper() not in line.upper():
            continue
        result.append(line.rstrip("\n"))
        if len(result) >= lines:
            break

    return list(reversed(result))


async def _log_stream_generator(file_path: str, level_filter: str | None = None):
    """Generate SSE events for real-time log streaming."""
    initial_lines = _read_log_lines(file_path, 50, level_filter)
    for line in initial_lines:
        yield f"data: {line}\n\n"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    if level_filter and level_filter.upper() not in line.upper():
                        continue
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    await asyncio.sleep(0.5)
    except Exception:
        return


@router.get("/logs")
async def get_logs(
    params: LogQueryParams = Depends(), api_key: str = Depends(check_api_key)
):
    """
    Get node logs.
    - If follow=false: returns last N lines as JSON
    - If follow=true: streams new lines via Server-Sent Events (SSE)
    """
    if params.follow:
        return StreamingResponse(
            _log_stream_generator(LOG_FILE, params.level),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    lines = _read_log_lines(LOG_FILE, params.lines, params.level)
    return ResponseModel(
        success=True,
        msg=f"Retrieved {len(lines)} log lines",
        data={"lines": lines, "total_lines": len(lines)},
    )
