from pydantic import BaseModel
from typing import Any, Optional


class User(BaseModel):
    name: str
    status: str = "activate"


class ResponseModel(BaseModel):
    success: bool
    msg: str
    data: Optional[Any] = None


class SetSettingsModel(BaseModel):
    tunnel_address: str
    protocol: str
    ovpn_port: int
    set_new_setting: bool
