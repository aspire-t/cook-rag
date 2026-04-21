"""RRF (Reciprocal Rank Fusion) 结果融合算法."""

from typing import List, Dict, Any, Tuple
from collections import defaultdict


def rrf(
    es_results: List[Dict[str, Any]],
    qdrant_results: List[Dict[str, Any]],
    k: int = 60,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) 融合算法.

    将 ES BM25 搜索结果和 Qdrant 向量搜索结果融合。

    Args:
        es_results: ES 搜索结果列表 [{"recipe_id": str, "score": float, ...}]
        qdrant_results: Qdrant 搜索结果列表 [{"id": str, "score": float, "payload": dict}]
        k: 平滑参数，默认 60 (防止除以 0)
        top_n: 返回 Top N 结果

    Returns:
        融合后的结果列表
    """
    # 存储每个菜谱的 RRF 分数
    rrf_scores: Dict[str, float] = defaultdict(float)

    # 存储每个菜谱的完整信息
    recipe_info: Dict[str, Dict[str, Any]] = {}

    # 计算 ES 结果的 RRF 分数
    for rank, result in enumerate(es_results, start=1):
        recipe_id = result.get("recipe_id") or result.get("id")
        if not recipe_id:
            continue

        # RRF 分数 = 1 / (k + rank)
        rrf_scores[recipe_id] += 1.0 / (k + rank)

        # 保存信息
        if recipe_id not in recipe_info:
            recipe_info[recipe_id] = {
                "recipe_id": recipe_id,
                "es_rank": rank,
                "es_score": result.get("score", 0),
            }

    # 计算 Qdrant 结果的 RRF 分数
    for rank, result in enumerate(qdrant_results, start=1):
        recipe_id = result.get("id") or result.get("recipe_id")
        if not recipe_id:
            continue

        # RRF 分数 = 1 / (k + rank)
        rrf_scores[recipe_id] += 1.0 / (k + rank)

        # 保存信息
        if recipe_id not in recipe_info:
            recipe_info[recipe_id] = {
                "recipe_id": recipe_id,
                "qdrant_rank": rank,
                "qdrant_score": result.get("score", 0),
            }
        else:
            # 更新已有记录
            recipe_info[recipe_id]["qdrant_rank"] = rank
            recipe_info[recipe_id]["qdrant_score"] = result.get("score", 0)

    # 按 RRF 分数排序
    sorted_results = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    # 构建最终结果
    fused_results = []
    for recipe_id, rrf_score in sorted_results[:top_n]:
        info = recipe_info.get(recipe_id, {})
        fused_results.append({
            "recipe_id": recipe_id,
            "rrf_score": rrf_score,
            "es_rank": info.get("es_rank"),
            "es_score": info.get("es_score"),
            "qdrant_rank": info.get("qdrant_rank"),
            "qdrant_score": info.get("qdrant_score"),
        })

    return fused_results


def fuse_results(
    es_results: List[Dict[str, Any]],
    qdrant_results: List[Dict[str, Any]],
    k: int = 60,
    top_n: int = 10,
    dedup: bool = True,
) -> List[Dict[str, Any]]:
    """
    融合 ES 和 Qdrant 搜索结果.

    Args:
        es_results: ES 搜索结果
        qdrant_results: Qdrant 搜索结果
        k: RRF k 参数
        top_n: 返回数量
        dedup: 是否去重

    Returns:
        融合后的结果
    """
    if dedup:
        return rrf(es_results, qdrant_results, k=k, top_n=top_n)
    else:
        # 简单合并（不去重）
        return es_results + qdrant_results


class RRFFusion:
    """RRF 融合器类."""

    def __init__(self, k: int = 60, top_n: int = 10):
        """
        初始化 RRF 融合器.

        Args:
            k: RRF k 参数 (默认 60)
            top_n: 返回 Top N 结果
        """
        self.k = k
        self.top_n = top_n

    def fuse(
        self,
        es_results: List[Dict[str, Any]],
        qdrant_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        融合两路搜索结果.

        Args:
            es_results: ES 搜索结果
            qdrant_results: Qdrant 搜索结果

        Returns:
            融合后的结果
        """
        return rrf(es_results, qdrant_results, k=self.k, top_n=self.top_n)

    def deduplicate(
        self,
        results: List[Dict[str, Any]],
        key: str = "recipe_id",
    ) -> List[Dict[str, Any]]:
        """
        去重.

        Args:
            results: 结果列表
            key: 去重键

        Returns:
            去重后的结果
        """
        seen = set()
        unique = []
        for result in results:
            recipe_id = result.get(key)
            if recipe_id and recipe_id not in seen:
                seen.add(recipe_id)
                unique.append(result)
        return unique
