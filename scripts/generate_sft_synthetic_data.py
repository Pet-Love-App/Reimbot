from __future__ import annotations

import argparse
import json
import os
import random
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_template(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("模板文件必须是 JSON 对象。")
    return payload


def _sample_date(rng: random.Random) -> str:
    start = datetime(2024, 1, 1)
    delta_days = rng.randint(0, 900)
    return (start + timedelta(days=delta_days)).strftime("%Y-%m-%d")


def _sample_amount(rng: random.Random) -> float:
    return round(rng.uniform(30.0, 5000.0), 2)


def _sample_value(field: Dict[str, Any], rng: random.Random) -> Any:
    name = str(field.get("name", "")).strip()
    field_type = str(field.get("type", "string")).strip().lower()
    candidates = field.get("candidates", [])
    if isinstance(candidates, list) and candidates:
        return rng.choice(candidates)
    if "金额" in name or field_type in {"amount", "number", "float", "int"}:
        return _sample_amount(rng)
    if "日期" in name or field_type in {"date", "datetime"}:
        return _sample_date(rng)
    if "是否" in name or field_type in {"bool", "boolean"}:
        return rng.choice([True, False])
    if field_type == "integer":
        return rng.randint(1, 20)
    return f"{name or '字段'}示例值{rng.randint(1, 999)}"


def _rule_generate_sample(template: Dict[str, Any], rng: random.Random, idx: int) -> Dict[str, Any]:
    task_name = str(template.get("task_name", "表单填充任务")).strip() or "表单填充任务"
    scenario_pool = template.get("scenarios", [])
    scenario = rng.choice(scenario_pool) if isinstance(scenario_pool, list) and scenario_pool else "常规报销"
    fields = template.get("fields", [])
    if not isinstance(fields, list):
        fields = []

    output_data: Dict[str, Any] = {}
    for field in fields:
        if isinstance(field, dict):
            key = str(field.get("name", "")).strip()
            if key:
                output_data[key] = _sample_value(field, rng)

    output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
    instruction = (
        f"你是行政助手。请根据给定场景完成“{task_name}”表单填充，"
        "仅输出 JSON，不要添加解释。"
    )
    user_input = (
        f"场景：{scenario}\n"
        f"要求：按模板字段完整填写，缺失项用 null。\n"
        f"字段：{', '.join(output_data.keys()) if output_data else '无'}"
    )
    return {
        "id": f"sft-{idx:06d}",
        "instruction": instruction,
        "input": user_input,
        "output": output_json,
        "meta": {
            "source": "rule_based",
            "task_name": task_name,
            "scenario": scenario,
        },
    }


def _llm_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return normalized + "/chat/completions"
    return normalized + "/v1/chat/completions"


def _extract_json(text: str) -> Dict[str, Any]:
    blocks = re.findall(r"\{[\s\S]*\}", text)
    for block in reversed(blocks):
        try:
            obj = json.loads(block)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    raise ValueError("模型返回中未找到有效 JSON。")


def _llm_generate_sample(
    template: Dict[str, Any],
    *,
    idx: int,
    model: str,
    api_key: str,
    base_url: str,
    timeout: int,
) -> Dict[str, Any]:
    prompt = (
        "你是数据合成助手，请生成一条用于指令微调的数据。"
        "返回 JSON 对象，包含 instruction、input、output 三个字段。"
        "其中 output 必须是 JSON 字符串。"
        f"\n模板定义：\n{json.dumps(template, ensure_ascii=False)}"
    )
    body = {
        "model": model,
        "temperature": 0.9,
        "messages": [
            {"role": "system", "content": "你擅长生成高质量中文行政任务合成数据。"},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        _llm_endpoint(base_url),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    choices = payload.get("choices", [])
    if not choices:
        raise RuntimeError("模型返回为空。")
    content = str(choices[0].get("message", {}).get("content", "")).strip()
    parsed = _extract_json(content)
    instruction = str(parsed.get("instruction", "")).strip()
    sample_input = str(parsed.get("input", "")).strip()
    sample_output = str(parsed.get("output", "")).strip()
    if not (instruction and sample_output):
        raise ValueError("模型返回缺少 instruction 或 output。")
    return {
        "id": f"sft-{idx:06d}",
        "instruction": instruction,
        "input": sample_input,
        "output": sample_output,
        "meta": {"source": "llm", "model": model},
    }


def generate_dataset(
    template: Dict[str, Any],
    *,
    count: int,
    seed: int,
    use_llm: bool,
    model: str,
    api_key: str,
    base_url: str,
    timeout: int,
) -> Tuple[List[Dict[str, Any]], int]:
    rng = random.Random(seed)
    records: List[Dict[str, Any]] = []
    llm_success = 0
    for idx in range(1, count + 1):
        if use_llm and api_key:
            try:
                sample = _llm_generate_sample(
                    template,
                    idx=idx,
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                )
                llm_success += 1
                records.append(sample)
                continue
            except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError):
                pass
        records.append(_rule_generate_sample(template, rng, idx))
    return records, llm_success


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="基于模板批量生成 SFT 合成数据（JSONL）")
    parser.add_argument("--template", required=True, help="模板 JSON 文件路径")
    parser.add_argument("--output", default="data/eval/sft_synthetic_data.jsonl", help="输出 JSONL 路径")
    parser.add_argument("--count", type=int, default=200, help="生成条数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--use-llm", action="store_true", help="优先使用 LLM 生成，失败自动回退规则生成")
    parser.add_argument("--model", default=os.getenv("AGENT_SYNTH_MODEL", "glm-4-flash"), help="模型名称")
    parser.add_argument(
        "--base-url",
        default=os.getenv("AGENT_SYNTH_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        help="OpenAI 兼容接口 base URL（可接智谱兼容网关）",
    )
    parser.add_argument("--timeout", type=int, default=60, help="接口超时时间（秒）")
    args = parser.parse_args()

    template_path = Path(args.template).resolve()
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    output_path = Path(args.output).resolve()

    template = _load_template(template_path)
    api_key = os.getenv("AGENT_SYNTH_API_KEY", "").strip() or os.getenv("ZHIPU_API_KEY", "").strip()
    records, llm_success = generate_dataset(
        template,
        count=max(1, int(args.count)),
        seed=int(args.seed),
        use_llm=bool(args.use_llm),
        model=str(args.model).strip(),
        api_key=api_key,
        base_url=str(args.base_url).strip(),
        timeout=max(10, int(args.timeout)),
    )
    _write_jsonl(output_path, records)
    print(
        json.dumps(
            {
                "ok": True,
                "template": str(template_path),
                "output": str(output_path),
                "count": len(records),
                "llm_success": llm_success,
                "rule_based_count": len(records) - llm_success,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
