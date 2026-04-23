"""Elasticsearch 服务 - BM25 检索."""

from typing import List, Dict, Any, Optional
from elasticsearch import AsyncElasticsearch

from app.core.config import settings


class ESSearchService:
    """Elasticsearch 搜索服务.

    使用 IK 分词器 (ik_max_word) 进行中文分词，支持 BM25 相关性评分。
    """

    def __init__(self, es_url: Optional[str] = None):
        """
        初始化 ES 服务.

        Args:
            es_url: Elasticsearch URL
        """
        self.es_url = es_url or settings.ELASTICSEARCH_URL
        self.index_name = settings.ES_INDEX_NAME
        self.client = AsyncElasticsearch(
            hosts=[self.es_url],
            retry_on_timeout=True,
            max_retries=3,
        )

    async def create_index(self) -> bool:
        """
        创建菜谱索引.

        Returns:
            True 如果创建成功
        """
        # 导入 schema
        from app.services.es_schema import RECIPE_INDEX_MAPPING

        try:
            # 检查索引是否存在
            exists = await self.client.indices.exists(index=self.index_name)
            if exists:
                return True

            # 创建索引
            await self.client.indices.create(
                index=self.index_name,
                body=RECIPE_INDEX_MAPPING,
            )
            return True
        except Exception as e:
            print(f"创建 ES 索引失败：{e}")
            return False

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索菜谱.

        Args:
            query: 搜索关键词
            filters: 过滤条件
            size: 返回数量

        Returns:
            搜索结果列表
        """
        # 构建查询 - 结合精确匹配和宽松匹配，返回更多相关结果
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        # 1. 精确短语匹配（最高优先级）
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "name^20",
                                    "description^10",
                                    "ingredients^5",
                                ],
                                "type": "phrase",
                                "slop": 3,
                            }
                        },
                        # 2. 宽松匹配（返回更多相关结果）
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "name^15",
                                    "description^8",
                                    "ingredients^4",
                                    "steps^2",
                                ],
                                "type": "best_fields",
                                "minimum_should_match": "30%",
                            }
                        },
                        # 3. 前缀匹配（匹配词开头）
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "name^10",
                                    "description^5",
                                    "ingredients^2",
                                ],
                                "type": "phrase_prefix",
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": size,
            "min_score": 0.01,  # 降低最低分数阈值，返回更多结果
        }

        # 添加过滤条件
        if filters:
            filter_clauses = []
            if filters.get("cuisine"):
                filter_clauses.append({"term": {"cuisine.keyword": filters["cuisine"]}})
            if filters.get("difficulty"):
                filter_clauses.append({"term": {"difficulty.keyword": filters["difficulty"]}})
            if filters.get("max_prep_time"):
                filter_clauses.append({"range": {"prep_time": {"lte": filters["max_prep_time"]}}})
            if filters.get("max_cook_time"):
                filter_clauses.append({"range": {"cook_time": {"lte": filters["max_cook_time"]}}})

            if filter_clauses:
                search_body["query"] = {
                    "bool": {
                        "must": search_body["query"],
                        "filter": filter_clauses,
                    }
                }

        response = await self.client.search(body=search_body)
        hits = response["hits"]["hits"]
        return [hit["_source"] for hit in hits]

    async def index_recipe(self, recipe_id: str, recipe_data: Dict[str, Any]) -> bool:
        """
        索引菜谱文档.

        Args:
            recipe_id: 菜谱 ID
            recipe_data: 菜谱数据

        Returns:
            True 如果索引成功
        """
        try:
            await self.client.index(
                index=self.index_name,
                id=recipe_id,
                body=recipe_data,
            )
            return True
        except Exception as e:
            print(f"索引菜谱失败：{e}")
            return False

    async def delete_recipe(self, recipe_id: str) -> bool:
        """
        删除菜谱文档.

        Args:
            recipe_id: 菜谱 ID

        Returns:
            True 如果删除成功
        """
        try:
            await self.client.delete(
                index=self.index_name,
                id=recipe_id,
                ignore=[400, 404],
            )
            return True
        except Exception as e:
            print(f"删除菜谱失败：{e}")
            return False

    async def close(self):
        """关闭客户端."""
        await self.client.close()


# 全局服务实例
_es_service: Optional[ESSearchService] = None


def get_es_service() -> ESSearchService:
    """获取 ES 服务实例."""
    global _es_service
    if _es_service is None:
        _es_service = ESSearchService()
    return _es_service
