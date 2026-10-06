# ============================================================
# 车间环境智能监测与控制系统 —— 后端配置【模板】
#
# 【使用方法】把本文件复制为 config.py，再填入你自己的 OneNET 信息。
#   config.py 已被 .gitignore 忽略，不会上传到仓库（避免密钥泄露）；
#   如果你只是 clone 本仓库，请务必先复制本模板，否则后端无法启动。
# ============================================================

# ---------- OneNET 平台配置（和 ESP32 端 config.py 保持一致） ----------
# 产品级 Token：后端调用 HTTP API 用它做 Authorization 头
# 生成规则：sign = base64(hmac_md5(base64decode(产品AccessKey), et\nmethod\nres\nversion))
#   res 必须是产品级 products/{产品ID}
# 生成脚本见 docs/OneNET平台配置.md 第四步
ONENET_TOKEN = "your_product_level_token"

PRODUCT_ID = "your_product_id"
DEVICE_NAME = "your_device_name"

# OneNET 查询接口地址（勿改）
ONENET_PROPERTY_URL = "https://iot-api.heclouds.com/thingmodel/query-device-property"
ONENET_HISTORY_URL = "https://iot-api.heclouds.com/thingmodel/query-device-property-history"
# 设备详情接口：用于获取设备在平台上的真实在线状态（勿改）
ONENET_DEVICE_DETAIL_URL = "https://iot-api.heclouds.com/device/detail"

# ---------- 数据同步配置 ----------
SYNC_INTERVAL_SECONDS = 30   # 每 30 秒从 OneNET 拉一次数据入库
HISTORY_QUERY_HOURS = 24     # 拉取最近 24 小时历史数据

# 在线状态判断（双保险）：
#   首选调用设备详情接口拿平台真实在线状态；若该接口异常，
#   则回退到“本地超时”——超过下面这个秒数没有新数据即判为离线。
ONLINE_TIMEOUT_SECONDS = 90

# 心跳补点：数据没变化时，每隔这么多秒也补存一条，
#   保证趋势图连续（仅在设备在线时生效，离线不会补）。
HEARTBEAT_SECONDS = 300   # 5 分钟

# ---------- 数据库 ----------
DATABASE_PATH = "monitor.db"

# ---------- 告警阈值（和 ESP32 端 config.py 保持一致） ----------
ALARM_TEMP_MAX = 35.0
ALARM_HUMI_MIN = 30.0
ALARM_HUMI_MAX = 85.0
ALARM_AIR_MAX = 4000     # MQ-135 用 3.3V 供电时基线约 3600，阈值需设在其上方
