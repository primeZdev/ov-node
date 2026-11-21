from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
import re


USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def validate_username(v: str) -> str:
    if not USERNAME_PATTERN.match(v):
        raise ValueError('Username must be 1-64 characters, only alphanumeric, underscore, and hyphen allowed')
    return v


class User(BaseModel):
    name: str = Field(..., description="Username", min_length=1, max_length=64)
    status: str = "activate"

    @property
    def validated_name(self) -> str:
        return validate_username(self.name)


class ResponseModel(BaseModel):
    success: bool
    msg: str
    data: Optional[Any] = None


class SetSettingsModel(BaseModel):
    tunnel_address: str
    protocol: str
    ovpn_port: int
    set_new_setting: bool


class UsersUsage(BaseModel):
    users: Dict[str, float]


class LogQueryParams(BaseModel):
    lines: int = Field(default=100, ge=1, le=5000, description="Number of lines to return")
    follow: bool = Field(default=False, description="Stream new lines in real-time (SSE)")
    level: Optional[str] = Field(default=None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)")