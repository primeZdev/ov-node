from fastapi import APIRouter, Depends
import psutil
from schema.all_schemas import User, ResponseModel
from auth.auth import check_api_key
from service.user_managment import create_user_on_server, delete_user_on_server


router = APIRouter(prefix="/sync", tags=["node_sync"])


@router.get("/get-status", response_model=ResponseModel)
async def get_status(api_key: str = Depends(check_api_key)):
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
    result = await delete_user_on_server(user.name)
    if result:
        return ResponseModel(
            success=True,
            msg="User deleted successfully",
            data={"client_name": user.name},
        )
    return ResponseModel(success=False, msg="Failed to delete user")
