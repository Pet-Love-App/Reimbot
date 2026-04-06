from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

@dataclass
class RetrievedChunk:
    source: str
    title: str
    content: str
    score: float


@dataclass
class _EmbeddingCacheEntry:
    signature: str
    texts: List[str]
    metadata: List[Dict[str, str]]
    emb_matrix: Any


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


# ---------------------------
# SentenceTransformer model
# ---------------------------
_model = None
_embedding_cache: Dict[str, _EmbeddingCacheEntry] = {}
_EMBED_MODEL_NAME = "jinaai/jina-embeddings-v5-text-nano-retrieval"


def _get_model():
    global _model
    if _model is not None:
        return _model

    try:
        import torch
        from sentence_transformers import SentenceTransformer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(
            _EMBED_MODEL_NAME,
            trust_remote_code=True,
            device=device,
        )
        return _model
    except Exception:
        _model = None
        return None


def _embed_texts(texts: List[str]):
    model = _get_model()
    if model is None:
        raise RuntimeError("Embedding model is not available")

    # delay import numpy to runtime
    import numpy as np

    emb = model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
    # ensure 2D
    return emb


def _to_hybrid_score(vector_score: float, keyword_score: float) -> float:
    keyword_component = min(max(keyword_score, 0.0), 8.0) / 8.0
    vector_component = max(vector_score, -1.0)
    return vector_component * 0.75 + keyword_component * 0.25


def _candidate_key(source: str, title: str, content: str) -> Tuple[str, str, str]:
    return (source.strip(), title.strip(), content.strip())


def _collect_keyword_candidates(
    query: str,
    query_tokens: Sequence[str],
    chunks: Sequence[Dict[str, str]],
    *,
    limit: int,
) -> List[Tuple[Dict[str, str], float]]:
    scored: List[Tuple[Dict[str, str], float]] = []
    for item in chunks:
        if not isinstance(item, dict):
            continue
        score = _score_chunk(query, query_tokens, item)
        if score <= 0:
            continue
        scored.append((item, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[: max(1, limit)]


def _detect_antonym_conflict(query: str, content: str) -> bool:
    """
    第三层：基于规则的简单语义与反义词冲突检测器
    例如：query中包含"不能超过"，但content中是"不能少于"之类
    """
    negations = ["不", "不能", "不可", "严禁", "禁止", "不得"]
    # 简单启发式：如果query和content在强否定词或方向性词汇上完全相反，可视为冲突
    # 这里只是一个占位或基础实现
    if "不能超过" in query and "不能少于" in content:
        return True
    if "可以" in query and "严禁" in content and "不可以" not in query:
        # 具体逻辑需要根据实际业务调整
        pass
    return False


def _rrf_fusion(
    keyword_ranked: List[RetrievedChunk],
    vector_ranked: List[RetrievedChunk],
    k: int = 60
) -> List[RetrievedChunk]:
    """
    第二层：RRF (Reciprocal Rank Fusion) 融合多路召回结果
    """
    rrf_scores: Dict[Tuple[str, str, str], float] = {}
    chunk_map: Dict[Tuple[str, str, str], RetrievedChunk] = {}

    for rank, chunk in enumerate(keyword_ranked):
        key = _candidate_key(chunk.source, chunk.title, chunk.content)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        chunk_map[key] = chunk

    for rank, chunk in enumerate(vector_ranked):
        key = _candidate_key(chunk.source, chunk.title, chunk.content)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        if key not in chunk_map:
            chunk_map[key] = chunk
            chunk_map[key].score = chunk.score # 保留原本的一些基础分

    # 将RRF分数赋给chunk的score字段用于最终排序
    fused = []
    for key, score in rrf_scores.items():
        chunk = chunk_map[key]
        chunk.score = score
        fused.append(chunk)
        
    fused.sort(key=lambda x: x.score, reverse=True)
    return fused


def _build_kb_signature(kb_path: Path, chunks: Sequence[Dict[str, object]]) -> str:
    try:
        st = kb_path.stat()
        return f"{kb_path.resolve()}::{st.st_mtime_ns}:{st.st_size}:{len(chunks)}"
    except OSError:
        return f"{kb_path.resolve()}::na:{len(chunks)}"


def _get_cached_embedding_index(
    kb_path: Path,
    chunks: Sequence[Dict[str, object]],
) -> Tuple[List[str], List[Dict[str, str]], Any]:
    cache_key = str(kb_path.resolve())
    signature = _build_kb_signature(kb_path, chunks)
    cached = _embedding_cache.get(cache_key)
    if cached and cached.signature == signature:
        return cached.texts, cached.metadata, cached.emb_matrix

    texts: List[str] = []
    metadata: List[Dict[str, str]] = []
    for item in chunks:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip()
        source = str(item.get("source", kb_path))
        full = (title + "\n" + content).strip()
        if not full:
            continue
        texts.append(full)
        metadata.append({"title": title or "未命名片段", "content": content, "source": source})

    emb_matrix = _embed_texts(texts)
    _embedding_cache[cache_key] = _EmbeddingCacheEntry(
        signature=signature,
        texts=texts,
        metadata=metadata,
        emb_matrix=emb_matrix,
    )
    return texts, metadata, emb_matrix


def retrieve_chunks(query: str, *, kb_path: str | Path, top_k: int = 4) -> List[RetrievedChunk]:
    """原有的基于词频/规则的检索，作为回退方案。"""
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


# ---------------------------
# 对外接口：语义召回
# ---------------------------
def search_policy(query: str, top_k: int = 3, kb_path: Optional[str | Path] = None) -> List[RetrievedChunk]:
    """
    使用分层多维度的向量与词频混合检索来返回与 query 最相关的片段。
    """
    if not query or not query.strip():
        return []

    if kb_path is None:
        kb_path = Path(__file__).resolve().parents[2] / "data" / "kb" / "reimbursement_kb.json"

    kb_payload = _load_kb(kb_path)
    chunks = kb_payload.get("chunks", [])
    if not isinstance(chunks, list) or len(chunks) == 0:
        return []

    query_tokens = _tokenize(query)
    candidate_limit = max(top_k * 8, 20)
    
    # 步骤1：先计算文件级别的分数，找到最匹配的文件（第一层前置过滤）
    file_scores: Dict[str, float] = {}
    for item in chunks:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", "未知来源"))
        content = str(item.get("content", ""))
        title = str(item.get("title", ""))
        text_to_score = f"{title}\n{content}"
        
        score = _score_chunk(query, query_tokens, {"content": text_to_score})
        if score > 0:
            if source not in file_scores or score > file_scores[source]:
                file_scores[source] = score
    
    top_files = set()
    if file_scores:
        sorted_files = sorted(file_scores.keys(), key=lambda k: file_scores[k], reverse=True)
        top_files = set(sorted_files[:3])
    
    filtered_chunks = []
    if top_files:
        for item in chunks:
            if not isinstance(item, dict):
                continue
            if item.get("source") in top_files:
                filtered_chunks.append(item)
    else:
        filtered_chunks = chunks

    # 第一层：多路检索 - 关键词/稀疏检索路
    keyword_candidates = _collect_keyword_candidates(
        query,
        query_tokens,
        filtered_chunks,  # type: ignore[arg-type]
        limit=candidate_limit,
    )
    
    keyword_ranked = []
    for item, keyword_score in keyword_candidates:
        source = str(item.get("source", "未知来源"))
        title = str(item.get("title", "未命名片段"))
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        # 第三层：反义词和语义冲突硬过滤
        if _detect_antonym_conflict(query, content):
            continue
        keyword_ranked.append(RetrievedChunk(source=source, title=title, content=content, score=keyword_score))

    resolved_path = Path(kb_path).resolve()
    db_path = resolved_path.parent / "chroma_db"
    
    vector_ranked = []
    # 第一层：多路检索 - 稠密向量检索路
    if db_path.exists():
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            class JinaEmbeddingFunction(embedding_functions.EmbeddingFunction):
                def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
                    model = _get_model()
                    if model is None:
                        raise RuntimeError("Embedding model is not available")
                    embeddings = model.encode(input, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
                    return embeddings.tolist()

            client = chromadb.PersistentClient(path=str(db_path))
            emb_fn = JinaEmbeddingFunction()
            collection = client.get_collection(name="reimbursement_kb", embedding_function=emb_fn)

            results = collection.query(query_texts=[query], n_results=candidate_limit)
            if results["documents"] and results["distances"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
                distances = results["distances"][0]

                for doc, meta, distance in zip(docs, metas, distances):
                    source = str(meta.get("source", "未知来源"))
                    if top_files and source not in top_files:
                        continue
                    
                    title = str(meta.get("title", "未命名片段"))
                    content = str(meta.get("content", doc)).strip()
                    if not content or _detect_antonym_conflict(query, content):
                        continue
                        
                    vector_score = 1.0 / (1.0 + float(distance))
                    vector_ranked.append(RetrievedChunk(source=source, title=title, content=content, score=vector_score))

        except Exception:
            pass

    # 如果 ChromaDB 失败或不存在，回退到动态嵌入
    if not vector_ranked:
        try:
            import numpy as np

            _, metadata, emb_matrix = _get_cached_embedding_index(resolved_path, chunks)
            query_emb = _embed_texts([query])[0]

            emb_norms = np.linalg.norm(emb_matrix, axis=1)
            q_norm = np.linalg.norm(query_emb) + 1e-10
            sims = (emb_matrix @ query_emb) / (emb_norms * q_norm + 1e-12)
            order = sorted(range(len(sims)), key=lambda i: float(sims[i]), reverse=True)

            for idx in order[: min(len(order), candidate_limit)]:
                meta = metadata[idx]
                source = str(meta.get("source", "未知来源"))
                if top_files and source not in top_files:
                    continue

                title = str(meta.get("title", "未命名片段"))
                content = str(meta.get("content", "")).strip()
                if not content or _detect_antonym_conflict(query, content):
                    continue
                
                vector_score = float(sims[idx])
                vector_ranked.append(RetrievedChunk(source=source, title=title, content=content, score=vector_score))
        except Exception:
            pass

    # 第一层的可选补充：稀疏向量检索（省略真实第三方库调用的模拟）
    sparse_ranked = []
    # ... 在实际生产中这路可由 BM25 配合 Sparse Embedding 提供 ...

    # 第二层：RRF 加权融合 (整合 keyword, vector 以及稀疏等的多路排序)
    # 此处假设 sparse_ranked 被合并到一起
    fused_results = _rrf_fusion(keyword_ranked, vector_ranked)
    
    # 截取最终需要返回的 top_k 数量
    final_top_chunks = fused_results[: max(1, top_k)]

    if final_top_chunks:
        return final_top_chunks
        
    # 如果完全失败，回退到最基础的词汇检索
    return retrieve_chunks(query, kb_path=kb_path, top_k=top_k)
