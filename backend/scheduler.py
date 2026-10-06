# ============================================================
# 数据同步 + 告警判断 + 定时任务
# 每 30 秒从 OneNET 拉最新数据 -> 入库 -> 判断告警 -> 更新设备状态
# ============================================================

import time
from datetime import datetime

from sqlalchemy import desc

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
    """拉取设备在线状态与最新数据并处理（每次定时触发调用）"""
    db = SessionLocal()
    try:
        device = get_or_create_device(db)
        now = datetime.now()

        # 1. 判断设备在线状态（双保险）
        #    首选 OneNET 设备详情接口的真实在线状态；接口异常(None)时，
        #    回退到“本地超时”判断。
        #    【不能再用“能查到属性”判断在线】离线设备的最后一份数据云端会
        #    一直保留，属性查询照样有返回，但设备其实已经掉线。
        online = onenet_service.get_device_online()
        if online is True:
            device.status = "online"
            device.last_report = now
        elif online is False:
            device.status = "offline"
        else:
            # 云端状态查不到 -> 回退：太久没有新数据就判离线
            if (device.last_report is None or
                    (now - device.last_report).total_seconds() > config.ONLINE_TIMEOUT_SECONDS):
                device.status = "offline"

        # 2. 拉取最新属性值
        data = onenet_service.get_latest_property()
        if not data:
            db.commit()
            return

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

        # 3. 入库判断：
        #    (a) 数据发生变化 -> 入库（避免同一个固定值被反复写入）；
        #    (b) 设备在线且距上一条已超过 HEARTBEAT_SECONDS -> 补一条心跳，
        #        保证趋势图连续（离线时不会补）。
        last = (db.query(EnvData)
                .filter_by(device_id=device.id)
                .order_by(desc(EnvData.id)).first())
        changed = last is None or (
            last.temp != temp or last.humidity != humidity or
            last.lux != lux or last.air != air or bool(last.relay) != relay)
        heartbeat = (device.status == "online" and last is not None and
                     last.report_time is not None and
                     (now - last.report_time).total_seconds() >= config.HEARTBEAT_SECONDS)

        if changed:
            # 数据发生变化说明设备确实在实时上报，可作为在线证据
            device.last_report = now

        if changed or heartbeat:
            env = EnvData(
                device_id=device.id,
                temp=temp,
                humidity=humidity,
                lux=lux,
                air=air,
                relay=relay,
                status=status,
                report_time=now,
            )
            db.add(env)
            # 判断是否需要产生告警记录
            check_alerts(db, device, temp, humidity, air)

        db.commit()
        if changed:
            tag = ""
        elif heartbeat:
            tag = "（心跳补点）"
        else:
            tag = "（无变化未入库）"
        print("[同步] %s 在线=%s 温度=%s 湿度=%s 光照=%s 空气=%s 状态=%s%s" % (
            now.strftime("%H:%M:%S"), device.status,
            temp, humidity, lux, air, status, tag))
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
