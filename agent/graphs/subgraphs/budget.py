from __future__ import annotations

from pathlib import Path

from agent.graphs.policy import get_bool_policy
from agent.graphs.state import AppState
from agent.tools import budget_calculate, generate_budget, generate_report, load_final_data


def _resolve_output_dir(payload: dict, default_subdir: str) -> str | None:
    explicit = str(payload.get("output_dir", "")).strip()
    if explicit:
        return explicit
    workspace_dir = str(payload.get("workspace_dir", "") or payload.get("workspace_root", "")).strip()
    if not workspace_dir:
        return None
    return str(Path(workspace_dir))


def budget_start_node(state: AppState) -> AppState:
    return {"task_progress": state.get("task_progress", []) + [{"step": "budget_start", "tool_name": "start"}]}


def route_after_load_final_data(state: AppState) -> str:
    payload = state.get("payload", {})
    aggregate = state.get("aggregate", {})
    if state.get("errors") and not aggregate:
        return "BudgetFailNode"
    skip_calculate_when_empty = get_bool_policy(payload, "budget_skip_calculate_when_empty", True)
    if aggregate:
        return "BudgetCalculateNode"
    return "BudgetGenerateNode" if skip_calculate_when_empty else "BudgetCalculateNode"


def load_final_data_node(state: AppState) -> AppState:
    res = load_final_data(state.get("payload", {}))
    return {
        "aggregate": res.data.get("final_data", {}),
        "errors": state.get("errors", []) + ([res.error] if res.error else []),
        "task_progress": state.get("task_progress", []) + [{"step": "load_final_data", "tool_name": "load_final_data"}],
    }


def budget_calculate_node(state: AppState) -> AppState:
    strategy = state.get("payload", {}).get("strategy", {})
    res = budget_calculate(state.get("aggregate", {}), strategy)
    return {
        "budget": res.data.get("budget", {}),
        "errors": state.get("errors", []) + ([res.error] if res.error else []),
        "task_progress": state.get("task_progress", []) + [{"step": "budget_calculate", "tool_name": "budget_calculate"}],
    }


def budget_generate_node(state: AppState) -> AppState:
    budget = state.get("budget", {})
    aggregate = state.get("aggregate", {})
    payload = state.get("payload", {}) if isinstance(state.get("payload", {}), dict) else {}
    route_decision = state.get("route_decision", {}) if isinstance(state.get("route_decision", {}), dict) else {}
    inferred_task = str(route_decision.get("task_type", "")).strip().lower()
    if inferred_task == "budget_fill" and not aggregate:
        message = "未检测到可用于预算填表的数据，请补充决算汇总、预算明细或上传待填写模板后重试。"
        return {
            "result": {
                "type": "budget",
                "status": "needs_clarification",
                "message": message,
                "errors": state.get("errors", []),
            },
            "errors": state.get("errors", []),
            "task_progress": state.get("task_progress", [])
            + [{"step": "budget_generate_guard", "tool_name": "missing_budget_fill_data_guard"}],
        }

    budget_output_dir = _resolve_output_dir(payload, "budget_outputs")
    report_output_dir = _resolve_output_dir(payload, "report_outputs")
    budget_res = generate_budget(budget, budget_output_dir)
    report_res = generate_report(aggregate, budget, report_output_dir)
    errors = state.get("errors", []) + ([budget_res.error] if budget_res.error else []) + ([report_res.error] if report_res.error else [])
    return {
        "outputs": {
            **state.get("outputs", {}),
            "budget_path": budget_res.data.get("budget_path", ""),
            "report_path": report_res.data.get("report_path", ""),
        },
        "result": {
            "type": "budget",
            "budget": budget,
            "budget_path": budget_res.data.get("budget_path", ""),
            "report_path": report_res.data.get("report_path", ""),
            "errors": errors,
        },
        "errors": errors,
        "task_progress": state.get("task_progress", []) + [{"step": "budget_generate", "tool_name": "generate_budget/generate_report"}],
    }


def budget_fail_node(state: AppState) -> AppState:
    errors = state.get("errors", [])
    return {
        "result": {
            "type": "budget",
            "status": "failed",
            "errors": errors,
        },
        "errors": errors,
        "task_progress": state.get("task_progress", []) + [{"step": "budget_fail", "tool_name": "fail_fast_guard"}],
    }
