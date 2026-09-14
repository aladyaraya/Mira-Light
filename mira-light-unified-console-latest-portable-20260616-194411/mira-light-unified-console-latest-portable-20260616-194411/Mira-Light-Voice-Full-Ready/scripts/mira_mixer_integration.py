"""Mira Light 动作混合器集成入口.

把 ActionMixer + EventBus + VoiceEventAdapter 组装起来，
提供一个简单的启动函数，替代之前的 RealtimeActionOrchestrator。

使用方式:
    from mira_mixer_integration import setup_mixer

    # 在 runtime 初始化后
    mixer, event_bus, adapter = setup_mixer(
        runtime=runtime,
        director_url="http://127.0.0.1:8790",
    )

    # 在 StepFun 事件循环中
    for event in stepfun_events:
        adapter.handle_event(event)

    # 在视觉跟踪回调中
    event_bus.emit("vision", "tracking", tracking_data)

    # 关闭时
    mixer.stop()

设计文档: docs/plans/2026-06-21-action-mixer-design.md
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mira_action_mixer import ActionMixer
from mira_event_bus import EventBus, emit_voice, emit_voice_done, emit_vision, emit_touch, emit_console
from mira_voice_event_adapter import VoiceEventAdapter

logger = logging.getLogger(__name__)


def setup_mixer(
    runtime: Any,
    *,
    director_url: str | None = None,
    director_token: str | None = None,
    source: str = "stepfun-realtime",
    recover_duration: float = 0.8,
    auto_start: bool = True,
) -> tuple[ActionMixer, EventBus, VoiceEventAdapter]:
    """初始化动作混合器系统.

    Args:
        runtime: MiraLightRuntime 实例
        director_url: 导演台 URL（用于语音阶段快速动作）
        director_token: 导演台认证 token
        source: 事件来源标识
        recover_duration: 跟踪恢复缓动时长（秒）
        auto_start: 是否自动启动混合器主循环

    Returns:
        (mixer, event_bus, adapter) 三元组

    使用后记得调用 mixer.stop() 清理资源。
    """
    # 1. 创建事件总线
    event_bus = EventBus()

    # 2. 创建动作混合器
    mixer = ActionMixer(
        runtime=runtime,
        event_bus=event_bus,
        emit=runtime.log if hasattr(runtime, "log") else None,
        recover_duration=recover_duration,
    )

    # 3. 把混合器注入 runtime（启用委托模式）
    runtime.set_action_mixer(mixer)

    # 4. 创建语音事件适配器
    adapter = VoiceEventAdapter(
        event_bus=event_bus,
        director_url=director_url,
        director_token=director_token,
        source=source,
        voice_state_enabled=bool(director_url),
        assistant_action_enabled=True,
        semantic_action_enabled=True,
    )

    # 5. 启动混合器主循环
    if auto_start:
        mixer.start()

    runtime.log("[mixer-integration] action mixer system ready")
    return mixer, event_bus, adapter


def teardown_mixer(mixer: ActionMixer) -> None:
    """清理混合器系统."""
    mixer.stop()
    logger.info("[mixer-integration] action mixer system stopped")


# ---------------------------------------------------------------------------
# 环境变量配置
# ---------------------------------------------------------------------------


def is_mixer_enabled() -> bool:
    """检查是否启用了动作混合器（环境变量控制）."""
    return os.environ.get("MIRA_ACTION_MIXER_ENABLED", "1").strip().lower() in {
        "1", "true", "yes", "on",
    }


def get_recover_duration() -> float:
    """从环境变量获取跟踪恢复时长."""
    try:
        return float(os.environ.get("MIRA_MIXER_RECOVER_DURATION", "0.8"))
    except ValueError:
        return 0.8


# ---------------------------------------------------------------------------
# 兼容性说明
# ---------------------------------------------------------------------------

"""
与现有代码的兼容性:

1. MiraLightRuntime:
   - set_action_mixer() 注入混合器
   - apply_tracking_event() 有混合器时委托，无混合器时保持原逻辑
   - _prepare_run() 有混合器时不抛异常，改为平滑切换
   - _compute_tracking_servo_angles() 新增方法，供混合器复用

2. RealtimeActionOrchestrator:
   - 不删除，保留作为 fallback
   - VoiceEventAdapter 复用其纯逻辑部分（关键词映射、意图分类）
   - 通过 MIRA_ACTION_MIXER_ENABLED=0 可回退到原状态机

3. StepFun 实时语音:
   - mira_windows_full_duplex_voice.py 的 receive_loop 中
   - 把 orchestrator.handle_event(event) 替换为 adapter.handle_event(event)
   - 在 response.done 事件时调用 adapter.on_response_done()

4. 控制台:
   - 控制台手动触发场景时，通过 emit_console() 发送事件
   - 混合器会按优先级处理（控制台优先级低于语音，高于跟踪）

5. 触摸事件:
   - 触摸检测回调中通过 emit_touch() 发送事件
   - 混合器把触摸作为 L2 优先级处理
"""
