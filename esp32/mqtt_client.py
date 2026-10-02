# ============================================================
# OneNET MQTT 通信模块
# 负责: 连接 OneNET / 属性上报 / 订阅下行控制指令
# 数据格式参考 OneNET 官方物模型标准
# ============================================================

import json
import time
from umqtt.simple import MQTTClient

import config


class OneNETClient:
    def __init__(self):
        # 【实测】新版 OneNET MQTT 连接三要素:
        # client_id = 设备名（注意：不是"产品ID_设备名"）
        # username  = 产品ID
        # password  = 产品级 Token（不是设备密钥）
        self.client_id = config.DEVICE_NAME
        self.username = config.PRODUCT_ID
        self.password = config.ONENET_TOKEN

        self.client = None
        self.connected = False

        # 上报 topic（设备发数据到平台）
        self.report_topic = "$sys/%s/%s/thing/property/post" % (
            config.PRODUCT_ID, config.DEVICE_NAME)
        # 订阅 topic（平台下发指令给设备）
        self.set_topic = "$sys/%s/%s/thing/property/set" % (
            config.PRODUCT_ID, config.DEVICE_NAME)
        # 【实测】收到 property/set 后必须回复 set_reply，否则平台侧
        # "设置设备属性"接口会一直等到超时，返回 10411"设备响应超时"
        self.set_reply_topic = "$sys/%s/%s/thing/property/set_reply" % (
            config.PRODUCT_ID, config.DEVICE_NAME)

        self.on_command = None  # 回调函数: (payload_dict)

    def connect(self):
        """连接 OneNET，返回是否成功"""
        try:
            self.client = MQTTClient(
                self.client_id,
                config.MQTT_SERVER,
                port=config.MQTT_PORT,
                user=self.username,
                password=self.password,
                keepalive=60,
            )
            self.client.set_callback(self._on_message)
            self.client.connect()
            self.client.subscribe(self.set_topic)
            self.connected = True
            print("[MQTT] 连接 OneNET 成功")
            print("[MQTT] 上报 topic:", self.report_topic)
            return True
        except OSError as e:
            print("[MQTT] 连接失败:", e)
            self.connected = False
            return False

    def _on_message(self, topic, msg):
        """收到平台下发的控制指令"""
        try:
            data = json.loads(msg.decode())
            print("[MQTT] 收到下行指令:", data)
            if self.on_command:
                self.on_command(data)
            # 执行完必须回复平台，带上平台下发的 id
            self._reply_set(data)
        except ValueError:
            print("[MQTT] 指令解析失败:", msg)

    def _reply_set(self, data):
        """回复属性设置结果，payload 需带回平台下发的 id"""
        try:
            payload = {"id": data.get("id", "1"), "code": 200, "msg": "success"}
            self.client.publish(self.set_reply_topic, json.dumps(payload))
            print("[MQTT] 已回复 set_reply:", json.dumps(payload))
        except OSError as e:
            print("[MQTT] 回复 set_reply 失败:", e)

    def publish(self, property_dict):
        """上报属性数据 property_dict = {"temp": 29.5, "humidity": 60, ...}"""
        # OneNET 物模型格式:
        # {"id":"1","version":"1.0","params":{"temp":{"value":29.5},...}}
        params = {}
        for key, value in property_dict.items():
            if value is None:
                # 未接或读取失败的传感器不上报，避免平台校验失败
                continue
            params[key] = {"value": value}

        payload = {
            "id": str(int(time.time())),
            "version": "1.0",
            "params": params,
        }
        try:
            self.client.publish(self.report_topic, json.dumps(payload))
            print("[MQTT] 上报:", json.dumps(payload))
            return True
        except OSError as e:
            print("[MQTT] 上报失败:", e)
            self.connected = False
            return False

    def check_message(self):
        """检查是否有下行指令（主循环里周期性调用）"""
        if self.connected and self.client:
            try:
                self.client.check_msg()
            except OSError:
                self.connected = False

    def reconnect_if_needed(self):
        """掉线自动重连"""
        if not self.connected:
            print("[MQTT] 尝试重连...")
            time.sleep(3)
            self.connect()
