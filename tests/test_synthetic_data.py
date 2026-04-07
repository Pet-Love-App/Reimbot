from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.generate_sft_synthetic_data import generate_dataset


class TestSyntheticDataGeneration(unittest.TestCase):
    def test_generate_dataset_rule_based(self) -> None:
        template = {
            "task_name": "自动填表",
            "scenarios": ["场景A", "场景B"],
            "fields": [
                {"name": "报销人", "type": "string", "candidates": ["张三", "李四"]},
                {"name": "报销金额", "type": "amount"},
                {"name": "发生日期", "type": "date"},
            ],
        }
        rows, llm_success = generate_dataset(
            template,
            count=5,
            seed=7,
            use_llm=False,
            model="glm-4-flash",
            api_key="",
            base_url="https://example.com/v1",
            timeout=10,
        )
        self.assertEqual(len(rows), 5)
        self.assertEqual(llm_success, 0)
        self.assertTrue(all("instruction" in row and "output" in row for row in rows))
        output_obj = json.loads(rows[0]["output"])
        self.assertIn("报销人", output_obj)
        self.assertIn("报销金额", output_obj)

    def test_jsonl_can_be_written(self) -> None:
        template = {
            "task_name": "自动填表",
            "fields": [{"name": "字段A", "type": "string"}],
        }
        rows, _ = generate_dataset(
            template,
            count=3,
            seed=1,
            use_llm=False,
            model="glm-4-flash",
            api_key="",
            base_url="https://example.com/v1",
            timeout=10,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.jsonl"
            with output.open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
