# ============================================================
# 断网缓存模块
# 当 MQTT 连接断开时，把数据写到本地 Flash 文件，
# 网络恢复后自动补传，保证数据不丢失（工业级可靠性设计）
# ============================================================

import json
import os

CACHE_FILE = "cache.json"
MAX_CACHE = 200  # 最多缓存 200 条，防止 Flash 写满


def save_cache(data):
    """断网时保存一条数据到本地"""
    records = load_cache()
    records.append(data)
    # 只保留最近 MAX_CACHE 条
    if len(records) > MAX_CACHE:
        records = records[-MAX_CACHE:]
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(records, f)
        print("[缓存] 已保存 1 条数据到本地，当前缓存: %d 条" % len(records))
    except OSError as e:
        print("[缓存] 写入失败:", e)


def load_cache():
    """读取本地缓存"""
    try:
        if CACHE_FILE in os.listdir("/"):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    return []


def get_cache_count():
    return len(load_cache())


def clear_cache():
    """清除本地缓存"""
    try:
        if CACHE_FILE in os.listdir("/"):
            os.remove(CACHE_FILE)
    except OSError:
        pass


def dump_cache():
    """返回缓存内容并清空（补传成功后调用）"""
    records = load_cache()
    clear_cache()
    return records
