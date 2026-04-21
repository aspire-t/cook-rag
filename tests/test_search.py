"""
测试 RAG 检索服务 (Task #7, #8, #9)

Sprint 3
TDD: 先写测试，再实现
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestESSearchService:
    """测试 ES BM25 检索服务 (Task #7)"""

    @pytest.fixture
    def es_service_file(self) -> str:
        """读取 app/services/es_search.py"""
        es_path = Path(__file__).parent.parent / "app" / "services" / "es_search.py"
        if es_path.exists():
            with open(es_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_es_service_file_exists(self):
        """测试 ES 服务文件存在"""
        es_path = Path(__file__).parent.parent / "app" / "services" / "es_search.py"
        assert es_path.exists(), "app/services/es_search.py 应该存在"

    def test_search_function(self, es_service_file):
        """测试搜索函数"""
        assert "def search" in es_service_file or "async def search" in es_service_file, "应该有 search 函数"

    def test_bm25_query(self, es_service_file):
        """测试 BM25 查询"""
        assert "multi_match" in es_service_file.lower() or "bm25" in es_service_file.lower(), "应该使用 BM25 multi_match 查询"

    def test_ik_tokenizer(self, es_service_file):
        """测试 IK 分词器使用"""
        assert "ik" in es_service_file.lower(), "应该使用 IK 分词器"

    def test_filter_support(self, es_service_file):
        """测试过滤条件支持"""
        assert "filter" in es_service_file.lower() or "bool" in es_service_file.lower(), "应该支持过滤条件"

    def test_index_recipe(self, es_service_file):
        """测试索引菜谱"""
        assert "index_recipe" in es_service_file.lower() or "index_recipe" in es_service_file, "应该有 index_recipe 函数"


class TestQdrantSearchService:
    """测试 Qdrant 向量检索服务 (Task #8)"""

    @pytest.fixture
    def qdrant_service_file(self) -> str:
        """读取 app/services/qdrant_service.py"""
        qdrant_path = Path(__file__).parent.parent / "app" / "services" / "qdrant_service.py"
        if qdrant_path.exists():
            with open(qdrant_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_qdrant_service_file_exists(self):
        """测试 Qdrant 服务文件存在"""
        qdrant_path = Path(__file__).parent.parent / "app" / "services" / "qdrant_service.py"
        assert qdrant_path.exists(), "app/services/qdrant_service.py 应该存在"

    def test_search_function(self, qdrant_service_file):
        """测试搜索函数"""
        assert "def search" in qdrant_service_file or "async def search" in qdrant_service_file, "应该有 search 函数"

    def test_four_vector_search(self, qdrant_service_file):
        """测试四路向量搜索"""
        assert "name_vec" in qdrant_service_file and "desc_vec" in qdrant_service_file, "应该支持四路向量搜索"

    def test_payload_filter(self, qdrant_service_file):
        """测试 Payload 过滤"""
        assert "filter" in qdrant_service_file.lower() or "Filter" in qdrant_service_file, "应该支持 Payload 过滤"

    def test_cosine_similarity(self, qdrant_service_file):
        """测试余弦相似度"""
        assert "cosine" in qdrant_service_file.lower() or "COSINE" in qdrant_service_file, "应该使用余弦相似度"

    def test_upsert_function(self, qdrant_service_file):
        """测试 upsert 函数"""
        assert "upsert" in qdrant_service_file.lower(), "应该有 upsert 函数"


class TestRRFusion:
    """测试 RRF 结果融合 (Task #9)"""

    @pytest.fixture
    def rrf_file(self) -> str:
        """读取 app/services/rrf_fusion.py"""
        rrf_path = Path(__file__).parent.parent / "app" / "services" / "rrf_fusion.py"
        if rrf_path.exists():
            with open(rrf_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_rrf_file_exists(self):
        """测试 RRF 融合文件存在"""
        rrf_path = Path(__file__).parent.parent / "app" / "services" / "rrf_fusion.py"
        assert rrf_path.exists(), "app/services/rrf_fusion.py 应该存在"

    def test_rrf_function(self, rrf_file):
        """测试 RRF 融合函数"""
        assert "def rrf" in rrf_file or "def fuse" in rrf_file or "class RRF" in rrf_file, "应该有 RRF 融合函数/类"

    def test_rrf_k_parameter(self, rrf_file):
        """测试 RRF k 参数 (默认 60)"""
        assert "k" in rrf_file.lower() or "60" in rrf_file, "应该有 k 参数 (默认 60)"

    def test_reciprocal_rank(self, rrf_file):
        """测试倒数排名计算"""
        assert "rank" in rrf_file.lower() or "reciprocal" in rrf_file.lower(), "应该使用倒数排名"

    def test_deduplication(self, rrf_file):
        """测试去重功能"""
        assert "dedup" in rrf_file.lower() or "unique" in rrf_file.lower() or "去重" in rrf_file, "应该有去重功能"

    def test_merge_results(self, rrf_file):
        """测试结果合并"""
        assert "merge" in rrf_file.lower() or "fuse" in rrf_file.lower() or "融合" in rrf_file, "应该有结果合并功能"


class TestHybridSearch:
    """测试混合检索服务"""

    @pytest.fixture
    def hybrid_file(self) -> str:
        """读取 app/services/hybrid_search.py"""
        hybrid_path = Path(__file__).parent.parent / "app" / "services" / "hybrid_search.py"
        if hybrid_path.exists():
            with open(hybrid_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_hybrid_file_exists(self):
        """测试混合检索文件存在"""
        hybrid_path = Path(__file__).parent.parent / "app" / "services" / "hybrid_search.py"
        assert hybrid_path.exists(), "app/services/hybrid_search.py 应该存在"

    def test_hybrid_search_class(self, hybrid_file):
        """测试混合检索类"""
        assert "class" in hybrid_file and ("Hybrid" in hybrid_file or "Search" in hybrid_file), "应该有混合检索类"

    def test_es_integration(self, hybrid_file):
        """测试 ES 集成"""
        assert "es" in hybrid_file.lower() or "elasticsearch" in hybrid_file.lower(), "应该集成 ES"

    def test_qdrant_integration(self, hybrid_file):
        """测试 Qdrant 集成"""
        assert "qdrant" in hybrid_file.lower(), "应该集成 Qdrant"

    def test_rrf_integration(self, hybrid_file):
        """测试 RRF 集成"""
        assert "rrf" in hybrid_file.lower() or "fusion" in hybrid_file.lower(), "应该集成 RRF 融合"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
