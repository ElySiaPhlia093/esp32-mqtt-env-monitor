# ============================================================
# OneNET 平台 API 封装
# 从 OneNET 拉取设备最新属性 / 历史数据
# ============================================================

import requests

import config


def get_latest_property():
    """获取设备最新属性值
    返回示例: {"temp": 29.5, "humidity": 60, "lux": 300, "air": 120, "relay": 0}
    """
    headers = {"Authorization": config.ONENET_TOKEN}
    params = {
        "product_id": config.PRODUCT_ID,
        "device_name": config.DEVICE_NAME,
    }
    try:
        res = requests.get(config.ONENET_PROPERTY_URL,
                           headers=headers, params=params, timeout=10)
        result = res.json()
        if result.get("code") != 0:
            print("[OneNET] 查询失败:", result.get("msg"))
            return None
        data = {}
        for item in result.get("data", []):
            idf = item.get("identifier")
            val = item.get("value")
            if val is None:
                continue
            # 【重要】OneNET 返回的数值是字符串（如 "27"、"false"），必须转换：
            # 否则 relay 用 bool("false") 会得到 True，数值也会以文本存进库
            if idf == "relay":
                data[idf] = str(val).lower() in ("true", "1")
            else:
                try:
                    data[idf] = float(val)
                except (TypeError, ValueError):
                    pass
        return data
    except requests.exceptions.RequestException as e:
        print("[OneNET] 网络异常:", e)
        return None


def get_history(identifier, start_ms, end_ms, page_size=100):
    """获取某个属性的历史数据
    返回: [{"time": 毫秒时间戳, "value": x}, ...]
    """
    headers = {"Authorization": config.ONENET_TOKEN}
    params = {
        "product_id": config.PRODUCT_ID,
        "device_name": config.DEVICE_NAME,
        "identifier": identifier,
        "start_time": start_ms,
        "end_time": end_ms,
        "page_size": page_size,
    }
    try:
        res = requests.get(config.ONENET_HISTORY_URL,
                           headers=headers, params=params, timeout=10)
        result = res.json()
        if result.get("code") != 0:
            return []
        return result.get("data", {}).get("list", [])
    except requests.exceptions.RequestException as e:
        print("[OneNET] 历史数据请求异常:", e)
        return []
