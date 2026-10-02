# ============================================================
# Pydantic 响应模型
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EnvDataOut(BaseModel):
    id: int
    temp: Optional[float] = None
    humidity: Optional[float] = None
    lux: Optional[float] = None
    air: Optional[float] = None
    relay: bool = False
    status: str = "normal"
    report_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceOut(BaseModel):
    id: int
    device_name: str
    status: str
    last_report: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    alert_type: str
    alert_value: Optional[float] = None
    threshold: Optional[float] = None
    status: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ControlCommand(BaseModel):
    command: str  # relay_on / relay_off
    source: str = "cloud"


class ControlLogOut(BaseModel):
    id: int
    command: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True
