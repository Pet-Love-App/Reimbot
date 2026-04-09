from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agent.tools.base import ToolResult, ok


def question_understand(question: str) -> ToolResult:
    normalized = question.strip()
    intent = "policy"
    if any(key in normalized for key in ["报销", "附件", "发票", "金额", "规则"]):
        intent = "policy"
    elif any(key in normalized for key in ["预算", "决算", "财务", "报表", "填表"]):
        intent = "finance"
    elif any(key in normalized for key in ["实验", "实验报告", "数据分析", "结论"]):
        intent = "lab_report"
    return ok(intent=intent, question=normalized)


def _build_clarifying_question(intent: str, question: str) -> str:
    if intent == "policy":
        return (
            "我目前缺少足够依据来精确回答。"
            "请补充活动类型、票据类型、金额区间和发生时间，我再按制度条款给出结论。"
        )
    if intent == "finance":
        return (
            "为了继续处理，请补充任务目标（报销校验/自动填表/预算或决算）、"
            "涉及模板文件名，以及关键字段（金额、项目号、时间范围）。"
        )
    if intent == "lab_report":
        return "请补充实验目的、数据来源、分析方法和希望输出的报告结构，我再生成可执行建议。"
    if question.strip():
        return "我需要更多上下文。请补充关键条件（场景、约束、时间范围），我再给出准确结论。"
    return "请先描述你的问题场景和目标，我会先反问补齐信息后再回答。"


def _infer_domain_label(item: Dict[str, Any]) -> str:
    category = str(item.get("category", "")).strip()
    subcategory = str(item.get("subcategory", "")).strip()
    if category and subcategory:
        return f"{category}/{subcategory}"
    if category:
        return category
    source = str(item.get("source", "")).replace("\\", "/")
    if "/" in source:
        return source.split("/", 1)[0].strip() or "综合政策"
    return "综合政策"


def _build_action_tip(domain_label: str) -> str:
    mapping = {
        "政策文件": "先核对制度条款，再准备票据与审批材料。",
        "学生活动": "优先准备预算/决算模板与活动说明，再补齐附件。",
        "国内+思政实践": "核验交通与住宿标准，补齐行程和差旅说明。",
        "海外实践": "先确认国际差旅标准与合同流程，再准备外汇/转账材料。",
        "清华大学 财务报销标准": "按学校统一标准先做额度与票据合规自查。",
        "工作餐报销 餐单（仅校内结算单报销需要填写，电子票据直接系统内添加餐单）": "先确认是否属于校内结算单，再补齐餐单与审批单。",
    }
    return mapping.get(domain_label, "先确认适用场景，再按模板和制度逐项补齐材料。")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _extract_query_tokens(question: str) -> List[str]:
    normalized = _normalize_text(question)
    if not normalized:
        return []
    raw_tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", normalized)
    return [token.lower() for token in raw_tokens if len(token.strip()) >= 2]


def _citation_label(item: Dict[str, Any]) -> str:
    source = str(item.get("source", "")).strip()
    if source:
        return Path(source.replace("\\", "/")).name or source
    title = str(item.get("title", "")).strip()
    return title or "知识库片段"


def _split_sentences(content: str) -> List[str]:
    text = _normalize_text(content)
    if not text:
        return []
    text = re.sub(r"\[Slide\s*\d+\]", " ", text, flags=re.IGNORECASE)
    parts = re.split(r"[。\n；;!?！？]+", text)
    return [_normalize_text(part) for part in parts if _normalize_text(part)]


def _extract_key_points(question: str, ranked: Sequence[Dict[str, Any]], max_points: int = 5) -> List[Tuple[str, str]]:
    query_tokens = _extract_query_tokens(question)
    generic_tokens = ["报销", "材料", "标准", "附件", "发票", "交通", "住宿", "保险", "租车", "实践"]
    selected: List[Tuple[float, str, str]] = []
    seen: set[str] = set()

    for item in ranked[:8]:
        source_name = _citation_label(item)
        sentences = _split_sentences(str(item.get("content", "")))
        for sentence in sentences:
            if len(sentence) < 10 or len(sentence) > 120:
                continue
            key = sentence.lower()
            if key in seen:
                continue
            token_hits = sum(1 for token in query_tokens if token and token in key)
            generic_hits = sum(1 for token in generic_tokens if token in key)
            if token_hits == 0 and generic_hits == 0:
                continue
            score = token_hits * 2 + generic_hits
            if re.search(r"报销|标准|需|需要|应|可|不得|凭票|附件", sentence):
                score += 1
            selected.append((float(score), sentence, source_name))
            seen.add(key)

    selected.sort(key=lambda row: row[0], reverse=True)
    return [(sentence, source_name) for _, sentence, source_name in selected[: max(1, max_points)]]


def build_workflow_hint(question: str) -> Optional[Dict[str, Any]]:
    text = question.strip()
    if not text:
        return None

    if any(key in text for key in ["报销", "自动填表", "填表", "审批", "财务"]):
        return {
            "name": "finance_workflow",
            "steps": [
                "信息采集（报销人、项目号、金额、票据）",
                "规则校验（额度、必填项、附件完整性）",
                "计算与格式化（汇总金额、模板字段映射）",
                "生成材料（表单、说明文档、邮件草稿）",
                "人工确认后提交",
            ],
            "tool_candidates": ["scan_inputs", "extract_text_from_files", "check_rules", "generate_excel_sheet"],
        }

    if any(key in text for key in ["实验报告", "实验", "报告辅助"]):
        return {
            "name": "lab_report_workflow",
            "steps": [
                "检索实验相关资料片段",
                "抽取实验背景与关键参数",
                "生成报告大纲与结论草稿",
                "按模板输出与人工复核",
            ],
            "tool_candidates": ["rag_retrieve", "generate_report"],
        }
    return None


def answer_generate(
    question: str,
    retrieved_items: List[Dict[str, Any]],
    *,
    min_score: float = 0.55,
    intent: str = "policy",
) -> ToolResult:
    if not retrieved_items:
        clarifying = _build_clarifying_question(intent, question)
        return ok(
            answer=f"未检索到直接依据：{question}。",
            citations=[],
            confidence=0.0,
            needs_clarification=True,
            clarifying_question=clarifying,
        )

    ranked = sorted(retrieved_items, key=lambda item: float(item.get("score", 0.0)), reverse=True)
    top = ranked[0]
    top_score = float(top.get("score", 0.0))
    if top_score < float(min_score):
        clarifying = _build_clarifying_question(intent, question)
        return ok(
            answer="已检索到相关内容，但证据置信度不足，暂不直接下结论。",
            citations=[],
            confidence=top_score,
            needs_clarification=True,
            clarifying_question=clarifying,
        )

    domain_label = _infer_domain_label(top)
    key_points = _extract_key_points(question, ranked, max_points=5)
    top_title = str(top.get("title", "规则片段")).strip() or "规则片段"
    top_source_name = _citation_label(top)
    if key_points:
        lines = [
            f"已结合检索到的制度内容直接回答。核心依据来自《{top_title}》。",
        ]
        for idx, (point, source_name) in enumerate(key_points, start=1):
            lines.append(f"{idx}. {point}（参考：{source_name}）")
        answer = "\n".join(lines)
    else:
        top_category = str(top.get("category", "")).strip()
        action_tip = _build_action_tip(top_category or domain_label)
        answer = f"{action_tip}（参考：{top_source_name}）"
    citations = [
        {
            "source": top.get("source", ""),
            "title": top.get("title", ""),
            "score": float(top.get("score", 0)),
            "category": top.get("category", ""),
            "doc_type": top.get("doc_type", ""),
        }
        for top in ranked[:3]
    ]
    return ok(
        answer=answer,
        citations=citations,
        confidence=top_score,
        needs_clarification=False,
        clarifying_question="",
    )
