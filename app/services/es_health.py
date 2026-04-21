"""Elasticsearch 健康检查."""

from elasticsearch import AsyncElasticsearch
from typing import Optional
from app.core.config import settings


class ESHealthCheck:
    """Elasticsearch 健康检查."""

    def __init__(self, es_url: Optional[str] = None):
        """
        初始化健康检查.

        Args:
            es_url: Elasticsearch URL
        """
        self.es_url = es_url or settings.ELASTICSEARCH_URL
        self.client = AsyncElasticsearch(hosts=[self.es_url])

    async def ping(self) -> bool:
        """
        检查 ES 是否可达.

        Returns:
            True 如果可达
        """
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def cluster_health(self) -> dict:
        """
        获取集群健康状态.

        Returns:
            集群健康信息 {"status": "green|yellow|red", ...}
        """
        try:
            response = await self.client.cluster.health()
            return {
                "status": response.get("status", "unknown"),
                "active_shards": response.get("active_shards", 0),
                "relocating_shards": response.get("relocating_shards", 0),
                "initializing_shards": response.get("initializing_shards", 0),
                "unassigned_shards": response.get("unassigned_shards", 0),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def is_healthy(self) -> bool:
        """
        检查集群是否健康.

        Returns:
            True 如果集群状态为 green 或 yellow
        """
        health = await self.cluster_health()
        return health.get("status") in ["green", "yellow"]

    async def close(self):
        """关闭客户端."""
        await self.client.close()


# 全局实例
_es_health: Optional[ESHealthCheck] = None


def get_es_health_check() -> ESHealthCheck:
    """获取健康检查实例."""
    global _es_health
    if _es_health is None:
        _es_health = ESHealthCheck()
    return _es_health
