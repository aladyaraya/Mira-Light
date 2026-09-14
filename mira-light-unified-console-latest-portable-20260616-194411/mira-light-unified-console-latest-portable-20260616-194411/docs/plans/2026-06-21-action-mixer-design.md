# Mira Light 动作混合器设计：语音优先的联合调度方案

> 日期：2026-06-21
> 状态：设计稿
> 替代：当前 `mira_realtime_action_orchestrator.py` 的状态机 + `mira_light_runtime.py` 的强互斥锁

---

## 一、问题诊断：为什么"越往后走越容易出问题"

### 1.1 当前架构的四个根因

阅读当前代码后，定位到四个根因，它们叠加在一起导致长时间运行后越来越不稳定：

**根因 A：强互斥锁导致跟踪与语音对立**

`mira_light_runtime.py` 的 `_prepare_run` 使用 `_run_lock.acquire(blocking=False)`，同一时间只允许一个场景运行。`apply_tracking_event` 在有场景运行时直接抛异常：

```python
# mira_light_runtime.py:1623
if self.running_scene and self.running_scene.get("name") != "track_target":
    raise RuntimeError("Cannot update live tracking while another scene is running")
```

这意味着跟踪和语音场景是**互斥**的，不是联合的。

**根因 B：抢占式 stop + restart 导致动作抖动**

`mira_realtime_action_orchestrator.py` 的 `_post_with_scene_preemption` 遇到 "Another scene is already running" 错误时，先 stop 当前场景再重试：

```python
# 抢占逻辑：stop → 等待 → retry
resp = self._post(url, payload)
if "already running" in err_text:
    self._post("/v1/mira-light/stop", {})
    time.sleep(0.3)
    resp = self._post(url, payload)  # retry
```

这导致：跟踪正在跑 → 语音命令到来 → 跟踪被突然 stop → 语音场景启动 → 语音结束 → 跟踪需要重新 start。每次切换都有明显的"打断感"，而且 stop 事件、锁状态、tracking 状态在频繁切换中容易不一致。

**根因 C：状态机累积 stale 状态**

`RealtimeActionOrchestrator` 维护了大量运行时状态：

- `current_phase`（当前阶段）
- `last_transcript` / `last_assistant_text`（去重用）
- `cooldown_until`（冷却计时器）
- `pending_refinement`（待处理的细化）
- `recent_actions`（最近动作历史）

长时间运行后，这些状态会"累积"：cooldown 窗口可能误判、pending_refinement 可能变 stale、last_assistant_text 去重可能漏掉合理的重复。状态机只有"当前状态"这一个维度，没有"叠加"和"恢复"的能力。

**根因 D：没有统一的优先级仲裁层**

当前靠"谁先抢到锁谁赢" + "抢占式 stop"来处理冲突，没有统一的优先级调度。语音、跟踪、触摸事件各自直接调 runtime API，冲突时靠异常处理来"补救"，而不是提前仲裁。

### 1.2 问题表现

这四个根因叠加后，长时间运行的表现：

1. 跟踪和语音来回切换时动作抖动明显
2. cooldown 计时器在长时间运行后误判，导致合理的语音命令被忽略
3. stop 事件和锁状态不一致，导致 runtime 卡在"锁被占用但没有场景在跑"的死状态
4. 跟踪被反复 stop + restart，每次 restart 都从初始位置开始，丢失了之前的跟踪上下文

---

## 二、设计目标

1. **语音优先**：语音动作到来时，跟踪让出控制权但不被销毁；语音结束后跟踪平滑恢复
2. **联合而非互斥**：跟踪和语音可以同时存在，按优先级混合，不是"一个停另一个才能跑"
3. **比状态机好**：用"意图栈 + 关节控制权"替代"当前状态"，支持叠加和恢复
4. **长时间稳定**：不累积 stale 状态，每次语音交互都是干净的上下文
5. **平滑过渡**：动作切换有缓动过渡，没有突然的 stop + restart 抖动

---

## 三、核心概念：动作混合器（Action Mixer）

### 3.1 从"状态机"到"混音器"的范式转换

当前是状态机模型：同一时刻只有一个"当前状态"，切换时旧状态被销毁。

新方案是混音器模型：多个动作层同时存在，按优先级混合，像音频混音器一样。

```
状态机模型（当前）          混音器模型（新方案）
┌─────────────┐            ┌─────────────────────┐
│  当前状态:   │            │  L2 语音动作 (最高)  │ ← 抢占关节
│  track_target│            │  L1 跟踪动作        │ ← 被压低，保持位置
│             │            │  L0 背景微动 (最低)  │ ← 始终运行
│  语音到来 → │            │                     │
│  stop track │            │  语音到来 →          │
│  start voice │           │  L2 入栈，L1 让出关节 │
│  语音结束 → │            │  语音结束 →          │
│  start track │           │  L2 出栈，L1 收回关节 │
│  (从初始位置)│            │  (从当前位置恢复)     │
└─────────────┘            └─────────────────────┘
```

### 3.2 三层动作优先级

| 层级 | 名称 | 优先级 | 内容 | 关节控制权 |
|------|------|--------|------|-----------|
| L0 | 背景层 | 最低 | idle 微动、呼吸灯、待机姿态 | 没有其他层时才控制 |
| L1 | 跟踪层 | 中 | track_target 视觉跟踪 | 被 L2 压低时让出关节，保持最后位置 |
| L2 | 语音层 | 最高 | 语音触发的场景动作 | 到来时接管关节，结束后归还 |

### 3.3 关节控制权机制

每个关节（servo1, servo2, servo3, servo4, LED）有独立的"控制权"归属。高优先级层可以"借用"关节，低优先级层"让出"关节但记住自己的状态。

```python
# 关节控制权的数据结构
joint_ownership = {
    "servo1": {"owner": "L2", "prev_owner": "L1", "prev_pos": 512},
    "servo2": {"owner": "L2", "prev_owner": "L1", "prev_pos": 400},
    "servo3": {"owner": "L1", "prev_owner": "L0", "prev_pos": 300},
    "servo4": {"owner": "L1", "prev_owner": "L0", "prev_pos": 600},
    "led":    {"owner": "L2", "prev_owner": "L1", "prev_state": "tracking_blue"},
}
```

当 L2（语音）需要 servo1 和 servo2 时：
1. 记录 L1（跟踪）当前在 servo1/servo2 上的位置
2. 将 servo1/servo2 的 owner 改为 L2
3. L1 继续运行，但它的 servo1/servo2 输出被忽略（"压低"）
4. L2 结束后，servo1/servo2 的 owner 恢复为 L1
5. L1 从记录的位置平滑恢复跟踪

### 3.4 意图栈（Intent Stack）

替代状态机的"当前状态"，用"意图栈"管理动作叠加：

```
语音命令到来时的意图栈变化：

初始状态（只有跟踪在跑）:
栈顶 → [L1: track_target { target: book_A, pos: (300,400) } ]
栈底 → [L0: idle_breathing ]

用户说"摸一摸"（touch_affection 场景）:
栈顶 → [L2: touch_affection { phase: approach } ]  ← 新入栈
       [L1: track_target { target: book_A, pos: (300,400) } ]  ← 被压低
栈底 → [L0: idle_breathing ]

touch_affection 结束:
栈顶 → [L1: track_target { target: book_A, pos: (300,400) } ]  ← 恢复
栈底 → [L0: idle_breathing ]
```

关键区别：被压低的意图**不被销毁**，它的状态（目标、位置）被保留，恢复时从压低点继续。

---

## 四、音频驱动的联合调度

### 4.1 以语音事件为心跳

当前架构以固定间隔轮询 + cooldown 来管理动作。新方案以语音事件为心跳，语音事件驱动动作变化，跟踪事件作为背景修正。

```python
# 音频驱动的主循环（伪代码）
async def mixer_main_loop():
    while True:
        event = await event_bus.recv()  # 等待事件，不轮询

        if event.source == "voice":
            # 语音事件 = 高优先级，入栈 L2
            mixer.push_l2(event.scene, event.context)
            # 跟踪自动被压低，不需要显式 stop

        elif event.source == "vision":
            # 视觉事件 = 背景修正，更新 L1
            if mixer.l2_active():
                # L2 在跑，只更新 L1 的目标缓存，不输出到关节
                mixer.update_l1_target(event.target)
            else:
                # L2 不在跑，L1 正常输出到关节
                mixer.apply_l1_tracking(event.target)

        elif event.source == "touch":
            # 触摸事件 = 中高优先级，入栈 L2
            mixer.push_l2("touch_affection", event.context)
```

### 4.2 语音优先的运动规则

**规则 1：语音动作到来时，跟踪让出关节但不停止**

```python
def on_voice_action(scene_name, context):
    if mixer.l1_active() and mixer.l1_uses_joints(scene_name):
        # 记录 L1 当前关节位置
        mixer.snapshot_l1_joints()
        # L1 让出关节，但继续跟踪目标（只是不输出到关节）
        mixer.l1.set_mode("shadow")  # 影子模式：继续跟踪但不输出
    # L2 入栈，接管关节
    mixer.push_l2(scene_name, context)
```

**规则 2：语音动作结束后，跟踪从当前位置平滑恢复**

```python
def on_voice_action_done():
    mixer.pop_l2()
    if mixer.l1_active():
        # L1 从影子模式恢复，从当前关节位置平滑过渡到跟踪目标
        mixer.l1.set_mode("recover")
        # 缓动过渡，不是突然跳回
        mixer.l1.recover_from_current_pos(duration=0.8)
```

**规则 3：跟踪事件在语音期间被缓存，不丢弃**

```python
def on_vision_event(target):
    if mixer.l2_active():
        # L2 在跑，视觉事件存入 L1 的目标缓存
        mixer.l1.update_target_buffer(target)
        # 不输出到关节，但不丢弃目标信息
    else:
        mixer.l1.apply_tracking(target)
```

### 4.3 联合运动的具体场景

**场景：用户在跟踪书的时候说话**

```
时间线：
t0: 跟踪正在跑，灯头跟着书移动
t1: 用户说"你好可爱" → 语音层入栈
    - 跟踪让出 servo1/servo2（灯头），保持最后位置
    - 语音层接管 servo1/servo2，执行 cute_probe 动作
    - 跟踪继续在影子模式更新目标缓存
t2: cute_probe 动作进行中，灯头做呆萌探头
    - 视觉事件继续到来，存入缓存
t3: cute_probe 结束 → 语音层出栈
    - 跟踪从当前灯头位置平滑恢复
    - 恢复目标 = 缓存中最新的目标位置
    - 0.8 秒缓动过渡，不是突然跳回
t4: 跟踪恢复正常，灯头重新跟着书移动
```

**场景：用户在说话的时候书被移动了**

```
时间线：
t0: 语音动作正在跑（比如 daydream）
t1: 视觉检测到书移动了
    - 视觉事件存入跟踪缓存
    - 语音动作不受影响，继续跑
t2: 语音动作结束
    - 跟踪恢复，目标 = 缓存中最新的书位置
    - 灯头平滑转向新的书位置
    - 用户感觉：Mira 做完梦后自然地看向书的新位置
```

---

## 五、架构设计

### 5.1 新增组件：ActionMixer

```python
# mira_action_mixer.py（新文件）

class ActionMixer:
    """动作混合器：替代状态机 + 互斥锁的联合调度核心"""

    def __init__(self, bridge_url: str):
        self.bridge = MiraLightBridge(bridge_url)
        self.intent_stack = []  # 意图栈
        self.l0 = BackgroundLayer(self.bridge)   # 背景微动
        self.l1 = TrackingLayer(self.bridge)     # 跟踪层
        self.l2 = VoiceActionLayer(self.bridge)  # 语音动作层
        self.joint_ownership = {}  # 关节控制权表

    def push_voice_action(self, scene_name: str, context: dict):
        """语音动作入栈（L2）"""
        # 1. 快照 L1 当前关节位置
        if self.l1.is_active():
            self.l1.snapshot_joints()
            self.l1.set_mode("shadow")  # 影子模式
        # 2. L2 入栈，接管关节
        self.l2.start(scene_name, context)
        self._update_ownership(scene_name, "L2")

    def pop_voice_action(self):
        """语音动作出栈（L2 结束）"""
        self.l2.stop()
        # 恢复 L1
        if self.l1.is_active():
            self.l1.set_mode("recover")
            self.l1.recover_from_snapshot(duration=0.8)
            self._restore_ownership("L1")

    def update_tracking(self, target: dict):
        """视觉跟踪事件更新（L1）"""
        if self.l2.is_active():
            # L2 在跑，只更新缓存
            self.l1.update_target_buffer(target)
        else:
            self.l1.apply_tracking(target)

    def tick(self):
        """主循环 tick，由事件驱动"""
        self.l0.tick()  # 背景微动始终 tick
        self.l1.tick()  # 跟踪层 tick（影子模式也 tick）
        self.l2.tick()  # 语音动作层 tick
```

### 5.2 三层组件

```python
class BackgroundLayer:
    """L0 背景层：idle 微动、呼吸灯"""
    def tick(self):
        if not self._higher_layers_active():
            self._do_idle_motion()

class TrackingLayer:
    """L1 跟踪层：视觉跟踪，支持影子模式"""
    def __init__(self):
        self.mode = "active"  # active / shadow / recover
        self.target_buffer = None  # 目标缓存
        self.joint_snapshot = {}   # 关节位置快照

    def set_mode(self, mode):
        self.mode = mode

    def snapshot_joints(self):
        """记录当前关节位置，用于恢复"""
        self.joint_snapshot = self._read_current_joints()

    def update_target_buffer(self, target):
        """影子模式下更新目标缓存"""
        self.target_buffer = target

    def recover_from_snapshot(self, duration=0.8):
        """从快照位置平滑恢复到跟踪目标"""
        # 缓动过渡：从当前关节位置 → 目标位置
        self._ease_to_target(self.target_buffer, duration)
        self.mode = "active"

    def tick(self):
        if self.mode == "active":
            self._output_tracking()
        elif self.mode == "shadow":
            # 继续跟踪计算，但不输出到关节
            self._compute_tracking()
        elif self.mode == "recover":
            self._do_recovery_step()

class VoiceActionLayer:
    """L2 语音动作层：执行语音触发的场景"""
    def start(self, scene_name, context):
        self.current_scene = scene_name
        self._run_scene(scene_name, context)

    def stop(self):
        self._stop_scene()
        self.current_scene = None

    def is_active(self):
        return self.current_scene is not None
```

### 5.3 事件总线

替代当前的"直接调 API + 异常处理"，用事件总线统一仲裁：

```python
# mira_event_bus.py（新文件）

class EventBus:
    """事件总线：统一接收语音/视觉/触摸事件，转发给混合器"""

    def __init__(self, mixer: ActionMixer):
        self.mixer = mixer
        self.queue = asyncio.Queue()

    async def recv(self):
        return await self.queue.get()

    def emit_voice(self, scene_name, context):
        self.queue.put_nowait({
            "source": "voice",
            "scene": scene_name,
            "context": context,
            "timestamp": time.time()
        })

    def emit_vision(self, target):
        self.queue.put_nowait({
            "source": "vision",
            "target": target,
            "timestamp": time.time()
        })

    def emit_touch(self, event_type, context):
        self.queue.put_nowait({
            "source": "touch",
            "event": event_type,
            "context": context,
            "timestamp": time.time()
        })
```

### 5.4 与现有 runtime 的关系

**不替换 runtime，而是在 runtime 之上加一层混合器**：

```
当前架构:
  语音编排器 ──→ runtime (互斥锁) ──→ bridge ──→ 硬件
  视觉跟踪   ──↗ (冲突时抛异常)

新架构:
  语音事件 ──→ 事件总线 ──→ ActionMixer ──→ runtime (去掉互斥锁) ──→ bridge ──→ 硬件
  视觉事件 ──↗              (联合调度)      (只执行，不仲裁)
  触摸事件 ──↗
```

runtime 的 `_run_lock` 互斥锁被移除或降级为"关节级锁"（只锁被占用的关节，不锁整个场景）。场景仲裁逻辑从 runtime 上移到 ActionMixer。

---

## 六、平滑过渡机制

### 6.1 缓动过渡

所有动作切换都经过缓动过渡，没有突然的 stop + restart：

```python
def ease_transition(self, from_pos, to_pos, duration=0.8):
    """缓动过渡：从 from_pos 到 to_pos"""
    steps = int(duration / 0.02)  # 20ms 一步
    for i in range(steps):
        t = i / steps
        # ease-in-out 缓动函数
        eased = t * t * (3 - 2 * t)
        pos = from_pos + (to_pos - from_pos) * eased
        self._set_joint(pos)
        time.sleep(0.02)
```

### 6.2 三种过渡场景

| 过渡场景 | 触发条件 | 过渡方式 | 时长 |
|---------|---------|---------|------|
| 跟踪 → 语音 | 语音动作入栈 | 跟踪让出关节，语音从当前位置开始 | 0.3s |
| 语音 → 跟踪 | 语音动作出栈 | 跟踪从当前关节位置缓动到目标位置 | 0.8s |
| 跟踪 → 跟踪 | 目标位置更新 | 平滑跟随，限速移动 | 持续 |

### 6.3 消除"抖动"的关键

当前抖动来自抢占式 stop + restart。新方案的改进：

- **不 stop 跟踪**：跟踪只是进入影子模式，不停止
- **不 restart 跟踪**：语音结束后从当前位置恢复，不从初始位置 restart
- **不抛异常**：冲突在混合器层仲裁，不靠异常补救
- **不累积 cooldown**：事件驱动，不需要 cooldown 窗口

---

## 七、长时间稳定性设计

### 7.1 不累积 stale 状态

当前状态机的问题：cooldown、last_transcript、pending_refinement 会累积。

新方案的改进：

- **意图栈自动清理**：L2 出栈时，所有 L2 相关状态被销毁，不残留
- **L1 状态最小化**：L1 只维护"当前目标"和"关节快照"，不维护历史
- **L0 无状态**：L0 是纯函数式的微动，不维护任何状态
- **事件驱动，不轮询**：没有 cooldown 计时器，不需要"过期检查"

### 7.2 状态一致性保证

```python
class ActionMixer:
    def _verify_consistency(self):
        """定期一致性检查（每 30 秒）"""
        # 检查 1：关节控制权表和实际输出一致
        for joint, owner in self.joint_ownership.items():
            actual_owner = self._who_is_outputting(joint)
            if owner != actual_owner:
                self._reconcile(joint)

        # 检查 2：L2 不在跑时，L1 应该是 active 模式
        if not self.l2.is_active() and self.l1.mode == "shadow":
            self.l1.set_mode("recover")
            self.l1.recover_from_snapshot()

        # 检查 3：意图栈深度不超过 3
        if len(self.intent_stack) > 3:
            self.intent_stack = self.intent_stack[-3:]
```

### 7.3 异常恢复

```python
def on_bridge_error(self, error):
    """bridge 通信错误时的恢复策略"""
    # 1. 不抛异常给上层，在混合器层消化
    # 2. 重置关节控制权表
    self.joint_ownership = {}
    # 3. L1 进入 active 模式（从当前位置重新开始跟踪）
    self.l1.set_mode("active")
    # 4. L2 如果在跑，标记为需要重试
    if self.l2.is_active():
        self.l2.mark_retry_needed()
    # 5. 记录日志，不中断主循环
    self._log_error(error)
```

---

## 八、与语音系统的集成

### 8.1 替代 RealtimeActionOrchestrator

当前的 `RealtimeActionOrchestrator` 是一个状态机，维护 current_phase、cooldown、last_transcript 等。新方案中，它的职责被拆分：

| 当前职责 | 新方案归属 | 改进 |
|---------|-----------|------|
| 语音转写去重 | 语音层（L2）内部 | 只在 L2 生命周期内维护，L2 出栈时清理 |
| cooldown 计时 | 移除 | 事件驱动不需要 cooldown |
| 场景抢占 | ActionMixer.push_voice_action | 混合器仲裁，不靠异常 |
| pending_refinement | 移除 | 语音事件即时处理，不缓存 |
| recent_actions 历史 | 移除 | 不需要历史，意图栈就是当前状态 |

### 8.2 语音事件到混合器的映射

```python
# StepFun 实时语音事件 → 混合器
class VoiceEventAdapter:
    """把 StepFun 实时语音事件转换为混合器事件"""

    def on_assistant_response(self, transcript: str):
        """助手回复时，解析动作意图"""
        action = self._parse_action(transcript)
        if action.type == "scene":
            # 语音触发场景 → L2 入栈
            self.mixer.push_voice_action(action.scene, action.context)
        elif action.type == "none":
            # 纯对话，不触发动作
            pass

    def on_response_done(self):
        """助手回复结束"""
        # 如果当前 L2 是语音触发的场景动作，出栈
        if self.mixer.l2.is_voice_triggered():
            self.mixer.pop_voice_action()
```

### 8.3 语音优先的具体实现

"语音优先"在代码层面体现为：

1. **语音事件总是入栈 L2**：不管 L1 在做什么，语音事件都会入栈
2. **L2 入栈时 L1 自动让出**：不需要显式 stop 跟踪
3. **L2 出栈时 L1 自动恢复**：不需要显式 restart 跟踪
4. **L2 期间 L1 继续缓存目标**：视觉信息不丢失
5. **L2 的关节输出优先级最高**：同一关节上 L2 的输出覆盖 L1

---

## 九、实施计划

### 阶段 1：混合器核心（1-2 天）

新建文件：
- `scripts/mira_action_mixer.py` — ActionMixer 核心类
- `scripts/mira_event_bus.py` — 事件总线

修改文件：
- `scripts/mira_light_runtime.py` — 移除 `_run_lock` 互斥锁，改为关节级锁
- `scripts/mira_light_runtime.py` — `apply_tracking_event` 不再抛异常，改为委托混合器

### 阶段 2：三层组件（2-3 天）

- `scripts/mira_action_mixer.py` — BackgroundLayer、TrackingLayer、VoiceActionLayer
- `scripts/mira_tracking_layer.py` — 跟踪层的影子模式 + 恢复逻辑

### 阶段 3：语音集成（1-2 天）

- 修改 `scripts/mira_stepfun_realtime_voice_actions.py` — 用 VoiceEventAdapter 替代 RealtimeActionOrchestrator
- 修改 `scripts/mira_windows_full_duplex_voice.py` — 语音事件转发到事件总线

### 阶段 4：测试与调参（2-3 天）

- 单元测试：混合器的入栈/出栈/影子模式/恢复逻辑
- 集成测试：语音 + 跟踪联合场景
- 长时间稳定性测试：连续运行 2 小时，检查状态一致性

### 验收标准

1. 语音动作到来时，跟踪平滑让出关节，没有突然 stop 的抖动
2. 语音动作结束后，跟踪从当前位置平滑恢复，不从初始位置 restart
3. 连续运行 2 小时，没有"锁被占用但没有场景在跑"的死状态
4. 语音和跟踪来回切换 50 次，动作流畅，没有累积抖动
5. 视觉事件在语音期间被缓存，语音结束后跟踪目标是最新的

---

## 十、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 影子模式下跟踪计算消耗资源 | 影子模式只更新目标缓存，不做关节输出计算 |
| 缓动过渡期间新的语音事件到来 | 意图栈支持多层 L2，新事件入栈时中断当前过渡 |
| 关节控制权表不一致 | 每 30 秒一致性检查 + bridge 错误时重置 |
| 与现有 5 个控制台的兼容 | 混合器作为可选层，控制台可以直接调 runtime（兼容模式）或调混合器（新模式） |
| StepFun 实时语音的事件格式变化 | VoiceEventAdapter 作为适配层，隔离格式变化 |

---

## 附录：与当前代码的对应关系

| 当前代码 | 新方案 | 变化 |
|---------|--------|------|
| `mira_realtime_action_orchestrator.py` | `mira_action_mixer.py` + `VoiceEventAdapter` | 状态机 → 混合器 |
| `mira_light_runtime.py:_run_lock` | 关节级锁 | 全局互斥 → 关节级 |
| `mira_light_runtime.py:apply_tracking_event` | `ActionMixer.update_tracking` | 抛异常 → 委托混合器 |
| `_post_with_scene_preemption` | `ActionMixer.push_voice_action` | 抢占式 stop → 影子模式 |
| `current_phase` / `cooldown_until` | 意图栈 | 状态累积 → 栈自动清理 |
| `pending_refinement` | 移除 | 缓存 → 即时处理 |
| `recent_actions` | 移除 | 历史 → 当前栈即状态 |
