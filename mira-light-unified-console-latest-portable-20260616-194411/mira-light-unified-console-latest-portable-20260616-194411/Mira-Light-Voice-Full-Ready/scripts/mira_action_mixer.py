"""Mira Light 动作混合器 (Action Mixer).

替代之前的"状态机 + 互斥锁"架构，用"混音器模型"实现
语音优先的联合调度。

核心概念:
    - 三层动作优先级: L0 背景层 / L1 跟踪层 / L2 语音层
    - 关节控制权: 每个关节有独立归属，高优先级可"借用"
    - 意图栈: 替代"当前状态"，被压低的意图不被销毁
    - 影子模式: 语音期间跟踪不停止，只是不输出到关节
    - 缓动过渡: 动作切换有 ease-in-out 过渡，没有突然 stop+restart

设计文档: docs/plans/2026-06-21-action-mixer-design.md
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from mira_event_bus import (
    EVENT_SOURCE_CONSOLE,
    EVENT_SOURCE_IDLE,
    EVENT_SOURCE_TOUCH,
    EVENT_SOURCE_VISION,
    EVENT_SOURCE_VOICE,
    EventBus,
    MixerEvent,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SERVO_KEYS = ("servo1", "servo2", "servo3", "servo4")
ALL_JOINTS = (*SERVO_KEYS, "led")

# 缓动过渡时长（秒）
RECOVER_DURATION_DEFAULT = 0.8
HANDOFF_DURATION_DEFAULT = 0.3

# 一致性检查间隔（秒）
CONSISTENCY_CHECK_INTERVAL = 30.0

# 意图栈最大深度
MAX_INTENT_STACK_DEPTH = 3


class LayerPriority:
    """三层优先级."""

    L0_BACKGROUND = 0  # 背景微动
    L1_TRACKING = 10  # 视觉跟踪
    L2_VOICE = 30  # 语音动作（最高）


class TrackingMode(str, Enum):
    """跟踪层的工作模式."""

    ACTIVE = "active"  # 正常输出到关节
    SHADOW = "shadow"  # 继续计算但不输出（语音期间）
    RECOVER = "recover"  # 从当前位置缓动到目标位置
    IDLE = "idle"  # 没有跟踪目标


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class JointOwnership:
    """关节控制权记录."""

    owner: str  # "L0" / "L1" / "L2"
    prev_owner: str = "L0"
    prev_value: Any = None  # 之前的关节位置/LED 状态


@dataclass
class Intent:
    """意图栈中的一个条目."""

    layer: str  # "L0" / "L1" / "L2"
    name: str  # 场景名 / "track_target" / "idle_breathing"
    context: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    # 跟踪层专用：被压低时的关节快照
    joint_snapshot: dict[str, Any] = field(default_factory=dict)
    # 跟踪层专用：被压低时的目标缓存
    target_buffer: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 缓动过渡工具
# ---------------------------------------------------------------------------


def ease_in_out(t: float) -> float:
    """ease-in-out 缓动函数."""
    return t * t * (3 - 2 * t)


def ease_step(current: float, target: float, alpha: float = 0.42) -> float:
    """单步平滑（类似 runtime 的 _smooth_servo_target）."""
    diff = target - current
    if abs(diff) <= 1:
        return target if abs(diff) > 0.5 else current
    return round(current + diff * alpha)


# ---------------------------------------------------------------------------
# 三层组件
# ---------------------------------------------------------------------------


class BackgroundLayer:
    """L0 背景层: idle 微动、呼吸灯.

    无状态，纯函数式。只在没有任何高层动作时才输出到关节。
    """

    def __init__(self, emit: Callable[[str], None] | None = None) -> None:
        self._emit = emit or (lambda msg: None)
        self._breath_phase = 0.0
        self._tick_count = 0

    def tick(self, higher_layers_active: bool) -> dict[str, Any] | None:
        """每个 tick 调用，返回关节指令（如果需要输出）.

        Returns:
            关节指令 dict 或 None（高层在跑时不输出）
        """
        self._tick_count += 1
        self._breath_phase += 0.02

        if higher_layers_active:
            return None  # 高层在跑，背景层不输出

        # 呼吸灯效果（每 50 tick 输出一次，约 1 秒）
        if self._tick_count % 50 != 0:
            return None

        brightness = int(120 + 30 * (0.5 + 0.5 * (self._breath_phase % 6.28) / 3.14))
        return {
            "led": {"mode": "solid", "brightness": brightness, "color": {"r": 255, "g": 200, "b": 150}},
            "_layer": "L0",
        }


class TrackingLayer:
    """L1 跟踪层: 视觉跟踪，支持影子模式.

    模式切换:
        ACTIVE  → 语音到来 → SHADOW（让出关节，继续计算）
        SHADOW  → 语音结束 → RECOVER（从当前位置缓动到目标）
        RECOVER → 缓动完成 → ACTIVE
        任意    → 目标丢失 → IDLE
    """

    def __init__(
        self,
        emit: Callable[[str], None] | None = None,
        compute_tracking: Callable[[dict[str, Any]], dict[str, int]] | None = None,
        read_joints: Callable[[], dict[str, int]] | None = None,
    ) -> None:
        self._emit = emit or (lambda msg: None)
        self._compute_tracking = compute_tracking or (lambda target: {})
        self._read_joints = read_joints or (lambda: {})
        self.mode = TrackingMode.IDLE
        self._target: dict[str, Any] = {}
        self._joint_snapshot: dict[str, int] = {}
        self._target_buffer: dict[str, Any] = {}  # 影子模式下缓存的目标
        self._recover_start: dict[str, int] = {}
        self._recover_target: dict[str, int] = {}
        self._recover_start_time: float = 0.0
        self._recover_duration: float = RECOVER_DURATION_DEFAULT
        self._last_output: dict[str, int] = {}
        self._lock = threading.Lock()

    def is_active(self) -> bool:
        with self._lock:
            return self.mode in (TrackingMode.ACTIVE, TrackingMode.SHADOW, TrackingMode.RECOVER)

    def is_outputting(self) -> bool:
        """是否正在向关节输出（ACTIVE 或 RECOVER 模式）."""
        with self._lock:
            return self.mode in (TrackingMode.ACTIVE, TrackingMode.RECOVER)

    def set_mode(self, mode: TrackingMode) -> None:
        with self._lock:
            old_mode = self.mode
            self.mode = mode
        if old_mode != mode:
            self._emit(f"[mixer-L1] mode {old_mode.value} → {mode.value}")

    def snapshot_joints(self) -> None:
        """记录当前关节位置，用于恢复."""
        with self._lock:
            self._joint_snapshot = dict(self._read_joints())
        self._emit(f"[mixer-L1] snapshot joints: {self._joint_snapshot}")

    def update_target_buffer(self, target: dict[str, Any]) -> None:
        """影子模式下更新目标缓存（不输出到关节）."""
        with self._lock:
            self._target_buffer = dict(target)

    def start_recovery(self, duration: float = RECOVER_DURATION_DEFAULT) -> None:
        """从当前关节位置缓动到跟踪目标位置."""
        with self._lock:
            # 使用缓存的目标计算恢复目标
            target = self._target_buffer or self._target
            if not target:
                self.set_mode(TrackingMode.IDLE)
                return
            self._recover_target = dict(self._compute_tracking(target))
            self._recover_start = dict(self._read_joints())
            self._recover_start_time = time.time()
            self._recover_duration = duration
            # 合并快照位置作为起点（如果有关节没读到）
            for joint in SERVO_KEYS:
                if joint not in self._recover_start and joint in self._joint_snapshot:
                    self._recover_start[joint] = self._joint_snapshot[joint]
        self.set_mode(TrackingMode.RECOVER)
        self._emit(f"[mixer-L1] start recovery → {self._recover_target}")

    def tick(self) -> dict[str, Any] | None:
        """每个 tick 调用，返回关节指令（如果需要输出）."""
        with self._lock:
            mode = self.mode

        if mode == TrackingMode.ACTIVE:
            return self._tick_active()
        elif mode == TrackingMode.SHADOW:
            # 影子模式：继续计算目标但不输出
            self._tick_shadow()
            return None
        elif mode == TrackingMode.RECOVER:
            return self._tick_recover()
        return None

    def clear_target(self, reason: str = "target_missing") -> None:
        """目标丢失时清理."""
        with self._lock:
            self._target = {}
            self._target_buffer = {}
        self.set_mode(TrackingMode.IDLE)
        self._emit(f"[mixer-L1] target cleared: {reason}")

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "mode": self.mode.value,
                "hasTarget": bool(self._target or self._target_buffer),
                "jointSnapshot": dict(self._joint_snapshot),
                "targetBuffer": dict(self._target_buffer),
                "lastOutput": dict(self._last_output),
            }

    # -- 内部方法 --

    def _tick_active(self) -> dict[str, Any] | None:
        """ACTIVE 模式：正常输出跟踪."""
        with self._lock:
            target = self._target_buffer or self._target
        if not target:
            return None
        servo_cmd = self._compute_tracking(target)
        if not servo_cmd:
            return None
        with self._lock:
            self._last_output = dict(servo_cmd)
        return {"servos": servo_cmd, "_layer": "L1"}

    def _tick_shadow(self) -> None:
        """SHADOW 模式：只更新目标缓存，不输出."""
        # 目标已经在 update_target_buffer 中更新，这里不做额外计算
        pass

    def _tick_recover(self) -> dict[str, Any] | None:
        """RECOVER 模式：缓动过渡."""
        with self._lock:
            elapsed = time.time() - self._recover_start_time
            progress = min(1.0, elapsed / max(0.01, self._recover_duration))
            eased = ease_in_out(progress)
            cmd = {}
            for joint in SERVO_KEYS:
                if joint in self._recover_start and joint in self._recover_target:
                    start_val = self._recover_start[joint]
                    target_val = self._recover_target[joint]
                    cmd[joint] = int(round(start_val + (target_val - start_val) * eased))
            self._last_output = dict(cmd)

        if progress >= 1.0:
            # 恢复完成，切回 ACTIVE
            self.set_mode(TrackingMode.ACTIVE)
            self._emit("[mixer-L1] recovery complete → ACTIVE")

        return {"servos": cmd, "_layer": "L1"} if cmd else None


class VoiceActionLayer:
    """L2 语音动作层: 执行语音触发的场景动作.

    到来时接管关节，结束后归还。
    支持场景执行和回调通知。
    """

    def __init__(
        self,
        emit: Callable[[str], None] | None = None,
        run_scene: Callable[[str, dict[str, Any]], Any] | None = None,
        stop_scene: Callable[[], Any] | None = None,
        is_scene_running: Callable[[], bool] | None = None,
    ) -> None:
        self._emit = emit or (lambda msg: None)
        self._run_scene = run_scene or (lambda name, ctx: None)
        self._stop_scene = stop_scene or (lambda: None)
        self._is_scene_running = is_scene_running or (lambda: False)
        self._current_scene: str | None = None
        self._current_context: dict[str, Any] = {}
        self._started_at: float = 0.0
        self._on_done: Callable[[str], None] | None = None
        self._lock = threading.Lock()

    def is_active(self) -> bool:
        with self._lock:
            return self._current_scene is not None

    def start(self, scene_name: str, context: dict[str, Any] | None = None) -> None:
        """启动语音场景."""
        with self._lock:
            # 如果有正在跑的场景，先停止
            if self._current_scene is not None:
                self._emit(f"[mixer-L2] preempting {self._current_scene} for {scene_name}")
                self._stop_scene()
            self._current_scene = scene_name
            self._current_context = dict(context or {})
            self._started_at = time.time()
        self._emit(f"[mixer-L2] start scene: {scene_name}")
        try:
            self._run_scene(scene_name, self._current_context)
        except Exception as exc:  # noqa: BLE001
            self._emit(f"[mixer-L2] scene start error: {exc}")
            with self._lock:
                self._current_scene = None

    def stop(self) -> None:
        """停止当前语音场景."""
        with self._lock:
            scene = self._current_scene
            self._current_scene = None
            self._current_context = {}
        if scene:
            self._emit(f"[mixer-L2] stop scene: {scene}")
            try:
                self._stop_scene()
            except Exception as exc:  # noqa: BLE001
                self._emit(f"[mixer-L2] scene stop error: {exc}")
        # 通知完成回调
        if self._on_done and scene:
            try:
                self._on_done(scene)
            except Exception:  # noqa: BLE001
                pass

    def set_on_done(self, callback: Callable[[str], None]) -> None:
        self._on_done = callback

    def check_done(self) -> bool:
        """检查场景是否已完成（非阻塞）."""
        with self._lock:
            if self._current_scene is None:
                return True
        # 检查 runtime 侧场景是否还在跑
        if not self._is_scene_running():
            scene = self._current_scene
            with self._lock:
                self._current_scene = None
                self._current_context = {}
            self._emit(f"[mixer-L2] scene {scene} finished")
            if self._on_done:
                try:
                    self._on_done(scene)
                except Exception:  # noqa: BLE001
                    pass
            return True
        return False

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._current_scene is not None,
                "scene": self._current_scene,
                "context": dict(self._current_context),
                "startedAt": self._started_at,
                "elapsed": time.time() - self._started_at if self._current_scene else 0,
            }


# ---------------------------------------------------------------------------
# ActionMixer 主类
# ---------------------------------------------------------------------------


class ActionMixer:
    """动作混合器: 替代状态机 + 互斥锁的联合调度核心.

    使用方式:
        mixer = ActionMixer(runtime=runtime)
        mixer.start()  # 启动事件循环

        # 语音事件
        mixer.push_voice_action("touch_affection", {"side": "left"})

        # 视觉事件
        mixer.update_tracking(target_data)

        # 语音结束
        mixer.pop_voice_action()

    关键设计:
        - 语音优先: 语音到来时跟踪让出关节（影子模式），不停止
        - 联合调度: 跟踪和语音同时存在，按优先级混合
        - 平滑过渡: 动作切换有缓动过渡，没有突然 stop+restart
        - 长时间稳定: 不累积 stale 状态，定期一致性检查
    """

    def __init__(
        self,
        runtime: Any | None = None,
        event_bus: EventBus | None = None,
        emit: Callable[[str], None] | None = None,
        recover_duration: float = RECOVER_DURATION_DEFAULT,
    ) -> None:
        self._runtime = runtime
        self._event_bus = event_bus or EventBus()
        self._emit = emit or (lambda msg: logger.info(msg))
        self._recover_duration = recover_duration

        # 关节控制权表
        self._joint_ownership: dict[str, JointOwnership] = {
            joint: JointOwnership(owner="L0") for joint in ALL_JOINTS
        }
        self._ownership_lock = threading.Lock()

        # 意图栈
        self._intent_stack: list[Intent] = []
        self._stack_lock = threading.Lock()

        # 三层组件
        self._l0 = BackgroundLayer(emit=self._emit)
        self._l1 = TrackingLayer(
            emit=self._emit,
            compute_tracking=self._compute_tracking_from_target,
            read_joints=self._read_current_joints,
        )
        self._l2 = VoiceActionLayer(
            emit=self._emit,
            run_scene=self._run_scene_via_runtime,
            stop_scene=self._stop_scene_via_runtime,
            is_scene_running=self._is_scene_running_via_runtime,
        )
        self._l2.set_on_done(self._on_voice_action_done)

        # 主循环控制
        self._running = False
        self._tick_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._tick_interval = 0.02  # 20ms

        # 一致性检查
        self._last_consistency_check = time.time()

        # 统计
        self._stats = {
            "voiceActionsTotal": 0,
            "trackingEventsTotal": 0,
            "touchEventsTotal": 0,
            "preemptionsTotal": 0,
            "recoveriesTotal": 0,
            "consistencyChecksTotal": 0,
            "consistencyFixesTotal": 0,
        }

    # -- 生命周期 --

    def start(self) -> None:
        """启动混合器主循环."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._tick_thread = threading.Thread(target=self._main_loop, daemon=True, name="action-mixer")
        self._tick_thread.start()
        self._emit("[mixer] started")

    def stop(self) -> None:
        """停止混合器."""
        self._running = False
        self._stop_event.set()
        if self._tick_thread and self._tick_thread.is_alive():
            self._tick_thread.join(timeout=2.0)
        self._emit("[mixer] stopped")

    # -- 公共 API: 语音动作 --

    def push_voice_action(self, scene_name: str, context: dict[str, Any] | None = None) -> None:
        """语音动作入栈（L2）.

        - 如果跟踪在跑，进入影子模式（让出关节但不停止）
        - L2 接管关节，执行语音场景
        - 视觉事件继续被缓存
        """
        self._stats["voiceActionsTotal"] += 1

        # 1. 如果 L1 在跑，快照关节 + 进入影子模式
        if self._l1.is_active():
            self._l1.snapshot_joints()
            self._l1.set_mode(TrackingMode.SHADOW)
            self._emit("[mixer] L1 → SHADOW (voice action incoming)")

        # 2. 更新关节控制权：L2 接管所有关节
        self._transfer_ownership("L2", ALL_JOINTS)

        # 3. 入栈意图
        intent = Intent(layer="L2", name=scene_name, context=dict(context or {}))
        with self._stack_lock:
            # 如果已有 L2 意图，先弹出（抢占）
            if any(i.layer == "L2" for i in self._intent_stack):
                self._stats["preemptionsTotal"] += 1
                self._emit("[mixer] preempting existing L2 intent")
            self._intent_stack.append(intent)
            # 限制栈深度
            if len(self._intent_stack) > MAX_INTENT_STACK_DEPTH:
                self._intent_stack = self._intent_stack[-MAX_INTENT_STACK_DEPTH:]

        # 4. 启动语音场景
        self._l2.start(scene_name, context)

    def pop_voice_action(self) -> None:
        """语音动作出栈（L2 结束）.

        - L2 释放关节
        - 如果 L1 在影子模式，开始恢复（从当前位置缓动到目标）
        """
        # 1. 停止 L2（会触发 _on_done 回调，但回调中会检查 L1 状态）
        self._l2.stop()

        # 2. 弹出意图栈中的 L2
        with self._stack_lock:
            self._intent_stack = [i for i in self._intent_stack if i.layer != "L2"]

        # 3. 恢复 L1（_l2.stop 的 _on_done 回调可能已经触发恢复，
        #    这里做幂等检查：只有 L1 还在 SHADOW 时才恢复）
        if self._l1.is_active() and self._l1.mode == TrackingMode.SHADOW:
            self._stats["recoveriesTotal"] += 1
            self._l1.start_recovery(duration=self._recover_duration)
            self._emit("[mixer] L1 starting recovery (from pop)")
        elif not self._l1.is_active():
            # L1 不在跑，关节归还给 L0
            self._transfer_ownership("L0", ALL_JOINTS)

    def _on_voice_action_done(self, scene_name: str) -> None:
        """语音场景完成后的回调."""
        # 弹出 L2 意图
        with self._stack_lock:
            self._intent_stack = [i for i in self._intent_stack if i.layer != "L2"]

        # 恢复 L1
        if self._l1.is_active():
            self._stats["recoveriesTotal"] += 1
            self._l1.start_recovery(duration=self._recover_duration)
            self._emit("[mixer] L1 starting recovery")
        else:
            # L1 不在跑，关节归还给 L0
            self._transfer_ownership("L0", ALL_JOINTS)

    # -- 公共 API: 视觉跟踪 --

    def update_tracking(self, target: dict[str, Any]) -> None:
        """视觉跟踪事件更新（L1）.

        - 如果 L2 在跑，只更新缓存（影子模式）
        - 如果 L2 不在跑，L1 正常输出到关节
        """
        self._stats["trackingEventsTotal"] += 1

        if self._l2.is_active():
            # L2 在跑，只更新缓存
            self._l1.update_target_buffer(target)
        else:
            # L2 不在跑
            if not self._l1.is_active():
                # L1 还没启动，启动并设为 ACTIVE
                self._l1.set_mode(TrackingMode.ACTIVE)
                self._transfer_ownership("L1", SERVO_KEYS)
            # 更新目标
            self._l1.update_target_buffer(target)
            with self._stack_lock:
                # 确保 L1 意图在栈中
                if not any(i.layer == "L1" for i in self._intent_stack):
                    self._intent_stack.append(Intent(layer="L1", name="track_target"))

    def clear_tracking(self, reason: str = "target_missing") -> None:
        """清除跟踪目标."""
        self._l1.clear_target(reason)
        self._transfer_ownership("L0", SERVO_KEYS)
        with self._stack_lock:
            self._intent_stack = [i for i in self._intent_stack if i.layer != "L1"]

    # -- 公共 API: 触摸事件 --

    def handle_touch(self, event_type: str, context: dict[str, Any] | None = None) -> None:
        """触摸事件处理（作为 L2 优先级）."""
        self._stats["touchEventsTotal"] += 1
        # 触摸事件触发 touch_affection 场景
        scene_map = {
            "touch_detected": "touch_affection",
            "hand_near": "touch_affection",
        }
        scene_name = scene_map.get(event_type, "touch_affection")
        self.push_voice_action(scene_name, context or {"touch_event": event_type})

    # -- 公共 API: 状态查询 --

    def get_state(self) -> dict[str, Any]:
        """获取混合器完整状态."""
        with self._ownership_lock:
            ownership = {j: {"owner": o.owner, "prevOwner": o.prev_owner} for j, o in self._joint_ownership.items()}
        with self._stack_lock:
            stack = [
                {"layer": i.layer, "name": i.name, "age": round(time.time() - i.created_at, 1)}
                for i in self._intent_stack
            ]
        return {
            "running": self._running,
            "ownership": ownership,
            "intentStack": stack,
            "l0": {"active": True},
            "l1": self._l1.get_state(),
            "l2": self._l2.get_state(),
            "stats": dict(self._stats),
        }

    # -- 主循环 --

    def _main_loop(self) -> None:
        """混合器主循环: 事件驱动 + 定期 tick."""
        # 订阅事件总线
        self._event_bus.subscribe(self._on_event)

        while not self._stop_event.is_set():
            try:
                # 1. 检查 L2 是否完成
                self._l2.check_done()

                # 2. tick 三层
                l2_active = self._l2.is_active()
                l1_outputting = self._l1.is_outputting()

                # L2 tick（如果有输出）
                # L2 的输出由 runtime 场景执行器处理，这里不直接 tick

                # L1 tick
                l1_cmd = self._l1.tick()

                # L0 tick（只在 L1/L2 都不输出时）
                l0_cmd = self._l0.tick(higher_layers_active=(l2_active or l1_outputting))

                # 3. 输出关节指令
                if l1_cmd:
                    self._apply_joint_command(l1_cmd)
                elif l0_cmd:
                    self._apply_joint_command(l0_cmd)

                # 4. 定期一致性检查
                now = time.time()
                if now - self._last_consistency_check > CONSISTENCY_CHECK_INTERVAL:
                    self._consistency_check()
                    self._last_consistency_check = now

                # 5. 等待下一个 tick
                self._stop_event.wait(self._tick_interval)

            except Exception:  # noqa: BLE001
                logger.exception("[mixer] main loop error")
                self._stop_event.wait(1.0)  # 出错后等 1 秒再重试

    # -- 事件处理 --

    def _on_event(self, event: MixerEvent) -> None:
        """处理来自事件总线的事件."""
        try:
            if event.source == EVENT_SOURCE_VOICE:
                if event.event_type == "scene":
                    self.push_voice_action(event.payload.get("scene", ""), event.payload.get("context"))
                elif event.event_type == "scene_done":
                    self.pop_voice_action()

            elif event.source == EVENT_SOURCE_VISION:
                if event.event_type == "tracking":
                    target = event.payload
                    if target.get("tracking", {}).get("target_present"):
                        self.update_tracking(target)
                    else:
                        self.clear_tracking("target_missing")

            elif event.source == EVENT_SOURCE_TOUCH:
                self.handle_touch(event.event_type, event.payload)

            elif event.source == EVENT_SOURCE_CONSOLE:
                if event.event_type == "scene":
                    self.push_voice_action(event.payload.get("scene", ""), event.payload.get("context"))

        except Exception:  # noqa: BLE001
            logger.exception("[mixer] event handler error")

    # -- 关节控制权管理 --

    def _transfer_ownership(self, new_owner: str, joints: tuple[str, ...]) -> None:
        """转移关节控制权."""
        with self._ownership_lock:
            for joint in joints:
                if joint in self._joint_ownership:
                    current = self._joint_ownership[joint]
                    if current.owner != new_owner:
                        current.prev_owner = current.owner
                        current.owner = new_owner

    def _restore_ownership(self, owner: str) -> None:
        """恢复关节控制权到指定层."""
        with self._ownership_lock:
            for joint, ownership in self._joint_ownership.items():
                if ownership.owner == "L2" and ownership.prev_owner == owner:
                    ownership.owner = owner

    # -- 关节指令输出 --

    def _apply_joint_command(self, cmd: dict[str, Any]) -> None:
        """应用关节指令到硬件（通过 runtime）."""
        if not self._runtime:
            return
        layer = cmd.get("_layer", "L0")
        try:
            if "servos" in cmd:
                servo_cmd = cmd["servos"]
                payload = {"mode": "absolute", **servo_cmd}
                # 通过 runtime 的 client 发送
                client = self._runtime.get_client()
                client.control(payload)
            elif "led" in cmd:
                led_cmd = cmd["led"]
                client = self._runtime.get_client()
                client.set_led(led_cmd)
        except Exception as exc:  # noqa: BLE001
            self._emit(f"[mixer] joint command error ({layer}): {exc}")

    # -- runtime 集成方法 --

    def _run_scene_via_runtime(self, scene_name: str, context: dict[str, Any]) -> None:
        """通过 runtime 启动场景."""
        if not self._runtime:
            self._emit(f"[mixer] dry-run: would start scene {scene_name}")
            return
        try:
            self._runtime.start_scene(scene_name, scene_context=context)
        except Exception as exc:  # noqa: BLE001
            self._emit(f"[mixer] start_scene error: {exc}")

    def _stop_scene_via_runtime(self) -> None:
        """通过 runtime 停止场景."""
        if not self._runtime:
            return
        try:
            self._runtime.stop_scene()
        except Exception as exc:  # noqa: BLE001
            self._emit(f"[mixer] stop_scene error: {exc}")

    def _is_scene_running_via_runtime(self) -> bool:
        """检查 runtime 侧场景是否在跑."""
        if not self._runtime:
            return False
        try:
            with self._runtime._state_lock:  # noqa: SLF001
                return self._runtime._running_scene is not None  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return False

    def _read_current_joints(self) -> dict[str, int]:
        """读取当前关节位置."""
        if not self._runtime:
            return {}
        try:
            with self._runtime._state_lock:  # noqa: SLF001
                return dict(self._runtime._tracking_servo_state)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return {}

    def _compute_tracking_from_target(self, target: dict[str, Any]) -> dict[str, int]:
        """从视觉目标计算舵机角度（委托给 runtime 的逻辑）."""
        if not self._runtime:
            return {}
        try:
            # 复用 runtime 的跟踪计算逻辑
            return self._runtime._compute_tracking_servo_angles(target)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return {}

    # -- 一致性检查 --

    def _consistency_check(self) -> None:
        """定期一致性检查，修复不一致状态."""
        self._stats["consistencyChecksTotal"] += 1
        fixes = 0

        # 检查 1: L2 不在跑时，L1 不应该在 SHADOW 模式
        if not self._l2.is_active():
            l1_state = self._l1.get_state()
            if l1_state["mode"] == TrackingMode.SHADOW.value:
                self._emit("[mixer-consistency] L1 stuck in SHADOW, starting recovery")
                self._l1.start_recovery(duration=self._recover_duration)
                fixes += 1

        # 检查 2: 意图栈深度
        with self._stack_lock:
            if len(self._intent_stack) > MAX_INTENT_STACK_DEPTH:
                self._intent_stack = self._intent_stack[-MAX_INTENT_STACK_DEPTH:]
                fixes += 1

        # 检查 3: 关节控制权一致性
        with self._ownership_lock:
            l2_active = self._l2.is_active()
            for joint, ownership in self._joint_ownership.items():
                if not l2_active and ownership.owner == "L2":
                    # L2 不在跑但关节还归 L2，归还给 L1 或 L0
                    ownership.owner = ownership.prev_owner or "L0"
                    fixes += 1

        if fixes:
            self._stats["consistencyFixesTotal"] += fixes
            self._emit(f"[mixer-consistency] {fixes} fixes applied")
