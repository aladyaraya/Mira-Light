# HANDOFF_TO_ENGINEER.md
交接给工程师 · Mira "答" 状态动作调整

> 收到这份文档时你应该已经拿到 **3 段 Mira 动作参考视频**（听 / 想 / 答）。
> **视频是动作的最终标准**——这份文档只是辅助技术上下文。

## 当前状态

已部署的功能（v18，可立即跑）：
- 深圳控制台（http://127.0.0.1:8777）已经有 "**演示「答」（12.5 秒）**" 按钮
- 点击后：Mac 通过蓝牙音箱播 12.5 秒 comedian 音频 + 同时板上 Mira 做 23 个 motion marker 同步动作
- 链路：Mac → SSH → 板上 `four_servo_control.py` → 4 个总线舵机

**剩余工作（你的事）**：现有 timeline 的动作幅度和节奏跟视频差距还挺大，需要**对照视频重新调整 marker 数值**。

## 改哪里

唯一要动的文件：
```
~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/answer_demo.py
```

里面有个常量 `TIMELINE`，是一组 tuple：
```python
TIMELINE = [
    (0.00,    [2048, 2156, 2108, 2048], "破冰: b +9°, c +5°"),
    (0.40,    [2048, 2120, 2072, 2048], "En 开场"),
    ...
]
```

每行：`(秒数, [a, b, c, d 舵机位置], 标签)`

- `a` = 底座旋转（左右转身），`>2048 左`, `<2048 右`
- `b` = 下臂抬降（整体上下），`>2048 抬起`, `<2048 降`
- `c` = 灯头俯仰（点头/抬头），`>2048 抬头`, `<2048 低头`
- `d` = 灯头左右歪，`>2048 右`, `<2048 左`
- 中性值 **2048**，**12 unit = 1°**
- 安全硬限 **[1688, 2408](#)**（±30°，dispatcher 内 clamp）

## 改完怎么部署

```bash
# 1. 重启控制台（重要：TIMELINE 是 lazy import，必须重启进程才生效）
pkill -f "shenzhen_console.py"
nohup python3 ~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/shenzhen_console.py \
    --host 127.0.0.1 --port 8777 \
    --board-host 192.168.0.183 --board-port 22 --board-user root \
    > /tmp/shenzhen_console.log 2>&1 &

# 2. 浏览器硬刷新 http://127.0.0.1:8777 （⌘+Shift+R）

# 3. 点 "演示「答」" 按钮 → 看 + 听效果
```

不想用浏览器，直接命令行测试：
```bash
curl -sX POST http://127.0.0.1:8777/api/play-answer-demo \
    -H "Content-Type: application/json" \
    -d '{"host":"192.168.0.183","port":22,"user":"root","password":"<board-password>"}'
```

只想看生成的板侧脚本（不发车）：
```bash
python3 ~/Downloads/Mira/Ready-To-Run-Mira-Light-Anime/mira-light-shenzhen-console/answer_demo.py --dry-run
```

## 已知小问题

1. **SCP 偶发 rc=1**：每次点按钮会 scp 一次脚本（2KB）到板。偶尔失败（可能 SSH 并发冲突）。等 5-10 秒再点通常就好。如果反复，看 `/tmp/shenzhen_console.log`。
2. **想根治这个**：把 scp 改成"控制台启动时一次性 scp，按按钮只 ssh 跑现有脚本"，能省 2 秒 + 排除并发问题。这是优化项不是必须。

## 不要动的（除非真的有必要）

| 不动                                    | 在哪                                                     | 原因                      |
| ------------------------------------- | ------------------------------------------------------ | ----------------------- |
| `touch_dispatcher.py`（板上）             | `/home/sunrise/Desktop/`                               | 触觉摸摸交互的核心，跟语音"答"是两套独立逻辑 |
| `touch_mapping.json`（板上）              | 同上                                                     | 同上                      |
| `bridge_config.json`（Mac）             | `Mira-Light-Voice-Full-Ready/tools/mira_light_bridge/` | 跟"答"无关                  |
| 板 dispatcher 里的 `_CLAMP_LO/_CLAMP_HI` | 同 dispatcher                                           | 防撞机械限位的安全阀              |

## 进一步上下文

- **系统说明 + 上下文（给 AI 看的）**：本文件夹下 `AI_BRIEFING.md`。**强烈建议把这份贴给 AI 助手**（ChatGPT/Claude），它就能帮你回答 80% 的"为什么这样写"。
- **三段交互剧本**（听/想/答）：`docs/v18-listening-thinking-script.md`
- **完整方案历史**：`docs/plans/mira-light-parallel-wren.md`（很长，按需查）
- **触觉系统手册**：`docs/plans/wifi-tingly-turtle.md`（v1-v13 历史 + 板侧硬件特性）

板子整体不响应、SSH 不通、舵机异响等硬件层问题 → 根目录 `DEPLOYMENT.md` 故障排查段。