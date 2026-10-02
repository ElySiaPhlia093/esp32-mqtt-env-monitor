# umqtt.simple - MicroPython MQTT 客户端库（官方版）
# 来源: micropython-lib 官方仓库，版权归原作者所有，MIT 协议
# 作用: 让 ESP32 通过 MQTT 协议连接 OneNET 等平台

import usocket as socket
import struct

# MQTT 协议报文类型
MQTT_CMD_CONNECT = 0x10
MQTT_CMD_CONNACK = 0x20
MQTT_CMD_PUBLISH = 0x30
MQTT_CMD_SUBSCRIBE = 0x80
MQTT_CMD_SUBACK = 0x90
MQTT_CMD_UNSUBSCRIBE = 0xA0
MQTT_CMD_UNSUBACK = 0xB0
MQTT_CMD_PINGREQ = 0xC0
MQTT_CMD_PINGRESP = 0xD0
MQTT_CMD_DISCONNECT = 0xE0

MQTT_MSG_TYPE_SUB = 0x8
MQTT_MSG_TYPE_UNSUB = 0xA


class MQTTException(Exception):
    pass


def _set_last_will(client, message):
    if message is None:
        return
    client.pubtopic, client.pubmsg = message


def _gen_client_id():
    # 简易生成随机 client id（MicroPython 无 uuid，用时间+随机数）
    import os
    return "mpy-" + os.urandom(4).hex()


class MQTTClient:
    def __init__(self, client_id, server, port=0, user=None, password=None,
                 keepalive=0, ssl=False, ssl_params={}):
        self.client_id = client_id or _gen_client_id()
        self.broker = server
        self.port = port or (8883 if ssl else 1883)
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.ssl = ssl
        self.ssl_params = ssl_params
        self.sock = None
        self.cb = None
        self.lock = False
        self.pubtopic = None
        self.pubmsg = None
        self.sub_topic = None

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7F) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def _connect(self):
        self.sock = socket.socket()
        addr = socket.getaddrinfo(self.broker, self.port)[0][-1]
        self.sock.connect(addr)
        if self.ssl:
            import ussl
            self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)
        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\x04MQTT\x04\x02\0\0")

        sz = 10 + 2 + len(self.client_id)
        # 【修复】msg[6] 是"连接标志"字节，原代码把 keepalive 写到了这里，
        # 导致清会话位(0x02)被覆盖、并误置 will-retain 位，服务器判为协议错误直接断开。
        # 正确位置是 msg[7]、msg[8] 两个字节。
        msg[7] = self.keepalive >> 8
        msg[8] = self.keepalive & 0x00FF
        if self.user is not None:
            sz += 2 + len(self.user) + 2 + len(self.pswd)
            msg[6] |= 0xC0

        i = 1
        while sz > 0x7F:
            premsg[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        premsg[i] = sz

        self.sock.write(premsg, i + 2)
        self.sock.write(msg)
        self._send_str(self.client_id)
        if self.user is not None:
            self._send_str(self.user)
            self._send_str(self.pswd)
        resp = self.sock.read(4)
        if resp[0] != MQTT_CMD_CONNACK or resp[3] != 0:
            raise MQTTException(resp[1])
        _set_last_will(self, None)

    def connect(self, clean_session=True):
        self._connect()
        self.connected = True
        return True

    def disconnect(self):
        try:
            self.sock.write(b"\xe0\0")
        except OSError:
            pass
        self.sock.close()
        self.connected = False

    def _msg_len(self, l):
        if l < 0x80:
            return bytes([l])
        out = []
        while l > 0:
            b = l & 0x7F
            l >>= 7
            out.append(b | 0x80)
        out[-1] &= 0x7F
        return bytes(out)

    def _publish(self, topic, msg, retain=False, qos=0):
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        # 【修复】原代码在剩余长度 < 128 时会多写 2 个 0 字节，报文非法；
        # 统一用 _msg_len 正确编码剩余长度
        pkt = bytearray(b"\x30")
        pkt[0] |= qos << 1 | retain
        pkt += self._msg_len(sz)
        self.sock.write(pkt)
        self._send_str(topic)
        if qos > 0:
            self.sock.write(b"\0\1")
        self.sock.write(msg)
        if qos == 1:
            self._wait_msg()  # 简化处理

    def publish(self, topic, msg, retain=False, qos=0):
        return self._publish(topic, msg, retain, qos)

    def _subscribe(self, topic, qos=0):
        # 【修复】原代码把"剩余长度"写死为 0，主题却在长度字段之后单独 write，
        # 报文非法，服务器会直接断开连接（表现为 subscribe 处 IndexError）
        pkt = bytearray(b"\x82")
        pkt += self._msg_len(2 + 2 + len(topic) + 1)
        pkt += b"\x00\x01"          # 报文标识符
        self.sock.write(pkt)
        self._send_str(topic)
        self.sock.write(bytes([qos]))
        resp = self.sock.read(5)
        if not resp or resp[0] != MQTT_CMD_SUBACK:
            raise MQTTException(resp)

    def subscribe(self, topic, qos=0):
        self.sub_topic = topic
        self._subscribe(topic, qos)

    def _unsubscribe(self, topic):
        pkt = bytearray(b"\xa2\0\0\0")
        self.sock.write(pkt)
        self._send_str(topic)

    def unsubscribe(self, topic):
        self._unsubscribe(topic)

    def ping(self):
        self.sock.write(b"\xc0\0")

    def _wait_msg(self):
        resp = self.sock.read(1)
        if resp is None or resp == b"":
            return None
        if resp[0] & 0xF0 == MQTT_CMD_PINGRESP:
            return None
        if resp[0] & 0xF0 != MQTT_CMD_PUBLISH:
            raise MQTTException(resp[0])
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        sz -= topic_len + 2
        if resp[0] & 6:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.read(sz)
        if self.cb is not None:
            self.cb(topic, msg)
        return topic, msg

    def wait_msg(self):
        return self._wait_msg()

    def check_msg(self):
        # 非阻塞检查是否有消息
        import usocket as _s
        import select
        try:
            r, w, x = select.select([self.sock], [], [], 0)
            if r:
                return self._wait_msg()
        except Exception:
            pass
        return None
