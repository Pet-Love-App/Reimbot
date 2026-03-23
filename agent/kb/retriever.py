from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


@dataclass
class RetrievedChunk:
    source: str
    title: str
    content: str
    score: float


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _tokenize(text: str) -> List[str]:
    normalized = _normalize(text)
    if not normalized:
        return []

    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", normalized)
    enriched: List[str] = []

    for token in tokens:
        if re.fullmatch(r"[\u4e00-\u9fff]", token):
            enriched.append(token)
        else:
            enriched.append(token)

    chinese_sequence = "".join(ch for ch in normalized if "\u4e00" <= ch <= "\u9fff")
    if len(chinese_sequence) >= 2:
        for idx in range(len(chinese_sequence) - 1):
            enriched.append(chinese_sequence[idx : idx + 2])

    return enriched


def _score_chunk(query: str, query_tokens: Sequence[str], chunk: Dict[str, str]) -> float:
    content = str(chunk.get("content", ""))
    haystack = _normalize(content)
    if not haystack:
        return 0.0

    overlap = 0
    for token in query_tokens:
        if token and token in haystack:
            overlap += 1

    phrase_bonus = 0.0
    query_norm = _normalize(query)
    if query_norm and query_norm in haystack:
        phrase_bonus = 2.0

    length_penalty = min(len(haystack) / 2000.0, 1.0)
    return overlap + phrase_bonus - length_penalty * 0.3


def _load_kb(kb_path: str | Path) -> Dict[str, object]:
    path = Path(kb_path)
    if not path.exists():
        raise FileNotFoundError(f"知识库文件不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def retrieve_chunks(query: str, *, kb_path: str | Path, top_k: int = 4) -> List[RetrievedChunk]:
    if not query.strip():
        return []

    kb_payload = _load_kb(kb_path)
    chunks = kb_payload.get("chunks", [])
    if not isinstance(chunks, list):
        return []

    query_tokens = _tokenize(query)
    scored: List[RetrievedChunk] = []

    for item in chunks:
        if not isinstance(item, dict):
            continue
        score = _score_chunk(query, query_tokens, item)
        if score <= 0:
            continue
        scored.append(
            RetrievedChunk(
                source=str(item.get("source", "未知来源")),
                title=str(item.get("title", "未命名片段")),
                content=str(item.get("content", "")).strip(),
                score=score,
            )
        )

    scored.sort(key=lambda chunk: chunk.score, reverse=True)
    return scored[: max(top_k, 1)]


def format_retrieved_context(chunks: Sequence[RetrievedChunk], *, max_chars: int = 1800) -> str:
    if not chunks:
        return ""

    lines: List[str] = []
    total = 0
    for idx, chunk in enumerate(chunks, start=1):
        snippet = chunk.content.strip()
        if not snippet:
            continue
        block = f"[{idx}] 来源: {chunk.source} | 标题: {chunk.title}\n{snippet}"
        if total + len(block) > max_chars:
            break
        lines.append(block)
        total += len(block)

    return "\n\n".join(lines)
