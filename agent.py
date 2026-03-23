"""财务报销 Agent 入口脚本。"""

from __future__ import annotations

import json

from agent.graph_builder import build_graph
from agent.sample_data import get_sample_payloads
from agent.state import AgentState

try:
    from jsonschema import ValidationError
except Exception:  # pragma: no cover
    ValidationError = ValueError


def main() -> None:
    budget_json, actual_json = get_sample_payloads()
    app = build_graph()

    initial_state: AgentState = {
        "budget_source": budget_json,
        "actual_source": actual_json,
        "discrepancies": [],
        "suggestions": [],
    }

    try:
        final_state = app.invoke(initial_state)
    except ValidationError as exc:
        print("输入数据未通过 JSON Schema 校验：")
        print(str(exc))
        return
    except Exception as exc:  # pragma: no cover
        print("Agent 运行失败：")
        print(str(exc))
        return

    print("=" * 80)
    print("JSON 报告")
    print("=" * 80)
    print(json.dumps(final_state["report"]["report_json"], ensure_ascii=False, indent=2))

    print("\n" + "=" * 80)
    print("Markdown 报告")
    print("=" * 80)
    print(final_state["report"]["report_markdown"])


if __name__ == "__main__":
    main()
