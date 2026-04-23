"""Qdrant 向量检索服务."""

from typing import List, Dict, Any, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
)

from app.core.config import settings
from app.services.qdrant_schema import get_collection_config, VECTOR_SIZE


class QdrantService:
    """Qdrant 向量检索服务 - 使用 COSINE 相似度计算."""

    def __init__(self, qdrant_url: Optional[str] = None):
        """
        初始化 Qdrant 服务.

        Args:
            qdrant_url: Qdrant URL
        """
        self.qdrant_url = qdrant_url or settings.QDRANT_URL
        self.collection_name = settings.QDRANT_COLLECTION
        self.client = QdrantClient(url=self.qdrant_url)
        self._collection_created = False

    def create_collection(self) -> bool:
        """
        创建 Collection.

        Returns:
            True 如果创建成功
        """
        try:
            # 检查 Collection 是否存在
            if self.client.collection_exists(collection_name=self.collection_name):
                self._collection_created = True
                return True

            # 获取配置
            config = get_collection_config()

            # 创建 Collection
            self.client.create_collection(
                collection_name=self.collection_name,
                **config,
            )

            # 创建 Payload 索引
            self._create_payload_indexes()

            self._collection_created = True
            return True
        except Exception as e:
            print(f"创建 Qdrant Collection 失败：{e}")
            return False

    def _create_payload_indexes(self):
        """创建 Payload 索引."""
        # 菜系索引
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="cuisine",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        # 难度索引
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="difficulty",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        # 用户 ID 索引
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="user_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        # 准备时间索引
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="prep_time",
            field_schema=PayloadSchemaType.INTEGER,
        )
        # 烹饪时间索引
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="cook_time",
            field_schema=PayloadSchemaType.INTEGER,
        )

    def collection_exists(self) -> bool:
        """
        检查 Collection 是否存在.

        Returns:
            True 如果存在
        """
        return self.client.collection_exists(collection_name=self.collection_name)

    def upsert(self, points: List[PointStruct]) -> bool:
        """
        插入或更新向量.

        Args:
            points: 向量点列表

        Returns:
            True 如果成功
        """
        try:
            result = self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            return result.status == "completed"
        except Exception as e:
            print(f"Upsert 失败：{e}")
            return False

    def search(
        self,
        query_vector: Dict[str, List[float]],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量搜索.

        Args:
            query_vector: 查询向量字典 {"name_vec": [...], "desc_vec": [...], ...}
            limit: 返回数量
            filters: 过滤条件

        Returns:
            搜索结果列表
        """
        # 构建过滤条件
        query_filter = None
        if filters:
            conditions = []
            if filters.get("cuisine"):
                conditions.append(
                    FieldCondition(key="cuisine", match=MatchValue(value=filters["cuisine"]))
                )
            if filters.get("difficulty"):
                conditions.append(
                    FieldCondition(key="difficulty", match=MatchValue(value=filters["difficulty"]))
                )
            if filters.get("max_prep_time"):
                conditions.append(
                    FieldCondition(key="prep_time", range=Range(lte=filters["max_prep_time"]))
                )
            if filters.get("user_id"):
                conditions.append(
                    FieldCondition(key="user_id", match=MatchValue(value=filters["user_id"]))
                )
            if conditions:
                query_filter = Filter(must=conditions)

        # 四路向量召回 - 使用 name_vec 作为主向量
        # 实际生产中应该做多路召回然后融合
        vector_name = "name_vec"
        query = query_vector.get(vector_name, [])

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=(vector_name, query),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    def search_image_vector(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索相似图片向量.

        Args:
            query_vector: 512 维 CLIP 向量 (numpy array)
            limit: 返回数量
            filters: 过滤条件

        Returns:
            匹配的菜谱列表
        """
        # 构建过滤条件
        query_filter = None
        if filters:
            conditions = []
            if filters.get("cuisine"):
                conditions.append(
                    FieldCondition(key="cuisine", match=MatchValue(value=filters["cuisine"]))
                )
            if filters.get("difficulty"):
                conditions.append(
                    FieldCondition(key="difficulty", match=MatchValue(value=filters["difficulty"]))
                )
            if filters.get("max_prep_time"):
                conditions.append(
                    FieldCondition(key="prep_time", range=Range(lte=filters["max_prep_time"]))
                )
            if filters.get("user_id"):
                conditions.append(
                    FieldCondition(key="user_id", match=MatchValue(value=filters["user_id"]))
                )
            if conditions:
                query_filter = Filter(must=conditions)

        # 转换 numpy 为 list
        vector_list = query_vector.flatten().tolist() if hasattr(query_vector, 'flatten') else list(query_vector)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=("image_vec", vector_list),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    def delete(self, recipe_id: str) -> bool:
        """
        删除菜谱向量.

        Args:
            recipe_id: 菜谱 ID

        Returns:
            True 如果删除成功
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[recipe_id],
            )
            return True
        except Exception as e:
            print(f"删除向量失败：{e}")
            return False

    def close(self):
        """关闭客户端."""
        self.client.close()


# 全局服务实例
_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """获取 Qdrant 服务实例."""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service
