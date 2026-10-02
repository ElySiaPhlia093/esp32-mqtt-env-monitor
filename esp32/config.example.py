# ============================================================
# 车间环境智能监测与控制系统 —— ESP32-S3 配置文件【模板】
# 开发板: ESP32-S3-N16R8（44 引脚，Xtensa LX7 双核 240MHz，512KB SRAM，384KB ROM）
#         模组 ESP32-S3-WROOM-1-N16R8（16MB SPI Flash / 8MB PSRAM），双 Type-C 接口
# 参考资料: 乐鑫《ESP32-S3 系列芯片技术规格书》v2.2
#
# 【使用方法】把本文件复制为 config.py，再填入你自己的 WiFi 与 OneNET 信息。
#   config.py 已被 .gitignore 忽略，不会上传到仓库（避免密钥泄露）；
#   如果你只是 clone 本仓库，请务必先复制本模板，否则程序会报 ImportError。
# ============================================================

# ---------- WiFi 配置（填你的 WiFi/手机热点） ----------
# ESP32-S3 无线规格: IEEE 802.11b/g/n，仅 2.4GHz，1T1R 最高 150Mbps
# 注意: 不支持 5GHz 频段，不要连 5GHz 的 WiFi
WIFI_SSID = "your_wifi_name"
WIFI_PASSWORD = "your_wifi_password"

# ---------- OneNET 平台配置 ----------
# 【实测结论】新版 OneNET 的 MQTT 接入用【产品级 Token】当密码，不需要设备密钥：
#   clientId = 设备名
#   username = 产品ID
#   password = 产品级 Token（见下面的 ONENET_TOKEN）
PRODUCT_ID = "your_product_id"          # 产品ID
DEVICE_NAME = "your_device_name"        # 设备名（平台上已存在的设备）

# 产品级 Token（由产品 AccessKey 生成，物模型/设备都在该产品下，多台设备通用）
# 生成规则：sign = base64(hmac_md5(base64decode(AccessKey), et\nmethod\nres\nversion))
#   其中 res 必须是【产品级】products/{产品ID}；et 为过期时间戳
# 生成脚本见 docs/OneNET平台配置.md 第四步
ONENET_TOKEN = "your_product_level_token"

# OneNET MQTT 服务器
# 【实测】新版 OneNET 的 MQTT 接入地址是 mqtts.heclouds.com（多一个 s）；
# 原来的 mqtt.heclouds.com 解析到 183.230.40.39，1883 端口连不上（超时）
MQTT_SERVER = "mqtts.heclouds.com"
MQTT_PORT = 1883

# ---------- 数据上报间隔（秒） ----------
UPLOAD_INTERVAL = 10

# ---------- 传感器引脚配置（ESP32-S3-N16R8 专用） ----------
# 【重要】按数据手册，以下引脚不要外接器件，接错会导致无法启动或数据异常：
#   GPIO26 ~ GPIO32 : SPI0/1 专用，连接模组内置 Flash 与 PSRAM
#   GPIO33 ~ GPIO37 : 八线(Octal) SPI 模式下的高 4 位数据线与 DQS，
#                     N16R8 的 8MB PSRAM 正是八线模式，故这 5 个脚同样被占用
#   GPIO19 / GPIO20 : USB_D- / USB_D+，USB 串口-JTAG 与 USB OTG 共用
#   GPIO43 / GPIO44 : U0TXD / U0RXD，串口0，下载与日志打印用
#   GPIO0 / GPIO3 / GPIO45 / GPIO46 : strapping 启动模式选择脚，不要占用
# 因此本设计统一使用 GPIO1~GPIO9，全部是安全可用的通用 IO

# DHT11 温湿度：DATA 脚接的 GPIO
DHT11_PIN = 4

# BH1750 光照 + SSD1306 OLED 共用 I2C 总线（SCL/SDA）
# 芯片内置 2 个 I2C 控制器，支持标准模式 100Kbit/s
I2C_SCL_PIN = 9
I2C_SDA_PIN = 8

# MQ-135 空气质量：AO 模拟输出接的 GPIO
# 芯片有 2 个 12 位 SAR ADC（ADC1/ADC2），共最多 20 个通道：
#   ADC1 = GPIO1~GPIO10（对应 ADC1_CH0~CH9）
#   ADC2 = GPIO11~GPIO20（对应 ADC2_CH0~CH9）
# 数据手册明确说明 ADC2 与 Wi-Fi 存在冲突，联网时必须用 ADC1，
# 所以这里选 GPIO1（即 ADC1_CH0）
MQ135_PIN = 1

# 继电器（控制风扇/排风）：IN 脚接的 GPIO
# 购买的继电器为【1路 低电平触发，工作电压 3.3V】
RELAY_PIN = 5

# 蜂鸣器（超限报警）：I/O 脚接的 GPIO
# 购买的有源蜂鸣器为【低电平触发，S8850 三极管驱动】
BUZZER_PIN = 6

# ---------- 触发方式配置 ----------
# True = 低电平触发（本次购买的模块就是这种，输出 0 才动作）
# False = 高电平触发（如果以后换成高电平模块，改成 False 即可）
RELAY_ACTIVE_LOW = True
BUZZER_ACTIVE_LOW = True

# ---------- ADC 量程说明（用于理解阈值） ----------
# 数据手册表 5-6：ESP32-S3 的 ADC 满量程由衰减档位决定
#   ATTN0  量程 0 ~ 850 mV
#   ATTN1  量程 0 ~ 1100 mV
#   ATTN2  量程 0 ~ 1600 mV
#   ATTN3（= MicroPython 的 ATTN_11DB）量程 0 ~ 2900 mV
# 程序采用 ATTN3，读取值 0~4095 对应约 0~2.9V。
# 注意 MQ-135 若用 5V 供电，AO 电压可能到 5V，必须分压后再接入。

# ---------- 超限告警阈值（车间场景） ----------
ALARM_TEMP_MAX = 35.0    # 温度超过 35℃ 告警 + 开风扇
ALARM_HUMI_MIN = 30.0    # 湿度低于 30% 告警（太干）
ALARM_HUMI_MAX = 85.0    # 湿度高于 85% 告警（太潮，开风扇排湿）
ALARM_AIR_MAX = 4000     # 空气质量 ADC 告警阈值（值越大越差，满量程 4095）
                         # 【临时值】MQ-135 目前 3.3V 供电，基线约 3600，
                         # 等改用 5V+分压 后重新标定，再改回合理值（如 2500）
