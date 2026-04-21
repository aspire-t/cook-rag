"""Qdrant 健康检查."""

from typing import Optional
from qdrant_client import QdrantClient
from app.core.config import settings


class QdrantHealthCheck:
    """Qdrant 健康检查."""

    def __init__(self, qdrant_url: Optional[str] = None):
        """
        初始化健康检查.

        Args:
            qdrant_url: Qdrant URL
        """
        self.qdrant_url = qdrant_url or settings.QDRANT_URL
        self.client = QdrantClient(url=self.qdrant_url)

    def ping(self) -> bool:
        """
        检查 Qdrant 是否可达.

        Returns:
            True 如果可达
        """
        try:
            return self.client.api_client.cluster.health() is not None
        except Exception:
            return False

    def cluster_info(self) -> dict:
        """
        获取集群信息.

        Returns:
            集群信息
        """
        try:
            info = self.client.get_collection(collection_name="recipes")
            return {
                "status": "connected",
                "collection_exists": info is not None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def is_healthy(self) -> bool:
        """
        检查是否健康.

        Returns:
            True 如果健康
        """
        try:
            # 检查是否能获取集群信息
            self.client.get_collections()
            return True
        except Exception:
            return False

    def close(self):
        """关闭客户端."""
        self.client.close()


# 全局实例
_qdrant_health: Optional[QdrantHealthCheck] = None


def get_qdrant_health_check() -> QdrantHealthCheck:
    """获取健康检查实例."""
    global _qdrant_health
    if _qdrant_health is None:
        _qdrant_health = QdrantHealthCheck()
    return _qdrant_health
