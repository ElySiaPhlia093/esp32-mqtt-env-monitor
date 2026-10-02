# ============================================================
# 数据同步 + 告警判断 + 定时任务
# 每 30 秒从 OneNET 拉最新数据 -> 入库 -> 判断告警 -> 更新设备状态
# ============================================================

import time
from datetime import datetime

import config
import onenet_service
from database import SessionLocal
from models import Device, EnvData, Alert, ControlLog


def get_or_create_device(db):
    """获取设备记录，不存在则创建"""
    device = db.query(Device).filter_by(
        device_name=config.DEVICE_NAME).first()
    if not device:
        device = Device(device_name=config.DEVICE_NAME, status="offline")
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


def sync_once():
    """拉取最新数据并处理（每次定时触发调用）"""
    db = SessionLocal()
    try:
        data = onenet_service.get_latest_property()
        if not data:
            return
        device = get_or_create_device(db)

        temp = data.get("temp")
        humidity = data.get("humidity")
        lux = data.get("lux")
        air = data.get("air")
        relay = bool(data.get("relay", 0))

        # 判断控制状态（与 ESP32 本地逻辑一致，双保险）
        status = "normal"
        if temp is not None and temp > config.ALARM_TEMP_MAX:
            status = "temp_alarm"
        elif air is not None and air > config.ALARM_AIR_MAX:
            status = "air_alarm"
        elif humidity is not None and humidity < config.ALARM_HUMI_MIN:
            status = "humi_low_alarm"
        elif humidity is not None and humidity > config.ALARM_HUMI_MAX:
            status = "humi_high_alarm"

        # 1. 保存环境数据
        env = EnvData(
            device_id=device.id,
            temp=temp,
            humidity=humidity,
            lux=lux,
            air=air,
            relay=relay,
            status=status,
            report_time=datetime.now(),
        )
        db.add(env)

        # 2. 更新设备在线状态
        device.status = "online"
        device.last_report = datetime.now()

        # 3. 判断是否需要产生告警记录
        check_alerts(db, device, temp, humidity, air)

        db.commit()
        print("[同步] %s 温度=%s 湿度=%s 光照=%s 空气=%s 状态=%s" % (
            datetime.now().strftime("%H:%M:%S"),
            temp, humidity, lux, air, status))
    except Exception as e:
        print("[同步] 异常:", e)
    finally:
        db.close()


def check_alerts(db, device, temp, humidity, air):
    """阈值判断，产生告警记录（相同类型未解决的告警不重复触发）"""
    rules = []
    if temp is not None and temp > config.ALARM_TEMP_MAX:
        rules.append(("high_temp", temp, config.ALARM_TEMP_MAX))
    if humidity is not None and humidity < config.ALARM_HUMI_MIN:
        rules.append(("low_humidity", humidity, config.ALARM_HUMI_MIN))
    if humidity is not None and humidity > config.ALARM_HUMI_MAX:
        rules.append(("high_humidity", humidity, config.ALARM_HUMI_MAX))
    if air is not None and air > config.ALARM_AIR_MAX:
        rules.append(("high_air", air, config.ALARM_AIR_MAX))

    for alert_type, value, threshold in rules:
        # 已存在未解决的同类告警 -> 跳过
        existing = db.query(Alert).filter_by(
            device_id=device.id,
            alert_type=alert_type,
            status="triggered",
        ).first()
        if existing:
            continue
        alert = Alert(
            device_id=device.id,
            alert_type=alert_type,
            alert_value=value,
            threshold=threshold,
            status="triggered",
        )
        db.add(alert)
        print("[告警] 触发 %s: 值=%s 阈值=%s" % (alert_type, value, threshold))

        # 自动控制：温度过高/空气差/湿度过高都会开通风 -> 记录 relay_on 控制日志
        if alert_type in ("high_temp", "high_air", "high_humidity"):
            log = ControlLog(device_id=device.id, command="relay_on", source="auto")
            db.add(log)


def start_scheduler():
    """启动定时任务（线程方式，简单可靠）"""
    import threading

    def worker():
        while True:
            try:
                sync_once()
            except Exception as e:
                print("[调度] 出错:", e)
            time.sleep(config.SYNC_INTERVAL_SECONDS)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    print("[调度] 定时任务已启动，每 %d 秒同步一次" % config.SYNC_INTERVAL_SECONDS)
