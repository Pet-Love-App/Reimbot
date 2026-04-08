from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    top_category = str(top.get("category", "")).strip()
    action_tip = _build_action_tip(top_category or domain_label)
    doc_type = str(top.get("doc_type", "")).strip()
    doc_type_tip = f"（文档类型：{doc_type}）" if doc_type else ""
    answer = (
        f"根据本地知识库（分类：{domain_label}），与你问题最相关的是《{top.get('title', '规则片段')}》{doc_type_tip}。"
        f"建议：{action_tip}"
    )
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
