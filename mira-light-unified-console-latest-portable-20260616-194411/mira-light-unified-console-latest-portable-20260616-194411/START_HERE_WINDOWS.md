# Mira Light — Windows 快速启动

> 更新：2026-06-28 | 当前状态：✅ 完整功能可用

---

## 一键启动

| 操作 | 双击 |
|------|------|
| Web 控制台 | `Start-Latest-Console-Windows.bat` |
| 语音控制 | `Start-Voice-Full-Windows.bat` |

> 语音启动前需动作桥在运行。如开发板刚重启，SSH 上去启 9527：
> ```powershell
> ssh root@192.168.0.183 "cd /home/sunrise/Desktop && python3 rdk_bus_servo_tcp_bridge.py &>/dev/null &"
> ```

---

## 文档

| 文件 | 内容 |
|------|------|
| `CHANGELOG_2026-06-26_to_2026-06-28.md` | 完整更新日志 |
| `SETUP_GUIDE_WINDOWS.md` | 新电脑从零配置 |
| `README_VOICE_FULL.md` | 语音功能详解 |

---

## 当前配置

| 项 | 值 |
|----|-----|
| 语音引擎 | StepAudio 2.5（自然女声） |
| 语音模式 | continuous（持续监听） |
| 动作延迟 | ~2s（说完到硬件动） |
| Web 控制台 | http://127.0.0.1:8791/ |
| 动作桥 | http://127.0.0.1:19783/health |
| 开发板 | root@192.168.0.183:9527 |

---

## 语音命令示例

| 说 | Mira 做 |
|----|---------|
| 起床 | 起身 |
| 跳舞 | 舞蹈 |
| 睡觉 | 趴下熄灯 |
| 歪头 | 卖萌歪头 |
| 摸一摸 | 蹭蹭 |
| 你好 | 打招呼 |
| 我好开心 | 开心跳舞 |
| 再见 | 送别挥手 |
