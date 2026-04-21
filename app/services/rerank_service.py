"""重排序服务 - 集成 Rerank 模型与个性化加权.

接收混合检索 (ES + Qdrant + RRF) 的候选结果，进行精细化重排序。
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.models.rerank_model import RerankModel, get_rerank_model
import asyncio


@dataclass
class RerankResult:
    """重排序结果."""
    recipe_id: str
    score: float
    rerank_score: float
    preference_score: float
    popularity_score: float
    final_score: float
    payload: Dict[str, Any]


class RerankService:
    """
    重排序服务.

    集成 BGE-Reranker 模型，支持：
    - 用户偏好加权
    - 菜谱热度加权
    - 最终分数融合
    """

    def __init__(
        self,
        rerank_model: Optional[RerankModel] = None,
        rerank_weight: float = 0.6,
        preference_weight: float = 0.25,
        popularity_weight: float = 0.15,
        rerank_top_k: int = 20,
    ):
        """
        初始化重排序服务.

        Args:
            rerank_model: Rerank 模型实例
            rerank_weight: Rerank 分数权重
            preference_weight: 用户偏好权重
            popularity_weight: 菜谱热度权重
            rerank_top_k: 送入 Rerank 的候选数量
        """
        self.rerank_model = rerank_model or get_rerank_model()
        self.rerank_weight = rerank_weight
        self.preference_weight = preference_weight
        self.popularity_weight = popularity_weight
        self.rerank_top_k = rerank_top_k

    async def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        user_prefs: Optional[Dict[str, Any]] = None,
    ) -> List[RerankResult]:
        """
        重排序候选菜谱.

        Args:
            query: 搜索查询
            candidates: 候选菜谱列表 (来自混合检索)
            user_prefs: 用户偏好

        Returns:
            重排序后的结果
        """
        if not candidates:
            return []

        # 1. 提取文档文本用于 Rerank
        documents = [self._extract_text(c) for c in candidates]

        # 2. Rerank 模型评分
        rerank_scores = await self._get_rerank_scores(query, documents)

        # 3. 计算用户偏好分数
        preference_scores = self._get_preference_scores(candidates, user_prefs)

        # 4. 计算菜谱热度分数
        popularity_scores = self._get_popularity_scores(candidates)

        # 5. 融合分数
        results = []
        for i, candidate in enumerate(candidates):
            rerank_score = rerank_scores.get(i, 0.0)
            pref_score = preference_scores.get(i, 0.0)
            pop_score = popularity_scores.get(i, 0.0)

            # 加权融合
            final_score = (
                self.rerank_weight * rerank_score +
                self.preference_weight * pref_score +
                self.popularity_weight * pop_score
            )

            results.append(RerankResult(
                recipe_id=candidate.get("recipe_id") or candidate.get("id"),
                score=final_score,
                rerank_score=rerank_score,
                preference_score=pref_score,
                popularity_score=pop_score,
                final_score=final_score,
                payload=candidate.get("payload", candidate),
            ))

        # 6. 按最终分数排序
        results.sort(key=lambda x: x.final_score, reverse=True)

        return results

    def _extract_text(self, candidate: Dict[str, Any]) -> str:
        """
        从候选中提取用于 Rerank 的文本.

        组合菜名、描述、主要食材。

        Args:
            candidate: 候选菜谱

        Returns:
            组合文本
        """
        payload = candidate.get("payload", candidate)
        parts = []

        if payload.get("name"):
            parts.append(f"菜名：{payload['name']}")
        if payload.get("description"):
            parts.append(f"描述：{payload['description']}")
        if payload.get("ingredients"):
            ingredients = payload.get("ingredients", [])
            if isinstance(ingredients, list):
                parts.append(f"食材：{', '.join(ingredients[:5])}")
        if payload.get("cuisine"):
            parts.append(f"菜系：{payload['cuisine']}")

        return " | ".join(parts) if parts else str(payload)

    async def _get_rerank_scores(
        self,
        query: str,
        documents: List[str],
    ) -> Dict[int, float]:
        """
        获取 Rerank 模型分数.

        Args:
            query: 查询
            documents: 文档列表

        Returns:
            {index: score}
        """
        try:
            scored_indices = await self.rerank_model.rerank_batch(
                query,
                documents,
                batch_size=16,
                top_k=None,  # 返回所有分数
            )
            return {idx: score for idx, score in scored_indices}
        except Exception as e:
            print(f"Rerank 评分失败：{e}")
            # 回退：返回均匀分数
            return {i: 0.5 for i in range(len(documents))}

    def _get_preference_scores(
        self,
        candidates: List[Dict[str, Any]],
        user_prefs: Optional[Dict[str, Any]] = None,
    ) -> Dict[int, float]:
        """
        获取用户偏好分数.

        考虑因素：
        - 菜系偏好
        - 口味偏好
        - 难度偏好
        - 时间偏好

        Args:
            candidates: 候选列表
            user_prefs: 用户偏好

        Returns:
            {index: score}
        """
        if not user_prefs:
            return {i: 0.5 for i in range(len(candidates))}

        scores = {}
        preferred_cuisines = set(user_prefs.get("preferred_cuisines", []))
        preferred_tastes = set(user_prefs.get("preferred_tastes", []))
        preferred_difficulty = user_prefs.get("preferred_difficulty")
        max_cook_time = user_prefs.get("max_cook_time")

        for i, candidate in enumerate(candidates):
            payload = candidate.get("payload", candidate)
            score = 0.5  # 基础分数

            # 菜系匹配
            cuisine = payload.get("cuisine", "")
            if cuisine in preferred_cuisines:
                score += 0.2

            # 口味匹配
            tags = payload.get("tags", [])
            if isinstance(tags, list):
                matching_tastes = set(tags) & preferred_tastes
                score += len(matching_tastes) * 0.1

            # 难度匹配
            if preferred_difficulty and payload.get("difficulty") == preferred_difficulty:
                score += 0.15

            # 时间匹配
            if max_cook_time:
                cook_time = payload.get("cook_time", 0)
                if cook_time and cook_time <= max_cook_time:
                    score += 0.1

            # 归一化到 [0, 1]
            scores[i] = min(1.0, score)

        return scores

    def _get_popularity_scores(
        self,
        candidates: List[Dict[str, Any]],
    ) -> Dict[int, float]:
        """
        获取菜谱热度分数.

        考虑因素：
        - 收藏次数
        - 浏览次数
        - 评分

        Args:
            candidates: 候选列表

        Returns:
            {index: score}
        """
        if not candidates:
            return {}

        # 提取热度指标
        popularity_data = []
        for candidate in candidates:
            payload = candidate.get("payload", candidate)
            favorites = payload.get("favorites_count", 0)
            views = payload.get("views_count", 0)
            rating = payload.get("rating", 0)
            popularity_data.append((favorites, views, rating))

        # 如果没有数据，返回均匀分数
        if not any(popularity_data):
            return {i: 0.5 for i in range(len(candidates))}

        # 归一化
        max_favorites = max(d[0] for d in popularity_data) or 1
        max_views = max(d[1] for d in popularity_data) or 1
        max_rating = max(d[2] for d in popularity_data) or 5

        scores = {}
        for i, (fav, views, rating) in enumerate(popularity_data):
            # 加权组合
            norm_fav = fav / max_favorites
            norm_views = views / max_views
            norm_rating = rating / max_rating

            # 热度分数：收藏 40% + 浏览 30% + 评分 30%
            score = 0.4 * norm_fav + 0.3 * norm_views + 0.3 * norm_rating
            scores[i] = score

        return scores


# 全局服务实例
_rerank_service: Optional[RerankService] = None


def get_rerank_service() -> RerankService:
    """获取重排序服务实例."""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service


async def rerank_candidates(
    query: str,
    candidates: List[Dict[str, Any]],
    user_prefs: Optional[Dict[str, Any]] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    重排序入口函数.

    Args:
        query: 搜索查询
        candidates: 候选列表
        user_prefs: 用户偏好
        top_k: 返回数量

    Returns:
        重排序后的结果
    """
    service = get_rerank_service()
    results = await service.rerank(query, candidates, user_prefs)

    # 转换为字典格式
    output = [
        {
            "recipe_id": r.recipe_id,
            "score": r.final_score,
            "rerank_score": r.rerank_score,
            "preference_score": r.preference_score,
            "popularity_score": r.popularity_score,
            "payload": r.payload,
        }
        for r in results
    ]

    if top_k:
        output = output[:top_k]

    return output
