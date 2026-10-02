# ============================================================
# 传感器驱动模块 (ESP32-S3-N16R8)
# 包含: DHT11(温湿度) / BH1750(光照) / MQ-135(空气质量)
#       SSD1306 OLED 背光屏 / 继电器 / 有源蜂鸣器
# 全部用 MicroPython 实现，纯 Python 语法
# ============================================================

import dht
from machine import Pin, ADC
import time

import config


class TempHumiSensor:
    """DHT11 温湿度传感器（单总线，DATA 接 4.7k 上拉可选）"""
    def __init__(self, pin):
        self.sensor = dht.DHT11(Pin(pin))

    def read(self):
        """返回 (温度℃, 湿度%)，读取失败返回 (None, None)"""
        try:
            self.sensor.measure()
            temp = self.sensor.temperature()
            humi = self.sensor.humidity()
            return temp, humi
        except OSError:
            return None, None


class BH1750Sensor:
    """GY-302 / BH1750 光照强度传感器 (I2C, 地址 0x23)

    I2C 总线由 main.py 创建后传入（与 OLED 共用同一条总线）。
    """
    def __init__(self, i2c, addr=0x23):
        self.i2c = i2c
        self.addr = addr  # BH1750 默认地址（ADDR 脚悬空/接地）
        # 上电指令：连续高分辨率模式
        self.i2c.writeto(self.addr, b'\x10')

    def read(self):
        """返回光照强度 (单位: lx)，失败返回 None"""
        try:
            time.sleep(0.2)  # 等待测量完成
            data = self.i2c.readfrom(self.addr, 2)
            lux = (data[0] << 8 | data[1]) / 1.2
            return int(lux)
        except OSError:
            return None


class MQ135Sensor:
    """MQ-135 空气质量传感器（4 引脚，AO 模拟输出 -> ADC1）

    按 ESP32-S3 数据手册，ADC 满量程随衰减档位变化，ATTN3（MicroPython 里的
    ATTN_11DB）满量程约 2.9V。而 MQ-135 模块若用 5V 供电，AO 电压最高可达 5V，
    远超量程（既读不准，也可能损伤引脚）。稳妥做法二选一：
      1) 把模块 VCC 改接开发板的 3.3V——最省事，灵敏度略降；
      2) 在 AO 与 GPIO 之间加电阻分压，把电压压到 2.9V 以内。
    """
    def __init__(self, pin):
        # 数据手册说明 ADC2 与 Wi-Fi 冲突，故 pin 必须取自 ADC1（GPIO1~GPIO10）
        self.adc = ADC(Pin(pin))
        # ATTN_11DB 对应手册的 ATTN3 档，满量程约 2.9V，读取值为 0~4095
        self.adc.atten(ADC.ATTN_11DB)

    def read(self):
        """返回 ADC 原始值 0~4095，值越大空气质量越差"""
        try:
            return self.adc.read()
        except OSError:
            return None


class Relay:
    """继电器模块（1 路，低电平触发）—— 控制 5V USB 小风扇

    低电平触发含义: IN 脚给 0 时继电器吸合（风扇开），给 1 时断开。
    RELAY_ACTIVE_LOW = False 时逻辑反过来（高电平触发模块）。
    """
    def __init__(self, pin, active_low=None):
        self.active_low = config.RELAY_ACTIVE_LOW if active_low is None else active_low
        # 初始电平直接设为"关闭"对应的值，避免上电瞬间风扇乱转
        self.pin = Pin(pin, Pin.OUT, value=self._level(False))
        self._state = False

    def _level(self, on):
        """把逻辑开关状态换算成实际要输出的电平"""
        if self.active_low:
            return 0 if on else 1
        return 1 if on else 0

    def on(self):
        self.pin.value(self._level(True))
        self._state = True

    def off(self):
        self.pin.value(self._level(False))
        self._state = False

    def set(self, value):
        """value 为 1/True 表示开，0/False 表示关"""
        if value:
            self.on()
        else:
            self.off()

    def state(self):
        """返回逻辑状态: 1 = 风扇开, 0 = 风扇关"""
        return 1 if self._state else 0


class Buzzer:
    """有源蜂鸣器模块（3 引脚，低电平触发，S8850 三极管驱动）

    低电平触发含义: I/O 脚给 0 时鸣叫。有源蜂鸣器内部自带震荡电路，
    通电即发声，不需要 PWM 驱动，所以直接用 Pin 开关即可。
    """
    def __init__(self, pin, active_low=None):
        self.active_low = config.BUZZER_ACTIVE_LOW if active_low is None else active_low
        # 初始电平设为"静音"，避免上电就一直响
        self.pin = Pin(pin, Pin.OUT, value=self._level(False))
        self._state = False

    def _level(self, on):
        if self.active_low:
            return 0 if on else 1
        return 1 if on else 0

    def on(self):
        """开始持续鸣叫（一直响，直到调用 off）"""
        self.pin.value(self._level(True))
        self._state = True

    def off(self):
        """停止鸣叫"""
        self.pin.value(self._level(False))
        self._state = False

    def state(self):
        """返回逻辑状态: 1 = 正在鸣叫, 0 = 静音"""
        return 1 if self._state else 0

    def beep(self, times=2, duration=0.2):
        """短促提示: 响 times 次，每次 duration 秒"""
        for _ in range(times):
            self.on()
            time.sleep(duration)
            self.off()
            time.sleep(duration)
