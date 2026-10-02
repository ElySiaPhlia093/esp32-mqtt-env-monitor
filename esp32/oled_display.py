# ============================================================
# OLED 显示模块（可选）
# 在 ESP32 上实时显示当前环境数据
# 需要 OLED 0.96寸 SSD1306 屏幕（I2C 接口）
# I2C 总线由 main.py 创建后传入（与 BH1750 共用同一条总线）
# ============================================================

import ssd1306  # 已随本工程一同上传（非固件内置）


def _fmt(value):
    """空数据显示为 -- ，避免屏上出现 None"""
    return "--" if value is None else value


class OLEDDisplay:
    def __init__(self, i2c, addr=0x3C):
        self.enabled = False
        try:
            self.oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr)
            self.enabled = True
            print("[OLED] 初始化成功")
        except Exception as e:
            print("[OLED] 初始化失败（无屏幕或接线错误）:", e)

    def show(self, temp, humi, lux, air, relay_state, status):
        """在 OLED 上显示 4 行环境数据"""
        if not self.enabled:
            return
        self.oled.fill(0)
        self.oled.text("Temp:%s C" % _fmt(temp), 0, 0)
        self.oled.text("Humi:%s %%" % _fmt(humi), 0, 16)
        self.oled.text("Lux :%s" % _fmt(lux), 0, 32)
        self.oled.text("Air :%s" % _fmt(air), 0, 48)
        self.oled.show()
