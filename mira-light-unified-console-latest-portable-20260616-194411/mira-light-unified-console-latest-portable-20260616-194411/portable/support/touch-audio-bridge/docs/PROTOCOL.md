# HTTP API 协议

> bridge 暴露的 HTTP 接口规范。板上 dispatcher 按这个协议发触发。

---

## 端点总表

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 健康检查（同 `/v1/mira-light/status`）|
| GET | `/v1/mira-light/status` | 当前音频播放状态 |
| POST | `/v1/mira-light/trigger` | 触发事件（播 / 停）|
| POST | `/v1/mira-light/stop` | 直接停止当前音频 |

---

## 1. GET /health, GET /v1/mira-light/status

健康检查 + 当前状态。

### 请求

无 body。

### 响应

```json
{
  "ok": true,
  "audio": {
    "playing": false,
    "asset": null,
    "started_at": null,
    "elapsed_ms": 0,
    "assets_root": "/Users/.../audio-bridge/assets"
  }
}
```

正在播音频时：

```json
{
  "ok": true,
  "audio": {
    "playing": true,
    "asset": "speech/cute_robot_comfort.aiff",
    "started_at": 1779595645.158,
    "elapsed_ms": 1234,
    "assets_root": "/Users/.../audio-bridge/assets"
  }
}
```

---

## 2. POST /v1/mira-light/trigger

主入口。事件名决定行为。

### 请求 body

```json
{
  "event": "<event_name>",
  "payload": { ... }
}
```

支持的 `event` (大小写不敏感):

| event | 行为 |
|---|---|
| `long_touch_comfort` | 播 payload.asset_name |
| `comfort_sound` | 同上（别名）|
| `stop_comfort_sound` | 立即停 |
| `stop_comfort` | 同上（别名）|
| `comfort_stop` | 同上（别名）|

### 2a. event=long_touch_comfort

**触觉系统长按时板上 dispatcher 发的事件**。

```json
{
  "event": "long_touch_comfort",
  "payload": {
    "asset_name": "speech/cute_robot_comfort.aiff",
    "elapsed_ms": 1500,
    "deviceId": "mira-light-lamp"
  }
}
```

字段：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|
| `asset_name` | string | 否 | 音频路径（相对 assets/）。默认 `speech/cute_robot_comfort.aiff` |
| `elapsed_ms` | int | 否 | 触摸了多少 ms 才触发的（日志用）|
| `deviceId` | string | 否 | 设备 ID（日志用）|

**行为**：
1. 如果当前正在播 → 先停（避免叠音）
2. 解析 asset_name 到本地路径
3. 路径必须在 assets_root 下（防 path traversal）
4. spawn `afplay <path>` 异步播放（不等待结束）
5. 返回结果

### 响应（成功）

```json
{
  "ok": true,
  "event": "long_touch_comfort",
  "asset": "speech/cute_robot_comfort.aiff",
  "elapsed_ms": 1500,
  "audio": {
    "ok": true,
    "asset": "speech/cute_robot_comfort.aiff",
    "path": "/Users/.../audio-bridge/assets/speech/cute_robot_comfort.aiff",
    "pid": 26779,
    "started_at": 1779595645.158
  }
}
```

### 响应（asset 不存在）

```json
{
  "ok": false,
  "event": "long_touch_comfort",
  "error": "asset_not_found",
  "detail": "asset not found: /Users/.../assets/speech/whatever.aiff"
}
```

HTTP 状态码 400。

### 响应（路径穿越攻击）

```json
{
  "ok": false,
  "event": "long_touch_comfort",
  "error": "asset path escapes assets root: ../../../etc/passwd"
}
```

HTTP 状态码 400。

### 2b. event=stop_comfort_sound

**触觉系统 release 时板上 dispatcher 发的事件**。立即停止当前播放的音频。

```json
{
  "event": "stop_comfort_sound",
  "payload": {
    "release_reason": "absence",
    "deviceId": "mira-light-lamp"
  }
}
```

字段：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|
| `release_reason` | string | 否 | 释放原因（debounced / absence / watchdog）|

### 响应

```json
{
  "ok": true,
  "stopped": true,
  "ts": 1779595645.576,
  "event": "stop_comfort_sound",
  "release_reason": "absence"
}
```

`stopped`:
- `true` —— 之前正在播，已停
- `false` —— 没在播（idempotent，不报错）

---

## 3. POST /v1/mira-light/stop

直接停止当前播放（不需要事件包装）。

### 请求 body

可空。

### 响应

```json
{
  "ok": true,
  "audio": {
    "ok": true,
    "stopped": true,
    "ts": 1779595645.576
  }
}
```

---

## 错误响应统一格式

```json
{
  "ok": false,
  "error": "<error_code>",
  "detail": "<human readable>"
}
```

| HTTP code | error | 何时 |
|---|---|---|
| 400 | `event is required` | trigger 缺 event |
| 400 | `invalid JSON body` | body 不是合法 JSON |
| 400 | `asset_not_found` | asset 路径不存在 |
| 400 | `unsupported_event` | event name 不识别 |
| 404 | `not_found` | 路径不存在的端点 |
| 500 | `internal` | bridge 内部异常 |

---

## 跟板上 dispatcher 的协议契约

板上 `touch_dispatcher.py` 在两个时机会调用本 bridge：

### A. 触摸时长跨越 threshold_ms 时

```python
# 来源: board-files/touch_dispatcher.py 中 _animator_loop
if elapsed_ms >= cs.get("threshold_ms", 1200) and not self._comfort_sound_fired:
    self._comfort_sound_fired = True
    requests.post(
        cs["bridge_url"],
        json={
            "event": cs.get("event_name", "long_touch_comfort"),
            "payload": {
                "asset_name": cs.get("asset_name", "speech/cute_robot_comfort.aiff"),
                "elapsed_ms": elapsed_ms,
                "deviceId": "mira-light-lamp"
            }
        },
        timeout=cs.get("post_timeout_ms", 1500) / 1000.0
    )
```

### B. release 后（如果 comfort_sound 已触发过）

```python
# 来源: board-files/touch_dispatcher.py 中 release 处理
if self._comfort_sound_fired:
    requests.post(
        cs["bridge_url"],
        json={
            "event": "stop_comfort_sound",
            "payload": {
                "release_reason": release_reason,
                "deviceId": "mira-light-lamp"
            }
        },
        timeout=cs.get("post_timeout_ms", 1500) / 1000.0
    )
    self._comfort_sound_fired = False
```

---

## 板上 mapping 配置示意

```json
"comfort_sound": {
  "enabled": true,
  "threshold_ms": 1200,
  "bridge_url": "http://192.168.0.46:9783/v1/mira-light/trigger",
  "event_name": "long_touch_comfort",
  "asset_name": "speech/cute_robot_comfort.aiff",
  "post_timeout_ms": 1500
}
```

注意：板上 dispatcher 发的 POST 不带 token，不带签名——LAN 内是受信网络。

---

## 后续扩展点（如果将来加事件）

加新事件名只需在 `audio_bridge_server.py` 的 `handle_trigger()` 添 elif 分支。例：

```python
elif event_key == "short_tap_chime":
    # 短按时播一个清脆的"叮"
    return _play(player, "sfx/tap_chime.aiff", payload)
```

跟板上协议保持一致即可（板上 dispatcher 改 mapping 加新触发逻辑）。

---

## curl 速查

```bash
# 健康
curl -s http://127.0.0.1:9783/health

# 触发默认音频
curl -X POST http://127.0.0.1:9783/v1/mira-light/trigger \
  -H "Content-Type: application/json" \
  -d '{"event":"long_touch_comfort"}'

# 触发指定音频
curl -X POST http://127.0.0.1:9783/v1/mira-light/trigger \
  -H "Content-Type: application/json" \
  -d '{"event":"long_touch_comfort","payload":{"asset_name":"speech/sigh_demo_host.aiff"}}'

# 停
curl -X POST http://127.0.0.1:9783/v1/mira-light/trigger \
  -H "Content-Type: application/json" \
  -d '{"event":"stop_comfort_sound"}'

# 跨主机测（在板子上执行，用 Mac IP）
ssh root@192.168.0.183 'curl -s http://192.168.0.46:9783/health'
```
