from __future__ import annotations

import unittest
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _install_fake_pandas() -> None:
    fake_pd = ModuleType("pandas")
    fake_pd.DataFrame = lambda *args, **kwargs: []
    sys.modules["pandas"] = fake_pd


_install_fake_pandas()

from agent.graphs.subgraphs.qa import rule_retrieve_node


class TestQAClarification(unittest.TestCase):
    def test_rule_retrieve_node_appends_clarification_to_answer(self) -> None:
        with patch("agent.graphs.subgraphs.qa.rule_retrieve") as mock_rule_retrieve, patch(
            "agent.graphs.subgraphs.qa.answer_generate"
        ) as mock_answer_generate, patch("agent.graphs.subgraphs.qa.build_workflow_hint") as mock_workflow_hint:
            mock_rule_retrieve.return_value.data = {"items": []}
            mock_rule_retrieve.return_value.error = None
            mock_answer_generate.return_value.data = {
                "answer": "证据不足，暂不下结论。",
                "citations": [],
                "confidence": 0.2,
                "needs_clarification": True,
                "clarifying_question": "活动类型、票据类型、金额区间分别是什么？",
            }
            mock_answer_generate.return_value.error = None
            mock_workflow_hint.return_value = None

            out = rule_retrieve_node({"payload": {"normalized_query": "报销怎么做"}, "errors": [], "task_progress": []})
            answer = out.get("result", {}).get("answer", "")
            self.assertIn("证据不足", answer)
            self.assertIn("请补充", answer)
            self.assertTrue(out.get("result", {}).get("needs_clarification"))


if __name__ == "__main__":
    unittest.main()
