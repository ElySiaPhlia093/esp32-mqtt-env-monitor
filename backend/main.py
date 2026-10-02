# ============================================================
# FastAPI 入口
# 车间环境智能监测与控制系统 —— 后端服务
#
# 启动方式:
#   cd backend
#   pip install -r requirements.txt
#   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# 浏览器访问: http://localhost:8000/docs  (API 文档)
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from database import init_db
from routers import data, alerts, control
import scheduler

app = FastAPI(
    title="车间环境智能监测与控制系统",
    description="基于 ESP32-S3 + MQTT + OneNET 的车间环境监测与远程控制系统",
    version="1.0.0",
)

# 跨域（开发时前端 Vue 在不同端口访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(data.router)
app.include_router(alerts.router)
app.include_router(control.router)


@app.on_event("startup")
def on_startup():
    init_db()
    scheduler.start_scheduler()


@app.get("/")
def root():
    return {
        "project": "车间环境智能监测与控制系统",
        "docs": "/docs",
        "api": ["/api/data/latest", "/api/data/history",
                "/api/alerts", "/api/device/control"],
    }
