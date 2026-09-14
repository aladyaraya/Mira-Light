# Voice Light Commands

These phrases are recognized after speech-to-text and mapped to Mira Light
bridge actions in Full mode.

Full mode path:

```text
voice transcript
-> scripts/mira_voice_intents.py
-> /v1/mira-light/run-scene or /v1/mira-light/trigger
-> local bridge
-> lamp target
```

## Scene Commands

You can say these as direct control commands:

```text
启动起床
执行起床
唤醒
开场
```

Runs:

```text
wake_up
```

```text
启动好奇
观察一下
看看我
歪头看
```

Runs:

```text
curious_observe
```

```text
摸一摸
摸摸
靠过来
撒娇
互动一下
```

Runs:

```text
touch_affection
```

```text
躲一下
手靠近
后退
缩一下
```

Runs:

```text
hand_avoid
```

```text
卖萌
萌一下
歪头
探头
```

Runs:

```text
cute_probe
```

```text
发呆
走神
放空
做梦
```

Runs:

```text
daydream
```

```text
提醒我站起来
久坐提醒
蹭蹭
活动一下
```

Runs:

```text
standup_reminder
```

```text
开始追踪
追踪目标
跟着看
跟随
```

Runs:

```text
track_target
```

```text
启动跳舞模式
来个庆祝
庆祝一下
彩虹
高兴一下
```

Runs:

```text
celebrate
```

```text
拜拜
再见
挥手
送别
```

Runs:

```text
farewell
```

```text
进入睡觉
休息
安静下来
收起来
回去睡觉
```

Runs:

```text
sleep
```

```text
叹气检测
安慰
听我叹气
```

Runs:

```text
sigh_demo
```

```text
多人反应
两个人
纠结一下
不知道看谁
```

Runs:

```text
multi_person_demo
```

```text
我今天好累
语音理解
听懂我累
安慰我
```

Runs:

```text
voice_demo_tired
```

```text
吓一跳
受惊
惊吓
被吓到
```

Runs:

```text
startle_sound
```

```text
夸奖
被夸奖
开心一下
你好可爱
表扬
```

Runs:

```text
praise_demo
```

```text
批评
被批评
委屈
表现不好
不太行
```

Runs:

```text
criticism_demo
```

## Emotion Trigger Phrases

These phrases also trigger lamp body reactions.

Some use trigger events:

```text
我今天好累啊
辛苦了
难受
```

Trigger:

```text
voice_tired
```

```text
唉
哎
```

Trigger:

```text
sigh_detected
```

```text
拜拜
再见
```

Trigger or scene depending on wording:

```text
farewell_detected / farewell
```

Direct command wording such as `启动挥手` or `送别` prefers the scene route.

Other emotional words map directly to scenes:

```text
开心 / 高兴 / 兴奋 / 太好了
```

Runs:

```text
celebrate
```

```text
困了 / 想睡 / 想休息 / 安静一点
```

Runs:

```text
sleep
```

```text
发呆 / 走神 / 放空
```

Runs:

```text
daydream
```

```text
害怕 / 吓到 / 吓一跳 / 紧张
```

Runs:

```text
startle_sound
```

## Motion Speed

The default action speed multiplier is:

```text
MIRA_LIGHT_ACTION_SPEED_MULTIPLIER=1.5
```

This makes scene delays and bus-servo move times about 1.5x faster than the
original choreography. To restore the old speed for one run:

```bash
MIRA_LIGHT_ACTION_SPEED_MULTIPLIER=1.0 ./Start-Mira-Light-Voice-Cloud-Full.command
```
