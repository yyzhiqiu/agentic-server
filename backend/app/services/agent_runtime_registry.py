"""Agent 运行时任务注册表。

该模块负责在单个应用进程内跟踪正在执行的 Agent 运行任务，并提供可恢复中断、
取消、等待结束与关闭期清理等控制能力。它只管理进程内 asyncio 任务，不承担
数据库持久化、HTTP 适配或跨进程调度职责。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal


ControlAction = Literal["interrupt", "cancel"]


@dataclass(slots=True)
class RuntimeControlRequest:
    """描述一次针对运行中任务的控制请求。"""

    action: ControlAction
    reason: str | None = None


@dataclass(slots=True)
class ActiveAgentRun:
    """保存进程内活跃 Agent 运行的任务句柄与控制状态。"""

    task: asyncio.Task[Any]
    control: RuntimeControlRequest | None = None


class AgentRuntimeRegistry:
    """维护 run_id 到 asyncio 任务的进程内映射。

    该注册表的边界刻意保持收敛：
    1. 它只关心“某个 run_id 当前是否有活跃任务”。
    2. 它只负责把中断/取消请求传递给任务，并记录原因。
    3. 它不直接写数据库，避免与 Service 层的事务职责混杂。
    """

    def __init__(self) -> None:
        self._runs: dict[str, ActiveAgentRun] = {}
        self._lock = asyncio.Lock()

    async def register(self, run_id: str, task: asyncio.Task[Any]) -> None:
        """登记一个新的活跃任务。

        如果同一 ``run_id`` 已有未结束任务，说明业务层出现了重复调度，
        这里显式抛错，避免两个任务同时写同一条运行记录。
        """

        async with self._lock:
            existing = self._runs.get(run_id)
            if existing is not None and existing.task is not task and not existing.task.done():
                raise RuntimeError(f"run {run_id} already has an active task")
            self._runs[run_id] = ActiveAgentRun(task=task)

    async def unregister(self, run_id: str, task: asyncio.Task[Any] | None = None) -> None:
        """移除一个已经结束或不再归当前任务持有的注册项。"""

        async with self._lock:
            existing = self._runs.get(run_id)
            if existing is None:
                return
            if task is not None and existing.task is not task:
                return
            self._runs.pop(run_id, None)

    async def has_active_task(self, run_id: str) -> bool:
        """判断指定运行是否仍绑定着未结束的进程内任务。"""

        async with self._lock:
            active_run = self._runs.get(run_id)
            if active_run is None:
                return False
            return not active_run.task.done()

    async def get_control_request(self, run_id: str) -> RuntimeControlRequest | None:
        """读取当前运行关联的控制请求快照。"""

        async with self._lock:
            active_run = self._runs.get(run_id)
            if active_run is None or active_run.control is None:
                return None
            return RuntimeControlRequest(
                action=active_run.control.action,
                reason=active_run.control.reason,
            )

    async def request_interrupt(self, run_id: str, reason: str | None = None) -> bool:
        """请求以“可恢复中断”的方式停止当前任务。"""

        return await self._request_control(run_id, action="interrupt", reason=reason)

    async def request_cancel(self, run_id: str, reason: str | None = None) -> bool:
        """请求以“彻底取消”的方式停止当前任务。"""

        return await self._request_control(run_id, action="cancel", reason=reason)

    async def _request_control(
        self,
        run_id: str,
        *,
        action: ControlAction,
        reason: str | None = None,
    ) -> bool:
        """记录控制请求并尝试取消对应任务。

        返回值表示当前进程内是否真的找到了活跃任务。若返回 ``False``，
        上层 Service 可以选择把它视为“任务已经不在本进程执行”并自行
        决定是否直接更新数据库状态。
        """

        async with self._lock:
            active_run = self._runs.get(run_id)
            if active_run is None:
                return False

            active_run.control = RuntimeControlRequest(action=action, reason=reason)
            if not active_run.task.done():
                active_run.task.cancel()
                return True
            return False

    async def wait_for_task(self, run_id: str, *, timeout: float = 5.0) -> bool:
        """等待指定运行的活跃任务退出。

        该等待主要用于控制接口在返回前尽量拿到更接近最终态的数据库结果。
        返回 ``True`` 表示任务已结束或原本就不存在，返回 ``False`` 表示超时。
        """

        async with self._lock:
            active_run = self._runs.get(run_id)
            if active_run is None:
                return True
            task = active_run.task

        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.CancelledError:
            return True
        except TimeoutError:
            return False
        return True

    async def shutdown(self, *, reason: str = "应用正在关闭") -> None:
        """在应用退出前取消全部活跃任务并等待其自行清理。"""

        async with self._lock:
            snapshot = list(self._runs.items())
            for _, active_run in snapshot:
                active_run.control = RuntimeControlRequest(action="cancel", reason=reason)
                if not active_run.task.done():
                    active_run.task.cancel()

        if not snapshot:
            return

        await asyncio.gather(
            *(active_run.task for _, active_run in snapshot),
            return_exceptions=True,
        )
