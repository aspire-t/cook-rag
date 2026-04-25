"""混合检索服务 - 整合 ES BM25 和 Qdrant 向量检索."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.es_search import ESSearchService, get_es_service
from app.services.qdrant_service import QdrantService, get_qdrant_service
from app.services.rrf_fusion import rrf, RRFFusion
from app.services.rerank_service import rerank_candidates, get_rerank_service


@dataclass
class SearchResult:
    """搜索结果."""
    recipe_id: str
    score: float
    source: str  # "es", "qdrant", "fused"
    payload: Dict[str, Any]


class HybridSearch:
    """混合检索服务."""

    def __init__(
        self,
        es_service: Optional[ESSearchService] = None,
        qdrant_service: Optional[QdrantService] = None,
        rrf_k: int = 60,
        top_n: int = 10,
        rerank_top_k: int = 20,
        use_rerank: bool = True,
    ):
        """
        初始化混合检索服务.

        Args:
            es_service: ES 服务
            qdrant_service: Qdrant 服务
            rrf_k: RRF k 参数
            top_n: 返回数量
            rerank_top_k: 送入 Rerank 的候选数量
            use_rerank: 是否启用 Rerank 重排序
        """
        self.es_service = es_service or get_es_service()
        self.qdrant_service = qdrant_service or get_qdrant_service()
        self.rrf_fusion = RRFFusion(k=rrf_k, top_n=rerank_top_k)
        self.top_n = top_n
        self.rerank_top_k = rerank_top_k
        self.use_rerank = use_rerank

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True,
        use_rerank: bool = True,
        user_prefs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索菜谱.

        Args:
            query: 搜索关键词
            filters: 过滤条件
            use_hybrid: 是否使用混合检索（否则只用 ES）
            use_rerank: 是否使用 Rerank 重排序
            user_prefs: 用户偏好（用于 Rerank）

        Returns:
            搜索结果列表
        """
        if use_hybrid:
            results = await self._hybrid_search(query, filters)

            if use_rerank and self.use_rerank and results:
                results = await self._rerank_results(query, results, user_prefs)

            return results[:self.top_n]
        else:
            return await self._es_only_search(query, filters)

    async def _hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """混合检索（ES + Qdrant + RRF 融合）."""
        # 1. ES BM25 搜索
        es_results = await self._search_es(query, filters)

        # 2. Qdrant 向量搜索
        qdrant_results = await self._search_qdrant(query, filters)

        # 3. RRF 融合
        fused_results = self.rrf_fusion.fuse(es_results, qdrant_results)

        return fused_results

    async def _rerank_results(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        user_prefs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """重排序结果."""
        return await rerank_candidates(query, candidates, user_prefs, top_k=self.rerank_top_k)

    async def _es_only_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """仅 ES 搜索."""
        return await self._search_es(query, filters)

    async def _search_es(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """执行 ES 搜索."""
        es_results = await self.es_service.search(query, filters, size=self.top_n)
        # 将 ES 结果转换为统一格式（包含 payload 字段）
        # 注意：ES 返回的结果中 id 字段可能不存在，需要从 payload 中获取
        results = []
        for r in es_results:
            recipe_id = r.get("id") or r.get("recipe_id") or ""
            results.append({"recipe_id": recipe_id, "score": 0.0, "payload": r})
        return results

    async def _search_qdrant(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """执行 Qdrant 搜索."""
        # 实际使用中需要通过 Embedding 服务生成查询向量
        # 这里为了简化直接返回空列表
        # 生产环境应该集成 EmbeddingService
        return []


# 全局服务实例
_hybrid_search: Optional[HybridSearch] = None


def get_hybrid_search_service() -> HybridSearch:
    """获取混合检索服务实例."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search


async def hybrid_search(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    混合检索入口函数.

    Args:
        query: 搜索关键词
        filters: 过滤条件
        top_n: 返回数量

    Returns:
        搜索结果列表
    """
    service = get_hybrid_search_service()
    return service.search(query, filters, use_hybrid=True)


async def keyword_search(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    纯关键词搜索（仅 ES）.

    Args:
        query: 搜索关键词
        filters: 过滤条件
        top_n: 返回数量

    Returns:
        搜索结果列表
    """
    service = get_hybrid_search_service()
    return service.search(query, filters, use_hybrid=False)
