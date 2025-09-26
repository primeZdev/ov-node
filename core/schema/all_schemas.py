from pydantic import BaseModel
from typing import Any, Optional


class User(BaseModel):
    name: str


class ResponseModel(BaseModel):
    success: bool
    msg: str
    data: Optional[Any] = None
