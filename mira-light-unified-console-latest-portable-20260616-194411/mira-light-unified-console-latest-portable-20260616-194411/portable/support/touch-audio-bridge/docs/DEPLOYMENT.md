# Audio Bridge 部署指南

> 怎么把这套 bridge 装到你的 Mac 上，让触觉系统能播音频。

---

## 前提

| 检查项 | 命令 |
|---|---|
| macOS（任意版本，10.14+ 都行）| `sw_vers` |
| Python 3.9+ | `python3 --version` |
| afplay 可用 | `command -v afplay` （macOS 自带）|
| 跟板子在同一 WiFi | `ping 192.168.0.183` |

如果 Python 没装：`xcode-select --install`

---

## 部署方法 A: 手动启动（最简单）

```bash
cd "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge"
./Start-Audio-Bridge.command
```

或者双击 Finder 里的 `Start-Audio-Bridge.command`。

留着这个终端窗口（关了 bridge 也会停）。

---

## 部署方法 B: 后台 launchd 自启（推荐长期运行）

让 bridge 跟随 Mac 用户登录自启，崩了自动重启。

### Step 1: 编辑 plist

```bash
# 用 TextEdit 打开模板
open -e "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge/launchd/com.miralight.audio-bridge.plist"
```

把里面的 `YOUR_USERNAME` **替换成你的实际 Mac 用户名**（用 `whoami` 查）。需要改 2 处：
- `<string>/Users/YOUR_USERNAME/.../audio_bridge_server.py</string>`
- `<string>/Users/YOUR_USERNAME/.../audio-bridge</string>` (WorkingDirectory)

### Step 2: 装到 LaunchAgents

```bash
cp "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge/launchd/com.miralight.audio-bridge.plist" \
   ~/Library/LaunchAgents/
```

### Step 3: 加载启动

```bash
launchctl load ~/Library/LaunchAgents/com.miralight.audio-bridge.plist
```

### Step 4: 验证

```bash
# 看是否在跑
launchctl list | grep miralight
# 期望看到一行：PID  0  com.miralight.audio-bridge

# 测端点
curl -s http://127.0.0.1:9783/health | python3 -m json.tool

# 看日志
tail -f /tmp/mira-audio-bridge.log
```

### 卸载（如果想关）

```bash
launchctl unload ~/Library/LaunchAgents/com.miralight.audio-bridge.plist
rm ~/Library/LaunchAgents/com.miralight.audio-bridge.plist
```

---

## 部署方法 C: tmux / screen 长会话（适合开发环境）

```bash
# 一次性启 tmux 会话
tmux new -d -s audio-bridge \
  'cd "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge" && ./Start-Audio-Bridge.command'

# 进去看日志
tmux attach -t audio-bridge

# Ctrl-b d 退出但不关
# 停掉
tmux kill-session -t audio-bridge
```

---

## 端到端联调（部署后必做）

### Step 1: 确认 bridge 在跑

```bash
curl -s http://127.0.0.1:9783/health
# 应该返回 {"ok":true,...}
```

### Step 2: 手动触发一次音频

```bash
curl -X POST http://127.0.0.1:9783/v1/mira-light/trigger \
  -H "Content-Type: application/json" \
  -d '{"event":"long_touch_comfort","payload":{"asset_name":"speech/cute_robot_comfort.aiff","elapsed_ms":1500}}'
```

**期望**：Mac 立即播放 cute_robot_comfort 这段语音。

### Step 3: 查 Mac IP

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
# 找到 192.168.0.X 那行（同板子的子网）
```

记住这个 IP，比如 `192.168.0.46`。

### Step 4: 改板上 mapping 的 bridge_url

```bash
# 本地改 board-files/touch_mapping.json
# 把 comfort_sound.bridge_url 改成 http://<你的 Mac IP>:9783/v1/mira-light/trigger

# 上传
scp "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/board-files/touch_mapping.json" \
    root@192.168.0.183:/home/sunrise/Desktop/

# 重启 dispatcher 让新配置生效
ssh root@192.168.0.183 'systemctl restart mira-touch'
```

### Step 5: 摸 Mira 灯头 ≥1.2 秒

期望：
1. Mira 用舵机蹭蹭（板上动作）
2. **Mac 同时响起 cute_robot_comfort 语音**
3. 你松手 → 动作回归 + 语音立即停（v16 行为）

如果只有动作没有声音：
- bridge 没启 / Mac IP 改错 / 网络隔离
- 看 bridge 日志：`tail -f /tmp/mira-audio-bridge.log` 看有没有 POST 进来
- 看 dispatcher 日志：`ssh root@192.168.0.183 'tail -f /var/log/mira-touch.log'` 找 `comfort_sound`

---

## 网络拓扑提醒

```
板子 192.168.0.183 ──┐                  ┌─→ Mac 192.168.0.46
                     │                  │
                     └── 5G WiFi 热点 ──┘
                          (192.168.0.x)
```

如果你 Mac 切到别的 WiFi，板子访问不了 Mac → 音频不响。**保持 Mac 在 5G WiFi 网络**。

如果 Mac 装了 VPN 拦截 LAN → 同样问题。临时关 VPN 或加 LAN 例外。

---

## 防火墙

macOS 默认防火墙可能阻挡入站连接。第一次启动时如果弹出"是否允许 python3 接受网络连接"，**点允许**。

或者预先添加规则：

```bash
# 允许 python3 监听（需要 sudo）
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3
```

---

## 端口冲突

如果 9783 被占用（最常见原因：你也在跑 Mira-Light-Voice-Full-Ready）：

```bash
# 查谁占用
lsof -i :9783

# 选 A：换本 bridge 端口（如 9788）
# 编辑 bridge_config.json:  "listenPort": 9788
# 同步改 board-files/touch_mapping.json:  "bridge_url": "http://<MAC_IP>:9788/v1/mira-light/trigger"
# 上传、重启 mira-touch

# 选 B：杀掉旧 bridge
kill $(lsof -ti :9783)
```

---

## 多 Mac 场景（如果有备用 Mac）

每台 Mac 独立部署即可。板上 `touch_mapping.json` 的 `bridge_url` 同时只能指向一台。要切就改 JSON 上传。

或者写个 router：板上 dispatcher 对多台 Mac 都发触发，谁回应快用谁——但这超出了 v14 的复杂度，没做。

---

## 验证 checklist

部署完后跑一遍：

- [ ] `curl http://127.0.0.1:9783/health` 返回 ok
- [ ] 手动 POST trigger，本地能播音频
- [ ] 在板上 `curl http://<MAC_IP>:9783/health` 也能通（跨主机）
- [ ] `scp` 更新过的 mapping 上去，`systemctl restart mira-touch`
- [ ] 摸 Mira ≥ 1.2s → 听到声音
- [ ] 松手 → 声音立即停
- [ ] 重启 Mac → 用 launchd 部署的话 bridge 自动起

全过 ✅ → 部署完成。

---

## 卸载

```bash
# 停 launchd（如果用了）
launchctl unload ~/Library/LaunchAgents/com.miralight.audio-bridge.plist
rm ~/Library/LaunchAgents/com.miralight.audio-bridge.plist

# 关 comfort_sound（让板上不再尝试触发，避免日志一堆 POST 失败）
# 改 board-files/touch_mapping.json:  "comfort_sound": { "enabled": false }
scp board-files/touch_mapping.json root@192.168.0.183:/home/sunrise/Desktop/
ssh root@192.168.0.183 'systemctl restart mira-touch'

# 如果想完全删除本 bridge
rm -rf "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge"
```

触觉系统的舵机动作不受影响——音频只是锦上添花。

---

## 相关文档

- HTTP API 详情 → [PROTOCOL.md](PROTOCOL.md)
- 怎么换音频 → [AUDIO_LIBRARY.md](AUDIO_LIBRARY.md)
- 板上 dispatcher 怎么发触发 → [../README.md](../README.md)
- 触觉系统整体 → [../../README.md](../../README.md)
