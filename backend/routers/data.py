# ============================================================
# 数据接口: 最新数据 / 历史数据 / 设备状态
# ============================================================

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from models import Device, EnvData
from schemas import EnvDataOut, DeviceOut

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/device/status", response_model=DeviceOut)
def get_device_status(db: Session = Depends(get_db)):
    """获取设备在线状态"""
    device = db.query(Device).first()
    if not device:
        return DeviceOut(id=0, device_name="none", status="offline")
    return device


@router.get("/data/latest", response_model=EnvDataOut)
def get_latest(db: Session = Depends(get_db)):
    """获取最新一条环境数据（实时面板用）"""
    env = db.query(EnvData).order_by(desc(EnvData.id)).first()
    if not env:
        return EnvDataOut(id=0)
    return env


@router.get("/data/history", response_model=list[EnvDataOut])
def get_history(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """获取最近 N 小时的历史数据（趋势图用）"""
    since = datetime.now() - timedelta(hours=hours)
    records = (
        db.query(EnvData)
        .filter(EnvData.created_at >= since)
        .order_by(EnvData.created_at.asc())
        .all()
    )
    return records
