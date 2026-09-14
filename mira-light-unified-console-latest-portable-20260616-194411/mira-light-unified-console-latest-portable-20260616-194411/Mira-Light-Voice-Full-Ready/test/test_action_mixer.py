"""Mira Light 动作混合器单元测试.

验证混合器的核心逻辑:
    - 事件总线收发
    - 关节控制权转移
    - 意图栈入栈/出栈
    - 影子模式切换
    - 缓动恢复
    - 一致性检查
    - 长时间稳定性

运行: python -m pytest test_action_mixer.py -v
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 把 scripts 目录加入路径
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mira_event_bus import (
    EventBus,
    MixerEvent,
    EVENT_SOURCE_VOICE,
    EVENT_SOURCE_VISION,
    EVENT_SOURCE_TOUCH,
    EVENT_SOURCE_IDLE,
    emit_voice,
    emit_vision,
    emit_touch,
)
from mira_action_mixer import (
    ActionMixer,
    BackgroundLayer,
    TrackingLayer,
    VoiceActionLayer,
    TrackingMode,
    JointOwnership,
    Intent,
    ease_in_out,
    ease_step,
    LayerPriority,
    MAX_INTENT_STACK_DEPTH,
    RECOVER_DURATION_DEFAULT,
)


# ---------------------------------------------------------------------------
# Mock runtime
# ---------------------------------------------------------------------------


class MockRuntime:
    """模拟 MiraLightRuntime，用于测试."""

    def __init__(self):
        self.log_messages: list[str] = []
        self._running_scene: str | None = None
        self._tracking_servo_state: dict[str, int] = {"servo1": 90, "servo2": 96, "servo3": 98, "servo4": 90}
        self._state_lock = __import__("threading").Lock()
        self._action_mixer = None
        self._client = MagicMock()
        self.started_scenes: list[tuple[str, dict]] = []
        self.stopped_scenes: list[str] = []

    def log(self, msg: str) -> None:
        self.log_messages.append(msg)

    def set_action_mixer(self, mixer) -> None:
        self._action_mixer = mixer

    def get_client(self):
        return self._client

    def start_scene(self, scene_name: str, scene_context: dict | None = None) -> None:
        self._running_scene = scene_name
        self.started_scenes.append((scene_name, scene_context or {}))

    def stop_scene(self) -> None:
        if self._running_scene:
            self.stopped_scenes.append(self._running_scene)
        self._running_scene = None

    def _compute_tracking_servo_angles(self, event: dict) -> dict[str, int]:
        control_hint = event.get("control_hint", {})
        return {
            "servo1": 90 + int(float(control_hint.get("yaw_error_norm", 0)) * 18),
            "servo2": 96,
            "servo3": 98,
            "servo4": 90,
        }


# ---------------------------------------------------------------------------
# 事件总线测试
# ---------------------------------------------------------------------------


class TestEventBus(unittest.TestCase):
    """事件总线测试."""

    def test_emit_and_recv(self):
        """事件发送和接收."""
        bus = EventBus()
        bus.emit(EVENT_SOURCE_VOICE, "scene", {"scene": "wake_up"})
        event = bus.recv(timeout=0.1)
        self.assertIsNotNone(event)
        self.assertEqual(event.source, EVENT_SOURCE_VOICE)
        self.assertEqual(event.event_type, "scene")
        self.assertEqual(event.payload["scene"], "wake_up")

    def test_priority(self):
        """事件优先级数值正确."""
        bus = EventBus()
        evt_voice = bus.emit(EVENT_SOURCE_VOICE, "scene", {})
        evt_vision = bus.emit(EVENT_SOURCE_VISION, "tracking", {})
        evt_idle = bus.emit(EVENT_SOURCE_IDLE, "tick", {})
        # 语音优先级数值最高
        self.assertGreater(evt_voice.priority, evt_vision.priority)
        self.assertGreater(evt_vision.priority, evt_idle.priority)

    def test_handler_subscription(self):
        """handler 订阅."""
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))
        bus.emit(EVENT_SOURCE_VOICE, "scene", {"scene": "test"})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["scene"], "test")

    def test_queue_overflow_drops_low_priority(self):
        """队列满时丢弃低优先级事件."""
        bus = EventBus(max_history=10)
        bus._max_queue = 3
        # 填满队列
        bus.emit(EVENT_SOURCE_VISION, "tracking", {"i": 1})
        bus.emit(EVENT_SOURCE_VISION, "tracking", {"i": 2})
        bus.emit(EVENT_SOURCE_VISION, "tracking", {"i": 3})
        # 再发一个语音事件，应该丢弃一个视觉事件
        bus.emit(EVENT_SOURCE_VOICE, "scene", {"scene": "test"})
        events = bus.drain()
        # 语音事件应该在队列中
        self.assertTrue(any(e.source == EVENT_SOURCE_VOICE for e in events))

    def test_convenience_functions(self):
        """便捷工厂函数."""
        bus = EventBus()
        emit_voice(bus, "wake_up", {"context": "test"})
        emit_vision(bus, {"tracking": {"target_present": True}})
        emit_touch(bus, "touch_detected", {"side": "left"})
        events = bus.drain()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].source, EVENT_SOURCE_VOICE)
        self.assertEqual(events[1].source, EVENT_SOURCE_VISION)
        self.assertEqual(events[2].source, EVENT_SOURCE_TOUCH)


# ---------------------------------------------------------------------------
# 缓动函数测试
# ---------------------------------------------------------------------------


class TestEasing(unittest.TestCase):
    """缓动函数测试."""

    def test_ease_in_out(self):
        """ease-in-out 曲线."""
        self.assertAlmostEqual(ease_in_out(0.0), 0.0)
        self.assertAlmostEqual(ease_in_out(1.0), 1.0)
        self.assertAlmostEqual(ease_in_out(0.5), 0.5)
        # 中点应该是对称的
        self.assertAlmostEqual(ease_in_out(0.25) + ease_in_out(0.75), 1.0)

    def test_ease_step(self):
        """单步平滑."""
        self.assertEqual(ease_step(90, 100, alpha=0.5), 95)
        self.assertEqual(ease_step(90, 91, alpha=0.5), 91)
        self.assertEqual(ease_step(90, 90, alpha=0.5), 90)


# ---------------------------------------------------------------------------
# 跟踪层测试
# ---------------------------------------------------------------------------


class TestTrackingLayer(unittest.TestCase):
    """跟踪层测试（影子模式 + 恢复）."""

    def test_mode_transitions(self):
        """模式切换: IDLE → ACTIVE → SHADOW → RECOVER → ACTIVE."""
        layer = TrackingLayer(
            emit=lambda msg: None,
            compute_tracking=lambda target: {"servo1": 100, "servo2": 96, "servo3": 98, "servo4": 90},
            read_joints=lambda: {"servo1": 90, "servo2": 96, "servo3": 98, "servo4": 90},
        )
        self.assertEqual(layer.mode, TrackingMode.IDLE)

        # IDLE → ACTIVE
        layer.set_mode(TrackingMode.ACTIVE)
        self.assertEqual(layer.mode, TrackingMode.ACTIVE)
        self.assertTrue(layer.is_outputting())

        # ACTIVE → SHADOW（语音到来）
        layer.snapshot_joints()
        layer.set_mode(TrackingMode.SHADOW)
        self.assertEqual(layer.mode, TrackingMode.SHADOW)
        self.assertFalse(layer.is_outputting())  # 影子模式不输出
        self.assertTrue(layer.is_active())  # 但仍然是活跃的

        # SHADOW → RECOVER（语音结束）
        layer.update_target_buffer({"tracking": {"target_present": True}})
        layer.start_recovery(duration=0.1)
        self.assertEqual(layer.mode, TrackingMode.RECOVER)
        self.assertTrue(layer.is_outputting())  # 恢复模式输出

        # RECOVER → ACTIVE（恢复完成）
        time.sleep(0.15)
        layer.tick()  # 触发恢复完成
        self.assertEqual(layer.mode, TrackingMode.ACTIVE)

    def test_shadow_does_not_output(self):
        """影子模式不输出关节指令."""
        layer = TrackingLayer(
            emit=lambda msg: None,
            compute_tracking=lambda target: {"servo1": 100},
            read_joints=lambda: {"servo1": 90},
        )
        layer.set_mode(TrackingMode.SHADOW)
        layer.update_target_buffer({"tracking": {"target_present": True}})
        result = layer.tick()
        self.assertIsNone(result)  # 影子模式返回 None

    def test_active_outputs(self):
        """ACTIVE 模式输出关节指令."""
        layer = TrackingLayer(
            emit=lambda msg: None,
            compute_tracking=lambda target: {"servo1": 100, "servo2": 96, "servo3": 98, "servo4": 90},
            read_joints=lambda: {"servo1": 90, "servo2": 96, "servo3": 98, "servo4": 90},
        )
        layer.set_mode(TrackingMode.ACTIVE)
        layer.update_target_buffer({"tracking": {"target_present": True}})
        result = layer.tick()
        self.assertIsNotNone(result)
        self.assertIn("servos", result)
        self.assertEqual(result["servos"]["servo1"], 100)

    def test_snapshot_and_recover(self):
        """快照和恢复."""
        layer = TrackingLayer(
            emit=lambda msg: None,
            compute_tracking=lambda target: {"servo1": 120, "servo2": 96, "servo3": 98, "servo4": 90},
            read_joints=lambda: {"servo1": 90, "servo2": 96, "servo3": 98, "servo4": 90},
        )
        # 快照
        layer.snapshot_joints()
        self.assertEqual(layer._joint_snapshot["servo1"], 90)

        # 恢复
        layer.update_target_buffer({"tracking": {"target_present": True}})
        layer.start_recovery(duration=0.05)
        self.assertEqual(layer.mode, TrackingMode.RECOVER)

        # 等待恢复完成
        time.sleep(0.06)
        result = layer.tick()
        self.assertEqual(layer.mode, TrackingMode.ACTIVE)

    def test_clear_target(self):
        """目标丢失清理."""
        layer = TrackingLayer(emit=lambda msg: None)
        layer.set_mode(TrackingMode.ACTIVE)
        layer.clear_target("target_missing")
        self.assertEqual(layer.mode, TrackingMode.IDLE)


# ---------------------------------------------------------------------------
# 语音动作层测试
# ---------------------------------------------------------------------------


class TestVoiceActionLayer(unittest.TestCase):
    """语音动作层测试."""

    def test_start_and_stop(self):
        """启动和停止."""
        started = []
        stopped = []
        layer = VoiceActionLayer(
            emit=lambda msg: None,
            run_scene=lambda name, ctx: started.append((name, ctx)),
            stop_scene=lambda: stopped.append(True),
            is_scene_running=lambda: False,
        )
        self.assertFalse(layer.is_active())

        layer.start("wake_up", {"context": "test"})
        self.assertTrue(layer.is_active())
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0][0], "wake_up")

        layer.stop()
        self.assertFalse(layer.is_active())
        self.assertEqual(len(stopped), 1)

    def test_preempt_existing(self):
        """抢占已有场景."""
        started = []
        stopped = []
        layer = VoiceActionLayer(
            emit=lambda msg: None,
            run_scene=lambda name, ctx: started.append(name),
            stop_scene=lambda: stopped.append(True),
            is_scene_running=lambda: False,
        )
        layer.start("wake_up", {})
        layer.start("cute_probe", {})  # 抢占
        self.assertEqual(len(stopped), 1)  # 先停止旧的
        self.assertEqual(len(started), 2)  # 再启动新的

    def test_check_done(self):
        """检查场景完成."""
        is_running = [True]
        layer = VoiceActionLayer(
            emit=lambda msg: None,
            run_scene=lambda name, ctx: None,
            stop_scene=lambda: None,
            is_scene_running=lambda: is_running[0],
        )
        layer.start("wake_up", {})
        self.assertFalse(layer.check_done())  # 还在跑

        is_running[0] = False
        self.assertTrue(layer.check_done())  # 完成了
        self.assertFalse(layer.is_active())


# ---------------------------------------------------------------------------
# ActionMixer 集成测试
# ---------------------------------------------------------------------------


class TestActionMixer(unittest.TestCase):
    """动作混合器集成测试."""

    def setUp(self):
        self.runtime = MockRuntime()
        self.mixer = ActionMixer(
            runtime=self.runtime,
            event_bus=EventBus(),
            emit=self.runtime.log,
            recover_duration=0.05,  # 测试用短恢复时间
        )

    def tearDown(self):
        self.mixer.stop()

    def test_voice_action_pushes_l2(self):
        """语音动作入栈 L2."""
        self.mixer.push_voice_action("wake_up", {"context": "test"})
        self.assertTrue(self.mixer._l2.is_active())
        self.assertEqual(len(self.runtime.started_scenes), 1)
        self.assertEqual(self.runtime.started_scenes[0][0], "wake_up")

    def test_voice_action_pop_restores_l1(self):
        """语音动作出栈后恢复 L1."""
        # 先启动跟踪（需要设置 target_buffer 供恢复使用）
        self.mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {"yaw_error_norm": 0.0}})
        self.assertEqual(self.mixer._l1.mode, TrackingMode.ACTIVE)

        # 语音到来 → L1 进入影子模式
        self.mixer.push_voice_action("cute_probe", {})
        self.assertEqual(self.mixer._l1.mode, TrackingMode.SHADOW)

        # 语音结束 → L1 恢复
        self.mixer.pop_voice_action()
        self.assertIn(self.mixer._l1.mode, (TrackingMode.RECOVER, TrackingMode.ACTIVE))

        # 等待恢复完成并手动 tick 推进（测试中没启动主循环）
        time.sleep(0.08)
        self.mixer._l1.tick()
        self.assertEqual(self.mixer._l1.mode, TrackingMode.ACTIVE)

    def test_vision_cached_during_voice(self):
        """语音期间视觉事件被缓存."""
        # 启动跟踪
        self.mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {"yaw_error_norm": 0.0}})
        # 语音到来
        self.mixer.push_voice_action("cute_probe", {})
        # 视觉事件到来（应该被缓存，不输出）
        self.mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {"yaw_error_norm": 0.5}})
        # 缓存应该有目标
        self.assertTrue(self.mixer._l1._target_buffer)

    def test_ownership_transfer(self):
        """关节控制权转移."""
        # 初始：所有关节归 L0
        for joint in ("servo1", "servo2", "servo3", "servo4", "led"):
            self.assertEqual(self.mixer._joint_ownership[joint].owner, "L0")

        # 启动跟踪 → servo 归 L1
        self.mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {}})
        for joint in ("servo1", "servo2", "servo3", "servo4"):
            self.assertEqual(self.mixer._joint_ownership[joint].owner, "L1")

        # 语音到来 → 所有关节归 L2
        self.mixer.push_voice_action("cute_probe", {})
        for joint in ("servo1", "servo2", "servo3", "servo4", "led"):
            self.assertEqual(self.mixer._joint_ownership[joint].owner, "L2")

    def test_intent_stack_depth(self):
        """意图栈深度限制."""
        # 连续入栈多个 L2
        for i in range(MAX_INTENT_STACK_DEPTH + 2):
            self.mixer.push_voice_action(f"scene_{i}", {})
        # 栈深度不超过最大值
        self.assertLessEqual(len(self.mixer._intent_stack), MAX_INTENT_STACK_DEPTH)

    def test_consistency_check_fixes_shadow_stuck(self):
        """一致性检查修复 L1 卡在 SHADOW 模式."""
        # 先设置 target_buffer（供恢复使用）
        self.mixer._l1.update_target_buffer({"tracking": {"target_present": True}, "control_hint": {"yaw_error_norm": 0.0}})
        # 模拟 L1 卡在 SHADOW（L2 不在跑）
        self.mixer._l1.set_mode(TrackingMode.ACTIVE)
        self.mixer._l1.snapshot_joints()
        self.mixer._l1.set_mode(TrackingMode.SHADOW)
        # L2 不在跑
        self.assertFalse(self.mixer._l2.is_active())

        # 执行一致性检查
        self.mixer._consistency_check()

        # L1 应该开始恢复
        self.assertIn(self.mixer._l1.mode, (TrackingMode.RECOVER, TrackingMode.ACTIVE))
        self.assertGreater(self.mixer._stats["consistencyFixesTotal"], 0)

    def test_touch_event_triggers_l2(self):
        """触摸事件触发 L2."""
        self.mixer.handle_touch("touch_detected", {"side": "left"})
        self.assertTrue(self.mixer._l2.is_active())
        self.assertEqual(self.runtime.started_scenes[-1][0], "touch_affection")

    def test_get_state(self):
        """状态查询."""
        state = self.mixer.get_state()
        self.assertIn("ownership", state)
        self.assertIn("intentStack", state)
        self.assertIn("l0", state)
        self.assertIn("l1", state)
        self.assertIn("l2", state)
        self.assertIn("stats", state)

    def test_stats_tracking(self):
        """统计计数."""
        self.mixer.push_voice_action("wake_up", {})
        self.assertEqual(self.mixer._stats["voiceActionsTotal"], 1)

        self.mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {}})
        self.assertEqual(self.mixer._stats["trackingEventsTotal"], 1)

        self.mixer.handle_touch("touch_detected", {})
        self.assertEqual(self.mixer._stats["touchEventsTotal"], 1)


# ---------------------------------------------------------------------------
# 长时间稳定性测试
# ---------------------------------------------------------------------------


class TestLongRunningStability(unittest.TestCase):
    """长时间稳定性测试."""

    def test_50_voice_tracking_switches(self):
        """语音和跟踪来回切换 50 次，检查状态一致性."""
        runtime = MockRuntime()
        mixer = ActionMixer(
            runtime=runtime,
            event_bus=EventBus(),
            emit=runtime.log,
            recover_duration=0.01,  # 极短恢复时间，加速测试
        )

        try:
            for i in range(50):
                # 启动跟踪（带 control_hint 确保 target_buffer 有值）
                mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {"yaw_error_norm": 0.0}})
                self.assertEqual(mixer._l1.mode, TrackingMode.ACTIVE)

                # 语音到来
                mixer.push_voice_action(f"scene_{i}", {})
                self.assertEqual(mixer._l1.mode, TrackingMode.SHADOW)
                self.assertTrue(mixer._l2.is_active())

                # 语音结束
                mixer.pop_voice_action()
                # L1 应该开始恢复或已恢复
                self.assertIn(mixer._l1.mode, (TrackingMode.RECOVER, TrackingMode.ACTIVE))

                # 等待恢复完成并手动 tick 推进
                time.sleep(0.02)
                mixer._l1.tick()

                # 一致性检查：L1 不应该卡在 SHADOW
                self.assertNotEqual(mixer._l1.mode, TrackingMode.SHADOW)
                # L2 应该不在跑
                self.assertFalse(mixer._l2.is_active())

            # 50 次切换后，统计应该正确
            self.assertEqual(mixer._stats["voiceActionsTotal"], 50)
            self.assertEqual(mixer._stats["trackingEventsTotal"], 50)

        finally:
            mixer.stop()

    def test_no_deadlock_under_rapid_events(self):
        """快速事件不产生死锁."""
        runtime = MockRuntime()
        mixer = ActionMixer(
            runtime=runtime,
            event_bus=EventBus(),
            emit=runtime.log,
            recover_duration=0.01,
        )

        try:
            # 快速交替发送语音和视觉事件
            for i in range(100):
                if i % 3 == 0:
                    mixer.push_voice_action(f"scene_{i}", {})
                elif i % 3 == 1:
                    mixer.update_tracking({"tracking": {"target_present": True}, "control_hint": {}})
                else:
                    mixer.pop_voice_action()

            # 最终状态应该是一致的
            state = mixer.get_state()
            self.assertIsNotNone(state)

            # 意图栈深度不超过最大值
            self.assertLessEqual(len(state["intentStack"]), MAX_INTENT_STACK_DEPTH)

        finally:
            mixer.stop()


# ---------------------------------------------------------------------------
# 运行测试
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main(verbosity=2)
