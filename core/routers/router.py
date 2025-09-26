from fastapi import APIRouter, Depends

from schema.all_schemas import User, ResponseModel
from auth.auth import check_api_key


router = APIRouter(prefix="/sync", tags=["node_sync"])


@router.post("/create-user", response_model=ResponseModel)
async def create_user(user: User, api_key: str = Depends(check_api_key)):
    return {"success": True, "msg": "User created successfully", "data": user}
