from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from agent.config import get_graph_policy_defaults
from agent.core.event_bus import EventBus
from agent.graphs.state import AppState


def _merge_graph_policy(payload: Dict[str, Any]) -> Dict[str, Any]:
    defaults = get_graph_policy_defaults()
    user_policy = payload.get("graph_policy", {})
    if not isinstance(user_policy, dict):
        user_policy = {}
    merged_policy = {**defaults, **user_policy}
    return {**payload, "graph_policy": merged_policy}


class TaskDispatcher:
    def __init__(self, event_bus: EventBus, graph: Optional[Any] = None) -> None:
        self.event_bus = event_bus
        if graph is not None:
            self.graph = graph
        else:
            from agent.graphs.main_graph import build_main_graph

            self.graph = build_main_graph()

    def dispatch(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        self.event_bus.publish("task_start", {"task_type": task_type, "trace_id": trace_id})
        merged_payload = _merge_graph_policy(payload if isinstance(payload, dict) else {})
        merged_payload = {**merged_payload, "trace_id": trace_id}
        initial_state: AppState = {
            "task_type": task_type,
            "payload": merged_payload,
            "task_progress": [],
            "outputs": {},
            "errors": [],
            "result": {},
        }
        try:
            final_state = self._invoke_with_progress_stream(initial_state, trace_id)
            result = final_state.get("result", {})
            if isinstance(result, dict):
                result = {**result, "trace_id": trace_id}
            if final_state.get("errors"):
                result = {**result, "errors": final_state.get("errors", [])}
            self.event_bus.publish("task_done", {"task_type": task_type, "result": result, "trace_id": trace_id})
            return result
        except Exception as exc:
            self.event_bus.publish("task_error", {"task_type": task_type, "message": str(exc), "trace_id": trace_id})
            raise

    def _invoke_with_progress_stream(self, initial_state: AppState, trace_id: str) -> Dict[str, Any]:
        """Invoke graph and emit progress incrementally when streaming is available."""
        last_progress_count = 0
        final_state: Optional[Dict[str, Any]] = None

        if hasattr(self.graph, "stream"):
            try:
                for snapshot in self.graph.stream(initial_state, stream_mode="values"):
                    if not isinstance(snapshot, dict):
                        continue
                    final_state = snapshot
                    progress = snapshot.get("task_progress", [])
                    if not isinstance(progress, list):
                        continue
                    new_steps = progress[last_progress_count:]
                    for step in new_steps:
                        if isinstance(step, dict):
                            self.event_bus.publish("task_progress", {**step, "trace_id": trace_id})
                    last_progress_count = len(progress)
            except Exception:
                # Fall back to non-stream invoke for compatibility with older graph runtimes.
                final_state = None

        if final_state is None:
            final_state = self.graph.invoke(initial_state)
            progress = final_state.get("task_progress", [])
            if isinstance(progress, list):
                for step in progress:
                    if isinstance(step, dict):
                        self.event_bus.publish("task_progress", {**step, "trace_id": trace_id})

        return final_state
