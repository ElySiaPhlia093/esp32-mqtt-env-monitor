# ============================================================
# 控制接口: 远程控制继电器 + 控制日志
# 说明: 远程控制通过 OneNET 的设备命令下发实现
#       后端把指令推送到 OneNET，ESP32 订阅后执行
# ============================================================

import requests

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

import config
from database import get_db
from models import ControlLog
from schemas import ControlCommand, ControlLogOut

router = APIRouter(prefix="/api", tags=["control"])

# OneNET 设备命令下发接口（新平台使用 fuse 协议）
# 这里用设备属性设置接口，与 ESP32 订阅的 property/set topic 对应
ONENET_SET_URL = "https://iot-api.heclouds.com/thingmodel/set-device-property"


@router.post("/device/control", response_model=dict)
def control_device(cmd: ControlCommand, db: Session = Depends(get_db)):
    """远程控制指令: {"command": "relay_on"} / {"command": "relay_off"}"""
    if cmd.command not in ("relay_on", "relay_off"):
        return {"success": False, "message": "未知指令: " + cmd.command}

    relay_value = True if cmd.command == "relay_on" else False

    # 1. 推送指令到 OneNET（ESP32 订阅后执行）
    # 【实测】新版 OneNET 的 set-device-property 要求 params 里【直接给值】，
    #   写成 {"relay": {"value": true}} 会被判为 "bool type error"，
    #   必须写成 {"relay": true}。relay 是 bool 类型，用 True/False 而非 1/0。
    headers = {"Authorization": config.ONENET_TOKEN,
               "Content-Type": "application/json"}
    body = {
        "product_id": config.PRODUCT_ID,
        "device_name": config.DEVICE_NAME,
        "params": {"relay": relay_value},
    }
    try:
        res = requests.post(ONENET_SET_URL, headers=headers, json=body, timeout=10)
        result = res.json()
        success = result.get("code") == 0
    except requests.exceptions.RequestException as e:
        print("[控制] 网络异常:", e)
        return {"success": False, "message": "OneNET 通信失败"}

    # 2. 记录控制日志
    if success and cmd.source == "cloud":
        log = ControlLog(device_id=1, command=cmd.command, source=cmd.source)
        db.add(log)
        db.commit()

    return {"success": success, "message": "指令已下发" if success else "指令下发失败"}


@router.get("/control/logs", response_model=list[ControlLogOut])
def control_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """控制日志列表"""
    return (
        db.query(ControlLog)
        .order_by(desc(ControlLog.id))
        .limit(limit)
        .all()
    )
