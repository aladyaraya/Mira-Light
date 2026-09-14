# AI_BRIEFING.md
Mira Light · "答" 状态项目 · AI 上下文简报

> **使用方法**：把这整份文档粘贴给 ChatGPT / Claude 作为对话的开头消息，AI 就能理解整个 Mira "答" 状态项目，帮你回答实现疑问、debug、写新 timeline。

---

## 一句话概括

Mira 是一台桌面灯泡机器人（4 个总线舵机驱动颈部 + 底座）。当前任务的 v18 "答" 状态：**让 Mira 在"说话"（播放预录 mp3）时，4 个舵机按音频内容的语义节奏做同步动作**，效果像一个会用肢体语言演段子的机器人。

---

## 整体架构

```
┌──── Mac (macOS, 192.168.0.46) ────────────────────────┐
│                                                       │
│  Shenzhen Console (Python HTTP server)                │
│    URL: http://127.0.0.1:8777                         │
│    位置: ~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/
│    入口: shenzhen_console.py                          │
│    Web UI: web/index.html + web/app.js                │
│                                                       │
│  点 "演示答" 按钮 → POST /api/play-answer-demo        │
│    → import answer_demo                               │
│    → answer_demo.play_answer_demo():                  │
│        1. 用 TIMELINE 生成板侧 Python 脚本            │
│        2. SCP 脚本到板的 /tmp/                        │
│        3. SSH 执行 + 同时 afplay 本地 mp3            │
│                                                       │
│  音频: afplay → macOS 默认输出 → 蓝牙音箱（Mira 旁边） │
└───────────────────────────────────────────────────────┘
                  │ WiFi LAN
                  │ SSH (root@192.168.0.183 / <board-password>)
                  │ Auth via expect (sshpass 没装)
                  ▼
┌──── 板子 RDK X5 (Ubuntu, 192.168.0.183) ──────────────┐
│                                                       │
│  系统已有两个独立服务：                                │
│  1. mira-touch.service (systemd, 开机自启)           │
│     跑 /home/sunrise/Desktop/touch_dispatcher.py     │
│     处理"摸摸"触觉交互                                │
│     ⚠️ 跟"答"状态独立，不要动它                       │
│                                                       │
│  2. /home/sunrise/Desktop/four_servo_control.py      │
│     舵机底层驱动，命令行调用:                          │
│       python3 four_servo_control.py pose A B C D \   │
│           --speeds 200 200 200 200                   │
│     4 个舵机走 UART1 (1Mbps 总线)                    │
│                                                       │
│  "答" 状态运行时：                                     │
│     Mac SCP 来的 /tmp/mira_answer_demo.py            │
│     在板上跑 ~13.5 秒，按 TIMELINE sleep + fire      │
│     每个 fire = subprocess.Popen four_servo_control  │
└───────────────────────────────────────────────────────┘
                  │ UART1 (1Mbps 总线舵机)
                  ▼
┌──── 4 个总线舵机 (Mira 颈部 + 底座) ────────────┐
│  a = base_yaw        (底座旋转，左右转身)       │
│  b = lower_arm_lift  (下臂抬降，整体高度)       │
│  c = upper_arm_pitch (灯头俯仰，点头/抬头)      │
│  d = head_tilt       (灯头左右歪)               │
│                                                  │
│  PWM 编码: 中性 = 2048                          │
│  单位换算: 12 units / 度                        │
│  硬安全限: [1688, 2408] (±30°)                  │
│  推荐工作范围: ±13° 内（安全余量大）             │
└──────────────────────────────────────────────────┘
```

---

## TIMELINE 编码（核心数据结构）

**文件**：`mira-light-shenzhen-console/answer_demo.py` 里的 `TIMELINE` 常量

**类型**：`list[tuple[float, list[int], str]]`

**每项**：`(板时间秒数, [a, b, c, d 位置], 文字标签)`

举例：
```python
(0.40, [2048, 2120, 2072, 2048], "En 开场"),
#  ↑     ↑     ↑     ↑     ↑      ↑
#  时间  a=中  b=抬  c=微  d=中    标签
#         性  6°    低 2°  性
```

### 关节极性表（极重要）

| 字段  | 关节                     | 值 \> 2048    | 值 \< 2048   |
| --- | ---------------------- | ------------ | ----------- |
| `a` | base\_yaw 底座           | 向**左**转      | 向**右**转     |
| `b` | lower\_arm\_lift 下臂    | **抬起**（整体长高） | 降下          |
| `c` | upper\_arm\_pitch 灯头俯仰 | **抬头**（看上）   | **低头**（凑过来） |
| `d` | head\_tilt 头摇          | 向**右**歪      | 向**左**歪     |

### 时间轴对齐

- 板上脚本从 `board_t=0` 开始执行（SCP/SSH 后第一时间触发）
- Mac 端**等 0.4 秒**才启动 afplay（**破冰先于音频**，视觉先于听觉）
- 所以：音频实际从 `board_t=0.4` 开始播
- timeline 里 `0.00` 是破冰那一帧，`0.40` 是音频开场对齐点
- 音频长 12.5s，所以 `board_t=12.9` 时音频结束
- timeline 最后两个 marker（12.6 / 13.1）是收尾

### 安全约束

- **硬 clamp** `_CLAMP_LO=1688, _CLAMP_HI=2408`（±30°），定义在板上 `touch_dispatcher.py`，**Mac 端 `answer_demo.py` 里有同样的 `_clamp()` 函数自动夹**
- **推荐工作幅度** ±13° 内（手册建议）。超过 ±25° 接近机械极限
- **舵机过热**：**b（下臂）最易过热**，承担最大力矩。大幅 + 高频运动后摸 Mira 颈部判断（烫 → `ssh root@192.168.0.183 systemctl stop mira-touch` 让它凉 10-15 分钟，等凉透再 start）

---

## 当前已部署的 timeline (v18)

参考视频出来后预计要全面重写。当前是占位版：23 个 marker，幅度比较保守：
- **a 全程 2048（不动）** ← 视频里有左右 sway，需要加
- **b 最大 +5°，"好笑"瞬间 +10°** ← 视频里幅度更大
- **c 多次小点头**，跟随每个句子的语义
- **d 几乎不动**

视频里看到的幅度明显更大、更"灵动"。直接对照视频每段截一个 timestamp，对应到 TIMELINE 重写即可。

---

## 12.5 秒 comedian 音频内容

```
0.0  - 3.8s   "En 这本《Big meets Little》是刘扬设计的超萌绘本~"
3.8  - 4.2s   [停顿 = 句号]
4.2  - 7.4s   "极简图标对比大人与孩子视角下的家庭日常"
7.4  - 7.6s   [停顿]
7.6  - 8.8s   "又暖又好笑"          ← 短包袱
8.8  - 9.0s   [停顿]
9.0  - 12.2s  "和亘机那种一眼看懂的干货视频风格很搭哦~"
12.2 - 12.5s  [结尾静音]
```

调 timeline 时把**文本 anchor + 视频 timestamp** 对齐即可。

---

## 部署 / 测试流程

```bash
# 1. 改 answer_demo.py 里的 TIMELINE
vim ~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/answer_demo.py

# 2. 重启控制台（lazy import 必须重启进程）
pkill -f "shenzhen_console.py"
nohup python3 ~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/shenzhen_console.py \
    --host 127.0.0.1 --port 8777 \
    --board-host 192.168.0.183 --board-port 22 --board-user root \
    > /tmp/shenzhen_console.log 2>&1 &

# 3. 浏览器 ⌘+Shift+R 硬刷新 http://127.0.0.1:8777
# 4. 点 "演示答" 按钮，看 + 听效果
```

不开浏览器，直接 curl 测：
```bash
curl -sX POST http://127.0.0.1:8777/api/play-answer-demo \
    -H "Content-Type: application/json" \
    -d '{"host":"192.168.0.183","port":22,"user":"root","password":"<board-password>"}' \
    | python3 -m json.tool
```

只看会下发的 timeline，不发到板：
```bash
python3 ~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/answer_demo.py --dry-run
```

---

## 已知问题

1. **SCP 偶发 rc=1**：每次点按钮会 scp 一次 2KB 脚本到板，偶尔失败（SSH 并发冲突）。重试通常 OK。**根本解法**：把 scp 改成控制台启动时一次性，按按钮只 ssh 跑现有脚本（省 2 秒 + 排除并发）。
2. **板子 RTC 没电**：断电后系统时钟从 2000-01-01 起算。不影响功能，只影响日志 timestamp。
3. **touch\_dispatcher 跟 voice 答状态共用 UART1**：理论冲突。实际不会，因为答状态期间用户在听 Mira 说话，不会同时摸它。
4. **MiniMax TTS 已写未启用**：v16 写了 launcher 但没充值余额，仍用预录 mp3。跟"答"调动作无关。

---

## 不要碰的（除非有明确理由）

- 板上 `touch_dispatcher.py` 的状态机（v1-v13 调出来的 hysteresis、absence、cooldown 时序）
- 板上 `touch_mapping.json` 里的 7 个核心 timing 参数（lamp\_thr 等）
- `bridge_config.json` 的 `listenHost: 0.0.0.0`（让板能 POST 进来，改了就断）
- `_CLAMP_LO/_CLAMP_HI`（防撞机械限位的安全阀）

---

## 版本演进（压缩史）

- **v13**：触觉摸摸用离散 pose 序列（17 帧）
- **v14**：换成公式驱动的 `phased_sine_choreography`，4 关节正弦运动 + 阶段化编排
- **v15**：摸 4 秒触发音频（板 → Mac bridge → afplay）
- **v16**：加 MiniMax TTS launcher（已建未启用，没充余额）+ Mira 人设规范 v1.0 重写 prompts
- **v16.1**：c 灯头幅度大幅放大 + bias 优化 + clamp 从 ±25° 放到 ±30°
- **v17**：整体归档（本仓 `mira-1/`）
- **v18 (当前)**：实现"答"状态 — 深圳控制台按钮 + Mac → SSH → 板 timeline 同步舵机

---

## 工程师如何提问 AI

把这份文档贴给 AI 后，可以这样问：
- "我想让 Mira 在 8.4 秒'好笑'那帧 b 跳到 +18°，怎么改 TIMELINE？"
- "为什么 c 用负值表示低头？" → 看上面"关节极性"表
- "如果舵机过热了怎么办？" → 看上面"安全约束"
- "我刚改完 timeline，怎么测试？" → 看上面"部署/测试流程"
- "板上脚本里 `time.sleep(wait_for)` 怎么保证不漂移？" → AI 看 answer\_demo.py 的 render\_board\_script 就能答

AI 有这些上下文就能给出**具体可执行的答案**，不会说官话。