# ============================================================
# 数据库模块 —— SQLite 初始化与建表
# 用 SQLAlchemy 2.x
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import config

# SQLite 连接（check_same_thread=False 允许 FastAPI 多线程访问）
engine = create_engine(
    "sqlite:///" + config.DATABASE_PATH,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def init_db():
    """创建所有表"""
    import models  # noqa: F401  确保模型已注册
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
