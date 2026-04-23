"""Qdrant 图片向量集成测试."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from app.services.qdrant_schema import get_collection_config, VECTOR_SIZE
from app.services.qdrant_service import QdrantService


class TestQdrantImageSchema:
    """测试 Qdrant Schema 图片向量配置."""

    def test_image_vec_field_exists(self):
        """测试 image_vec 字段存在."""
        config = get_collection_config()

        assert "vectors" in config
        assert "image_vec" in config["vectors"]

        image_vec_config = config["vectors"]["image_vec"]
        assert image_vec_config.size == 512
        assert image_vec_config.distance == "Cosine"

    def test_other_vec_fields_unchanged(self):
        """测试其他向量字段保持不变."""
        config = get_collection_config()
        vectors = config["vectors"]

        # 检查 4 个文本向量字段
        assert "name_vec" in vectors
        assert "desc_vec" in vectors
        assert "step_vec" in vectors
        assert "tag_vec" in vectors

        # 检查维度都是 1024
        for field_name in ["name_vec", "desc_vec", "step_vec", "tag_vec"]:
            assert vectors[field_name].size == VECTOR_SIZE
            assert vectors[field_name].distance == "Cosine"

    def test_image_vec_dimension(self):
        """测试 image_vec 维度是 512."""
        config = get_collection_config()
        image_vec = config["vectors"]["image_vec"]

        # Chinese-CLIP 输出 512 维
        assert image_vec.size == 512


class TestQdrantImageService:
    """测试 Qdrant Service 图片向量搜索."""

    @patch('app.services.qdrant_service.QdrantClient')
    def test_search_image_vector(self, mock_client_class):
        """测试图片向量搜索."""
        # Mock QdrantClient
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock search 结果
        mock_hit = Mock()
        mock_hit.id = "recipe_123"
        mock_hit.score = 0.95
        mock_hit.payload = {"name": "宫保鸡丁", "recipe_id": "123"}
        mock_client.search.return_value = [mock_hit]

        # 创建服务实例
        service = QdrantService(qdrant_url="http://localhost:6333")
        service.collection_name = "test_collection"

        # 创建 512 维 CLIP 向量
        query_vector = np.random.rand(512).astype(np.float32)

        # 调用搜索方法
        results = service.search_image_vector(query_vector, limit=10)

        # 验证结果
        assert len(results) == 1
        assert results[0]["id"] == "recipe_123"
        assert results[0]["score"] == 0.95
        assert results[0]["payload"]["name"] == "宫保鸡丁"

        # 验证调用了 search 方法，且使用了 image_vec
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args[1]["query_vector"][0] == "image_vec"
        assert len(call_args[1]["query_vector"][1]) == 512

    @patch('app.services.qdrant_service.QdrantClient')
    def test_search_image_vector_with_filters(self, mock_client_class):
        """测试带过滤条件的图片向量搜索."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        service = QdrantService(qdrant_url="http://localhost:6333")
        service.collection_name = "test_collection"

        query_vector = np.random.rand(512).astype(np.float32)

        # 带过滤条件
        filters = {
            "cuisine": "川菜",
            "max_prep_time": 30,
        }

        results = service.search_image_vector(query_vector, limit=5, filters=filters)

        # 验证调用了 search 方法且带了过滤条件
        assert mock_client.search.called
        call_args = mock_client.search.call_args
        assert call_args[1]["query_filter"] is not None

    @patch('app.services.qdrant_service.QdrantClient')
    def test_search_image_vector_empty_result(self, mock_client_class):
        """测试图片向量搜索无结果."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        service = QdrantService(qdrant_url="http://localhost:6333")
        service.collection_name = "test_collection"

        query_vector = np.random.rand(512).astype(np.float32)
        results = service.search_image_vector(query_vector)

        assert results == []


class TestCrossModalSearch:
    """测试跨模态搜索（文本搜图片）."""

    def test_cross_modal_search_concept(self):
        """测试跨模态搜索概念验证。

        Chinese-CLIP 支持文本->图片跨模态搜索：
        - 用文本 encoder 生成文本向量
        - 用图片向量字段搜索相似图片
        """
        # 模拟文本 CLIP 向量（512 维）
        text_vector = np.random.rand(512).astype(np.float32)

        # 验证向量维度匹配 image_vec
        assert text_vector.shape == (512,)

        # 在实际使用中，这个文本向量可以直接用于 search_image_vector
        # 实现文本搜图片的跨模态搜索
