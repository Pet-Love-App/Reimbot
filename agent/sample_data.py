from __future__ import annotations

from typing import Any, Dict, Tuple


def get_sample_payloads() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    budget_json = {
        "project": "科研项目A",
        "items": [
            {"category": "差旅费", "budget_amount": 3000, "aliases": ["交通", "出行"]},
            {"category": "餐饮费", "budget_amount": 2000, "aliases": ["餐费"]},
            {"category": "会议费", "budget_amount": 1500, "aliases": ["会务"]},
            {"category": "材料费", "budget_amount": 1200, "aliases": ["文具", "打印"]},
        ],
    }

    actual_json = {
        "project": "科研项目A",
        "items": [
            {
                "expense_type": "打车费",
                "claimed_category": "交通费",
                "amount": 2500,
                "attachments": ["发票", "行程单"],
                "description": "外出调研往返",
            },
            {
                "expense_type": "餐饮",
                "claimed_category": "餐费",
                "amount": 2600,
                "attachments": ["发票"],
                "description": "课题组研讨会餐费",
            },
            {
                "expense_type": "会议",
                "claimed_category": "会务",
                "amount": 900,
                "attachments": ["发票", "签到表"],
                "description": "学术交流会场地",
            },
            {
                "expense_type": "打印",
                "claimed_category": "材料费",
                "amount": 400,
                "attachments": ["发票", "明细"],
                "description": "实验资料打印",
            },
            {
                "expense_type": "礼品",
                "claimed_category": "其他",
                "amount": 300,
                "attachments": ["发票"],
                "description": "交流纪念品",
            },
        ],
    }

    return budget_json, actual_json
