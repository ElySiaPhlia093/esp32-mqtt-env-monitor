# OneNET 平台配置说明

> 本项目的 ESP32-S3 通过 MQTT 协议连接 OneNET 平台，后端通过 HTTP API 拉取数据。
> 平台地址：<https://open.iot.10086.cn>

## 第一步：创建 MQTT 产品

1. 打开 <https://open.iot.10086.cn> 登录（没有账号先注册）
2. 进入**开发者中心** → **创建产品**
3. 填写产品信息：

   - 产品名称：车间环境智能监测（或自定义）

   - 产品分类：工业互联网 / 智慧工厂

   - **接入协议：MQTT** ⚠️（重要！不要选 HTTP）
4. 创建成功后，记下**产品 ID**（形如 `xxxxxxxx` 的一串字符）

## 第二步：添加设备

1. 进入刚创建的产品 → **设备列表** → **添加设备**
2. 设备名称：`temp_humi`（要和 `esp32/config.py` 里的 `DEVICE_NAME` 一致）
3. 添加后记下**产品 ID** 和**设备名称**

> 只需要**一台**设备就够：OneNET 的物模型是定义在**产品**上的，同一台设备就能承载
> temp/humidity/lux/air/relay 全部 5 个属性，不必每类传感器各建一台设备。

### MQTT 接入参数（实测确认）

| 参数 | 取值 |
| ---- | ---- |
| 服务器地址 | `mqtts.heclouds.com`（**注意结尾多个 s**；`mqtt.heclouds.com:1883` 会连接超时） |
| 端口 | `1883` |
| clientId | **设备名**（是设备名，不是 `产品ID_设备名`） |
| username | **产品 ID** |
| password | **产品级 Token**（见第四步），不是"设备密钥" |

## 第三步：配置物模型（属性）

在产品的**物模型/功能定义**里添加以下属性：

| 功能名称  | 标识符 identifier | 数据类型  | 读写类型         |
| ----- | -------------- | ----- | ------------ |
| 温度    | temp           | float | 只读           |
| 湿度    | humidity       | float | 只读           |
| 光照强度  | lux            | int   | 只读           |
| 空气质量  | air            | int   | 只读           |
| 继电器开关 | relay          | bool  | **读写**（支持下发） |

> ⚠️ `relay` 必须设为**读写**，否则后端无法下发远程控制指令。
> 属性名必须和代码里的完全一致（temp/humidity/lux/air/relay）。

## 第四步：生成 Token（设备端与后端共用同一个）

新版 OneNET 用的是**产品级 Token**：设备端拿它当 MQTT 密码，后端拿它做 HTTP API 的 Authorization 头。

生成规则（见官方文档《访问鉴权》）：

```
sign = base64( hmac_<method>( base64decode(产品AccessKey), StringForSignature ) )
StringForSignature = et + '\n' + method + '\n' + res + '\n' + version
```

- `version` 固定为 `2018-10-31`；`method` 可为 `md5` / `sha1` / `sha256`
- `res` 必须是**产品级** `products/{产品ID}` —— 若写成 `products/{产品ID}/devices/{设备名}` 会返回 invalid authorization
- `et` 为过期时间戳（Unix 秒）
- **产品 AccessKey 要先 `base64decode` 再参与 HMAC**，否则签名算不对

生成脚本（用后端的 venv 跑即可）：

```python
import base64, hashlib, hmac, urllib.parse as up

PRODUCT_ID = "你的产品ID"
ACCESS_KEY = "你的产品AccessKey"
ET = 1920556800          # 过期时间戳，自己按需改
RES = "products/" + PRODUCT_ID

sfs = str(ET) + "\n" + "md5" + "\n" + RES + "\n" + "2018-10-31"
sign = base64.b64encode(
    hmac.new(base64.b64decode(ACCESS_KEY), sfs.encode(), hashlib.md5).digest()
).decode()
token = "version=2018-10-31&res=%s&et=%s&method=md5&sign=%s" % (
    up.quote(RES, safe=""), ET, up.quote(sign, safe=""))
print(token)
```

把生成的 Token 同时填到 `esp32/config.py` 和 `backend/config.py` 的 `ONENET_TOKEN`。

## 第五步：验证

1. 跑起 ESP32，串口应依次输出 `[WiFi] 连接成功` → `[MQTT] 连接 OneNET 成功`
2. 平台 → 设备详情 → **物模型数据**，可看到 temp/humidity/lux/air/relay 实时更新
3. 平台 → **设备命令 / 属性设置**，手动下发 `relay=true`，观察 ESP32 继电器是否动作

> 若上报后平台查不到数据，可订阅回复主题
> `$sys/{产品ID}/{设备名}/thing/property/post/reply`
> 查看平台对上报报文的真实校验结果。
> 例如 `{"code":2306,"msg":"identifier not exist:identifier:status"}`
> 表示上报了物模型里没有定义的属性，整条报文会被拒绝。

## 第六步：远程控制（属性下发）链路

看板"远程控制"页点下按钮后的完整链路：

```
Vue 看板 → FastAPI(control.py) → OneNET HTTP API(设置设备属性)
        → 平台 MQTT 下发 → ESP32 执行 → 回 set_reply → 平台返回结果
```

### 链路上三个关键点（均为实测结论）

**1. 后端下发的 `params` 必须"值直传"**

```json
{"product_id": "产品ID", "device_name": "设备名", "params": {"relay": true}}
```

若写成 `{"relay": {"value": true}}`，平台返回
`{"code":10411,"msg":"属性设置失败:identifier: relay, error: bool type error"}`。

> 注意区分方向：设备**上报**数据时用 `{"params": {"relay": {"value": true}}}`（见第三步、第五步）；
> 而后端**下发**设置时是 `{"params": {"relay": true}}`，两者格式不同。

**2. 设备收到 `property/set` 后必须回复 `set_reply`**

| 方向      | Topic                                                    |
| ------- | -------------------------------------------------------- |
| 平台 → 设备 | `$sys/{产品ID}/{设备名}/thing/property/set`                    |
| 设备 → 平台 | `$sys/{产品ID}/{设备名}/thing/property/set_reply`              |

回复报文必须带回平台下发的 `id`：

```json
{"id": "平台下发的id", "code": 200, "msg": "success"}
```

不回则平台一直等到超时，接口返回 `10411 设备响应超时`，看板上会显示"指令下发失败"。

**3. 设备主循环不能整段 `sleep`**

`check_msg()` 若只在每个上报周期（10 秒）开头调用一次，平台下发后最多要等 10 秒才被处理，
很容易超出平台等待窗口而超时。正确做法是把等待拆成 1 秒一跳、期间持续轮询下行指令，
见 `esp32/main.py` 主循环第 8 步。

> 另外，设备端解析下行报文时要兼容两种格式：新版是 `{"relay": true}`（值直传），
> 老版是 `{"relay": {"value": true}}`，只按老格式写会在 `bool` 上调用 `.get()` 报
> `'bool' object has no attribute 'get'`。

## 常见问题

| 问题                            | 原因                                        | 解决                                                        |
| ----------------------------- | ----------------------------------------- | --------------------------------------------------------- |
| `mqtt.heclouds.com` 连接超时      | 接入地址写错                                    | 改成 `mqtts.heclouds.com`（结尾多个 s）                           |
| MQTT 返回码 4（用户名或密码错误）          | 密码类型或 clientId 格式不对                       | clientId 用**设备名**、password 用**产品级 Token**、`res` 必须是 `products/{产品ID}` |
| 用平台生成的 Token 仍返回码 4           | 平台生成器给的 `res` 带了 `/devices/{设备名}`       | 按第四步用产品 AccessKey 自行生成（`res` 用产品级）                         |
| 上报成功但平台无数据                    | 上报了物模型未定义的属性                              | 只上报 temp/humidity/lux/air/relay；多传（如 `status`）会导致整条被拒       |
| 后端读到的 relay 恒为 true          | OneNET 返回值是字符串 `"false"`                  | 后端 `onenet_service.py` 已做类型转换，勿删除该转换逻辑                    |
| 远程控制无效                        | relay 属性没设成"读写"                           | 物模型改为读写并重新发布                                              |
| 下发返回 `10411 bool type error`    | 后端 `params` 把值包成了 `{"value": true}`        | 改成值直传 `{"relay": true}`（见第六步）                             |
| 下发返回 `10411 设备响应超时`           | 设备没回 `set_reply`，或下行轮询不及时                 | 收到 set 后回复 set_reply；主循环拆成 1 秒一跳轮询（见第六步）                 |
| 看板点"开启通风"后风扇又被关掉             | 本地自动控制在"环境正常"分支里执行了 `relay.off()`         | 已加 `manual_hold`：远程操作后环境正常时不强制关，出现报警自动控制重新接管             |
| 设备一直离线                        | 上报间隔内没有数据                                 | 检查 WiFi 是否连上、MQTT 是否成功                                     |

