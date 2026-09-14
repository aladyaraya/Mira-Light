"""Mira Light 事件总线.

统一接收语音 / 视觉 / 触摸事件，转发给动作混合器 (ActionMixer)。
替代之前"直接调 runtime API + 异常补救"的冲突处理方式，
改为事件驱动的统一仲裁。

事件优先级（由高到低）:
    - voice  : 语音触发的场景动作 (L2)
    - touch  : 触摸/近距输入 (L2)
    - vision : 视觉跟踪事件 (L1，背景修正)
    - idle   : 背景微动 (L0，混合器内部产生)

设计要点:
    - 事件驱动，不轮询，不需要 cooldown 计时器
    - 视觉事件在语音期间被缓存，不丢弃
    - 语音事件总是入栈 L2，跟踪自动让出关节
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 事件类型常量
# ---------------------------------------------------------------------------

EVENT_SOURCE_VOICE = "voice"
EVENT_SOURCE_VISION = "vision"
EVENT_SOURCE_TOUCH = "touch"
EVENT_SOURCE_IDLE = "idle"
EVENT_SOURCE_CONSOLE = "console"

# 事件优先级：数值越大优先级越高
EVENT_PRIORITY = {
    EVENT_SOURCE_VOICE: 30,
    EVENT_SOURCE_TOUCH: 25,
    EVENT_SOURCE_CONSOLE: 20,
    EVENT_SOURCE_VISION: 10,
    EVENT_SOURCE_IDLE: 0,
}


@dataclass
class MixerEvent:
    """混合器事件的统一表示."""

    source: str  # voice / vision / touch / idle / console
    event_type: str  # scene / tracking / touch_detected / ...
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0

    def __post_init__(self) -> None:
        if self.priority == 0:
            self.priority = EVENT_PRIORITY.get(self.source, 0)


# ---------------------------------------------------------------------------
# 同步事件总线（线程安全）
# ---------------------------------------------------------------------------


class EventBus:
    """线程安全的事件总线.

    支持两种使用方式:
        1. 同步回调: 注册 handler，事件到来时直接调用
        2. 队列消费: 用 recv() 在循环中消费（适合 asyncio 环境）

    在 Mira Light 的架构中，语音/视觉/触摸事件来自不同线程，
    所以事件总线内部用 threading.Lock 保护，handler 调用在线程池中执行。
    """

    def __init__(self, max_history: int = 200) -> None:
        self._lock = threading.Lock()
        self._handlers: list[Callable[[MixerEvent], None]] = []
        self._queue: deque[MixerEvent] = deque()
        self._cond = threading.Condition(self._lock)
        self._history: deque[dict[str, Any]] = deque(maxlen=max_history)
        self._dropped_count = 0
        self._max_queue = 100

    # -- 注册 / 注销 --

    def subscribe(self, handler: Callable[[MixerEvent], None]) -> None:
        """注册一个同步 handler，事件到来时会被调用."""
        with self._lock:
            self._handlers.append(handler)

    def unsubscribe(self, handler: Callable[[MixerEvent], None]) -> None:
        with self._lock:
            try:
                self._handlers.remove(handler)
            except ValueError:
                pass

    # -- 发送事件 --

    def emit(
        self,
        source: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int | None = None,
    ) -> MixerEvent:
        """发送一个事件到总线.

        线程安全，可以在任何线程调用。
        事件会被放入队列并通知所有 handler。
        """
        event = MixerEvent(
            source=source,
            event_type=event_type,
            payload=payload or {},
            priority=priority if priority is not None else EVENT_PRIORITY.get(source, 0),
        )

        with self._cond:
            # 记录历史
            self._history.append(
                {
                    "source": source,
                    "type": event_type,
                    "priority": event.priority,
                    "timestamp": event.timestamp,
                    "payload_keys": list(event.payload.keys()),
                }
            )
            # 入队（限长，防止视觉事件洪泛）
            if len(self._queue) >= self._max_queue:
                # 丢弃最低优先级的旧事件
                self._drop_lowest_priority()
                self._dropped_count += 1
            self._queue.append(event)
            self._cond.notify_all()

        # 在锁外调用 handler，避免死锁
        self._dispatch_to_handlers(event)
        return event

    # -- 消费事件 --

    def recv(self, timeout: float | None = None) -> MixerEvent | None:
        """同步消费一个事件（阻塞或带超时）."""
        with self._cond:
            if not self._queue:
                if not self._cond.wait(timeout=timeout):
                    return None
            if not self._queue:
                return None
            return self._queue.popleft()

    def drain(self) -> list[MixerEvent]:
        """取出所有待处理事件（非阻塞）."""
        with self._cond:
            events = list(self._queue)
            self._queue.clear()
        return events

    def has_pending(self) -> bool:
        with self._lock:
            return len(self._queue) > 0

    # -- 状态查询 --

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "queueLength": len(self._queue),
                "historyLength": len(self._history),
                "droppedCount": self._dropped_count,
                "handlerCount": len(self._handlers),
            }

    def get_recent_history(self, count: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)[-count:]

    # -- 内部方法 --

    def _dispatch_to_handlers(self, event: MixerEvent) -> None:
        """在锁外调用所有 handler."""
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                logger.exception("EventBus handler error for event %s", event.source)

    def _drop_lowest_priority(self) -> None:
        """队列满时丢弃最低优先级的旧事件（保留语音事件）."""
        if not self._queue:
            return
        # 找到最低优先级的事件索引（优先丢弃 vision/idle）
        min_idx = 0
        min_prio = self._queue[0].priority
        for i, evt in enumerate(self._queue):
            if evt.priority < min_prio:
                min_prio = evt.priority
                min_idx = i
        # 只丢弃非语音事件
        if self._queue[min_idx].source != EVENT_SOURCE_VOICE:
            del self._queue[min_idx]
        else:
            # 全是语音事件，丢弃最老的
            self._queue.popleft()


# ---------------------------------------------------------------------------
# 异步事件总线（兼容 asyncio 环境）
# ---------------------------------------------------------------------------


class AsyncEventBus:
    """asyncio 兼容的事件总线.

    用于 StepFun 实时语音等异步环境。
    内部包装同步 EventBus，提供 async 接口。
    """

    def __init__(self, sync_bus: EventBus | None = None) -> None:
        self._sync = sync_bus or EventBus()
        self._async_queue: asyncio.Queue[MixerEvent] = asyncio.Queue()
        self._bridge_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def emit(
        self,
        source: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int | None = None,
    ) -> MixerEvent:
        """发送事件（线程安全，可在任意线程调用）."""
        event = self._sync.emit(source, event_type, payload, priority=priority)
        # 如果在 asyncio 线程内，直接放入异步队列
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._async_queue.put_nowait, event)
        return event

    async def recv(self) -> MixerEvent:
        """异步消费事件."""
        return await self._async_queue.get()

    async def start_bridge(self) -> None:
        """启动同步→异步桥接（如果需要从同步线程消费）."""
        self._loop = asyncio.get_running_loop()

    def stop_bridge(self) -> None:
        if self._bridge_task and not self._bridge_task.done():
            self._bridge_task.cancel()
        self._bridge_task = None

    @property
    def sync_bus(self) -> EventBus:
        return self._sync


# ---------------------------------------------------------------------------
# 便捷工厂函数
# ---------------------------------------------------------------------------


def emit_voice(event_bus: EventBus, scene_name: str, context: dict[str, Any] | None = None) -> MixerEvent:
    """发送语音场景事件."""
    return event_bus.emit(
        EVENT_SOURCE_VOICE,
        "scene",
        {"scene": scene_name, "context": context or {}},
    )


def emit_voice_done(event_bus: EventBus, scene_name: str) -> MixerEvent:
    """发送语音场景结束事件."""
    return event_bus.emit(
        EVENT_SOURCE_VOICE,
        "scene_done",
        {"scene": scene_name},
    )


def emit_vision(event_bus: EventBus, target: dict[str, Any]) -> MixerEvent:
    """发送视觉跟踪事件."""
    return event_bus.emit(
        EVENT_SOURCE_VISION,
        "tracking",
        target,
    )


def emit_touch(event_bus: EventBus, event_type: str, context: dict[str, Any] | None = None) -> MixerEvent:
    """发送触摸事件."""
    return event_bus.emit(
        EVENT_SOURCE_TOUCH,
        event_type,
        context or {},
    )


def emit_console(event_bus: EventBus, scene_name: str, context: dict[str, Any] | None = None) -> MixerEvent:
    """发送控制台手动触发事件."""
    return event_bus.emit(
        EVENT_SOURCE_CONSOLE,
        "scene",
        {"scene": scene_name, "context": context or {}},
    )
