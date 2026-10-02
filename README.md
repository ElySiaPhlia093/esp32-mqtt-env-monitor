# 车间环境智能监测与控制系统

基于 **ESP32-S3-N16R8（模组 ESP32-S3-WROOM-1-N16R8，双 Type-C 接口）+ MicroPython + MQTT + OneNET + FastAPI + Vue3** 的车间环境智能监测与远程控制系统。

## 系统架构

```
┌────────────────────────────────────────────────┐
│  ESP32-S3-N16R8 开发板（MicroPython）           │
│  DHT11(温湿度) GY-302/BH1750(光照) MQ-135(空气) │
│  OLED(现场显示) 继电器+5V风扇 有源蜂鸣器          │
│  ├─ 本地自动控制: 温度/湿度/空气超限 → 继电器开风扇+蜂鸣器持续报警 │
│  ├─ 断网缓存: 数据存 Flash，恢复后补传           │
│  └─ MQTT 上报 + 订阅远程控制指令                 │
└────────────────────┬───────────────────────────┘
                     │ MQTT
┌────────────────────▼───────────────────────────┐
│  OneNET 云平台（物模型: temp/humidity/lux/air/  │
│  relay）                                       │
└────────────────────┬───────────────────────────┘
                     │ HTTP API（每30秒拉取）
┌────────────────────▼───────────────────────────┐
│  FastAPI 后端（Python + SQLite）                │
│  数据同步 / 告警判断 / 控制指令下发               │
└────────────────────┬───────────────────────────┘
                     │ REST API
┌────────────────────▼───────────────────────────┐
│  Vue3 Web 看板（实时概览/历史趋势/告警/远程控制） │
└────────────────────────────────────────────────┘
```

## 目录结构

```
车间环境智能监测系统/
├── esp32/            # ESP32-S3 端 MicroPython 代码
│   ├── config.py     #   配置（WiFi/OneNET/引脚/触发极性/阈值）
│   ├── main.py       #   主程序
│   ├── sensors.py    #   传感器驱动
│   ├── mqtt_client.py#   OneNET MQTT 通信
│   ├── cache.py      #   断网缓存
│   ├── oled_display.py # OLED 显示（可选）
│   ├── ssd1306.py    #   OLED 驱动（非固件内置，必须上传）
│   └── umqtt/        #   MQTT 客户端库
├── backend/          # FastAPI 后端
│   ├── main.py       #   服务入口
│   ├── config.py     #   后端配置
│   ├── models.py     #   数据库模型
│   ├── scheduler.py  #   定时同步+告警
│   ├── onenet_service.py # OneNET API 封装
│   └── routers/      #   API 路由
├── frontend/         # Vue3 前端看板
│   └── src/views/    #   4 个页面
├── docs/             # 文档（采购/平台配置/部署）
└── start_all.bat     # 一键启动前后端（Windows，双击运行）
```

## 快速开始

> **第一步（必须）**：出于安全考虑，本仓库**不包含真实密钥**，请先复制配置模板并填入自己的信息：
>
> ```bash
> copy esp32\config.example.py   esp32\config.py
> copy backend\config.example.py backend\config.py
> ```
>
> 然后按 [docs/OneNET平台配置.md](docs/OneNET平台配置.md) 填好 WiFi 名称/密码、产品ID、设备名和产品级 Token。
> （`config.py` 已在 `.gitignore` 中，你的密钥不会被提交到仓库。）

1. 看 [docs/采购清单.md](docs/采购清单.md) 采购硬件
2. 看 [docs/OneNET平台配置.md](docs/OneNET平台配置.md) 配置云平台
3. 看 [docs/部署文档.md](docs/部署文档.md) 部署全流程
4. 前后端依赖装好后，双击 `start_all.bat` 一键启动，浏览器访问 <http://localhost:5173>

> `start_all.bat` 保存为 **GBK + CRLF** 编码（Windows 批处理要求），修改时不要另存为 UTF-8。

## 功能特性

- ✅ 多传感器环境采集（温度/湿度/光照/空气质量）

- ✅ MQTT 协议上云（OneNET 平台）

- ✅ 本地自动控制（温度/湿度/空气超限自动开风扇 + 蜂鸣器**持续报警**，环境恢复自动停止）

- ✅ 断网缓存补传（数据零丢失，工业级可靠性）

- ✅ 云端远程控制（Web 看板一键开关继电器，指令经 OneNET 下行、设备回执确认）

- ✅ 历史数据趋势图（ECharts 可视化）

- ✅ 告警记录管理（触发/确认/解决）

- ✅ 控制日志审计

