from __future__ import annotations

from typing import Any, Dict, List, TypedDict

import pandas as pd


class AgentState(TypedDict, total=False):
    """LangGraph 状态对象定义。"""

    budget_source: Any
    actual_source: Any

    budget_data: List[Dict[str, Any]]
    actual_data: List[Dict[str, Any]]

    budget_df: pd.DataFrame
    actual_df: pd.DataFrame

    discrepancies: List[Dict[str, Any]]
    suggestions: List[str]
    extraction_warnings: List[str]

    report: Dict[str, Any]
