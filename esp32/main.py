# ============================================================
# 车间环境智能监测与控制系统 —— ESP32-S3 主程序 (MicroPython)
# 开发板: ESP32-S3-N16R8（44 引脚）
#
# 功能:
#   1. 连接 WiFi
#   2. 采集 温湿度(DHT11) / 光照(BH1750) / 空气(MQ-135)
#   3. 本地自动控制: 温度超标 -> 开风扇(继电器) + 蜂鸣器报警
#   4. MQTT 上报 OneNET 云平台
#   5. 断网时数据缓存本地，恢复后补传
#   6. 订阅平台下行指令，支持远程控制继电器
#
# 使用: 把本文件夹所有 .py 文件 + umqtt 文件夹拷贝到 ESP32 板子上，
#       Thonny 里点击运行 main.py 即可
# ============================================================

import network
import time
import json

import config
from machine import Pin, SoftI2C
from sensors import TempHumiSensor, BH1750Sensor, MQ135Sensor, Relay, Buzzer
from oled_display import OLEDDisplay
from mqtt_client import OneNETClient
import cache

# ---------------- I2C 总线（BH1750 与 OLED 共用同一条） ----------------
# 实测：ESP32-S3 上硬件 I2C 通道不可用，必须用软 I2C；
# 且引脚需启用内部上拉、速率降到 50kHz 才能稳定通信
i2c = SoftI2C(scl=Pin(config.I2C_SCL_PIN, Pin.OPEN_DRAIN, Pin.PULL_UP),
              sda=Pin(config.I2C_SDA_PIN, Pin.OPEN_DRAIN, Pin.PULL_UP),
              freq=50000)

# ---------------- 硬件初始化（未接的传感器不影响整体运行） ----------------
dht11 = TempHumiSensor(config.DHT11_PIN)
mq135 = MQ135Sensor(config.MQ135_PIN)
relay = Relay(config.RELAY_PIN)
buzzer = Buzzer(config.BUZZER_PIN)
oled = OLEDDisplay(i2c)

# BH1750 构造时会立即发送 I2C 指令，未接时会抛异常，这里做保护
try:
    bh1750 = BH1750Sensor(i2c)
except OSError as e:
    print("[初始化] BH1750 未接或异常:", e)
    bh1750 = None


# ---------------- WiFi 连接 ----------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("[WiFi] 正在连接 %s ..." % config.WIFI_SSID)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        # 最多等 20 秒
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    if wlan.isconnected():
        print("[WiFi] 连接成功, IP:", wlan.ifconfig()[0])
        return True
    else:
        print("[WiFi] 连接失败，请检查 WiFi 名称和密码")
        return False


# ---------------- 采集所有传感器 ----------------
def read_all_sensors():
    temp, humi = dht11.read()
    lux = bh1750.read() if bh1750 else None
    air = mq135.read()
    data = {
        "temp": temp,
        "humidity": humi,
        "lux": lux,
        "air": air,
    }
    print("[采集] 温度=%s 湿度=%s 光照=%s 空气=%s" % (
        data["temp"], data["humidity"], data["lux"], data["air"]))
    return data


# ---------------- 本地自动控制逻辑 ----------------
def local_control(data, manual_hold=False):
    """根据阈值自动控制继电器 + 蜂鸣器，返回控制状态

    报警方式: 只要处于报警状态，蜂鸣器就【持续鸣叫】，
    直到下一轮检查发现环境恢复正常，才停止鸣叫。
    manual_hold 为 True 表示用户刚做过远程操作，环境正常时不强制关风扇。
    """
    status = "normal"
    if data["temp"] is not None and data["temp"] > config.ALARM_TEMP_MAX:
        relay.on()       # 温度过高，开风扇散热
        buzzer.on()
        status = "temp_alarm"
    elif data["air"] is not None and data["air"] > config.ALARM_AIR_MAX:
        relay.on()       # 空气质量差，开排风
        buzzer.on()
        status = "air_alarm"
    elif data["humidity"] is not None and data["humidity"] < config.ALARM_HUMI_MIN:
        relay.off()      # 湿度过低靠风扇无法改善，故只报警、不吸合继电器
        buzzer.on()
        status = "humi_low_alarm"
    elif data["humidity"] is not None and data["humidity"] > config.ALARM_HUMI_MAX:
        relay.on()       # 湿度过高，开风扇/排风降湿
        buzzer.on()
        status = "humi_high_alarm"
    else:
        # 环境正常：若此前是远程手动操作，保持用户设定，不强行关闭
        if not manual_hold:
            relay.off()
        buzzer.off()     # 环境恢复正常，停止鸣叫
        status = "normal"
    return status


# ---------------- 下行指令处理（远程控制） ----------------
# 远程手动标志：用户远程操作后置 True，在环境正常期间本地自动逻辑
# 不再把继电器关掉（否则刚打开的风扇会在 10 秒后被本地逻辑关闭）；
# 一旦出现报警，自动控制重新接管。
manual_hold = False


def handle_command(data):
    """收到平台下发的控制指令

    【实测】新版 OneNET 下发格式是 {"params": {"relay": true}}（值直传），
    老格式是 {"params": {"relay": {"value": true}}}，这里两种都兼容。
    """
    global manual_hold
    try:
        params = data.get("params", {})
        if "relay" in params:
            raw = params["relay"]
            value = raw.get("value", False) if isinstance(raw, dict) else raw
            relay.set(value)
            manual_hold = True
            print("[控制] 远程指令: 继电器 ->", "ON" if value else "OFF")
    except Exception as e:
        print("[控制] 指令处理异常:", e)


# ---------------- 主循环 ----------------
def main():
    global manual_hold

    if not connect_wifi():
        print("[WiFi] 未联网，进入本地模式（继续采集与显示，联网后自动补传）")

    mqtt = OneNETClient()
    mqtt.on_command = handle_command
    mqtt.connect()

    while True:
        # 1. 检查是否有下行指令（远程控制）
        mqtt.check_message()

        # 2. 采集数据
        data = read_all_sensors()

        # 3. 本地自动控制（超限自动开风扇）
        status = local_control(data, manual_hold)
        print("[状态] %s" % status)
        if status != "normal":
            # 出现报警，自动控制优先接管，取消远程手动保持
            manual_hold = False

        # 4. OLED 本地显示
        oled.show(data["temp"], data["humidity"], data["lux"], data["air"],
                  relay.state(), status)

        # 5. 上报数据（含继电器状态）
        # 【实测】物模型里只定义了 temp/humidity/lux/air/relay 五个属性，
        # 若多传未定义的标识符（如 status），平台会整条拒绝（code 2306
        # identifier not exist），所以 status 仅供本地 OLED 显示、不上报；
        # 另外 relay 是 bool 类型，必须上报 True/False 而不是 1/0。
        data["relay"] = bool(relay.state())

        if mqtt.connected:
            # 6. 先补传之前缓存的断网数据
            cached = cache.dump_cache()
            if cached:
                print("[补传] 补传 %d 条缓存数据..." % len(cached))
                for item in cached:
                    mqtt.publish(item)
            # 7. 上报当前数据
            ok = mqtt.publish(data)
            if not ok:
                cache.save_cache(data)   # 上报失败 -> 缓存
        else:
            # 断网了，缓存当前数据
            cache.save_cache(data)
            mqtt.reconnect_if_needed()

        # 8. 等待下个周期
        # 【实测】不能整段 sleep：平台下发指令后要等整个周期才被处理，
        # 会超出平台的等待窗口，接口返回 10411"设备响应超时"。
        # 这里拆成 1 秒一跳，期间持续轮询下行指令。
        for _ in range(config.UPLOAD_INTERVAL):
            mqtt.check_message()
            time.sleep(1)


if __name__ == "__main__":
    main()
