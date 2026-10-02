# ============================================================
# ORM 模型
# 表结构: devices / env_data / alerts / control_log
# ============================================================

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey

from database import Base


class Device(Base):
    """设备表"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    device_name = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="offline")     # online / offline
    last_report = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class EnvData(Base):
    """环境数据表（传感器历史数据）"""
    __tablename__ = "env_data"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    temp = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    lux = Column(Float, nullable=True)
    air = Column(Float, nullable=True)
    relay = Column(Boolean, default=False)             # 继电器状态
    status = Column(String(20), default="normal")      # 控制状态
    report_time = Column(DateTime, nullable=True)      # OneNET 时间
    created_at = Column(DateTime, default=datetime.now)


class Alert(Base):
    """告警记录表"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    alert_type = Column(String(50))                    # high_temp / low_humidity / high_air
    alert_value = Column(Float)
    threshold = Column(Float)
    status = Column(String(20), default="triggered")   # triggered / resolved
    triggered_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)


class ControlLog(Base):
    """控制记录表（远程/自动控制日志）"""
    __tablename__ = "control_log"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    command = Column(String(50))                       # relay_on / relay_off
    source = Column(String(20), default="auto")        # auto(本地自动) / cloud(远程)
    created_at = Column(DateTime, default=datetime.now)
