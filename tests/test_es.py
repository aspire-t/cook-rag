"""
测试 Elasticsearch 配置

Task #4 - Sprint 2
TDD: 先写测试，再实现
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestElasticsearchConfig:
    """测试 Elasticsearch 配置"""

    @pytest.fixture
    def config_file(self) -> str:
        """读取 app/core/config.py"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_config_file_exists(self):
        """测试配置文件存在"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        assert config_path.exists(), "app/core/config.py 应该存在"

    def test_es_url_configured(self, config_file):
        """测试 ES URL 配置"""
        assert "ELASTICSEARCH" in config_file or "es_url" in config_file.lower(), "应该配置 Elasticsearch URL"

    def test_es_index_configured(self, config_file):
        """测试 ES 索引配置"""
        assert "INDEX" in config_file or "index" in config_file.lower(), "应该配置 ES 索引名称"


class TestElasticsearchService:
    """测试 Elasticsearch 服务"""

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

    def test_es_client_initialization(self, es_service_file):
        """测试 ES 客户端初始化"""
        assert "Elasticsearch" in es_service_file or "AsyncElasticsearch" in es_service_file, "应该初始化 ES 客户端"

    def test_es_index_creation(self, es_service_file):
        """测试索引创建"""
        assert "create_index" in es_service_file.lower() or "indices.create" in es_service_file.lower(), "应该创建索引"

    def test_ik_analyzer_configured(self, es_service_file):
        """测试 IK 分词器配置"""
        assert "ik" in es_service_file.lower(), "应该配置 IK 分词器"

    def test_bm25_configured(self, es_service_file):
        """测试 BM25 参数配置"""
        assert "bm25" in es_service_file.lower() or "similarity" in es_service_file.lower(), "应该配置 BM25 相似度"


class TestElasticsearchIndexSchema:
    """测试 ES 索引 Schema"""

    @pytest.fixture
    def es_schema_file(self) -> str:
        """读取 app/services/es_schema.py 或相关文件"""
        schema_path = Path(__file__).parent.parent / "app" / "services" / "es_schema.py"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_es_schema_file_exists(self):
        """测试 Schema 文件存在"""
        schema_path = Path(__file__).parent.parent / "app" / "services" / "es_schema.py"
        assert schema_path.exists(), "app/services/es_schema.py 应该存在"

    def test_recipe_index_mapping(self, es_schema_file):
        """测试菜谱索引映射"""
        assert "recipes" in es_schema_file.lower(), "应该定义 recipes 索引"
        assert "properties" in es_schema_file.lower() or "mapping" in es_schema_file.lower(), "应该定义 mapping"

    def test_text_fields_with_ik(self, es_schema_file):
        """测试文本字段 IK 分词器"""
        assert "ik_max_word" in es_schema_file or "ik_smart" in es_schema_file, "文本字段应该使用 IK 分词器"

    def test_keyword_fields(self, es_schema_file):
        """测试 keyword 字段"""
        assert "keyword" in es_schema_file.lower(), "应该定义 keyword 类型字段"


class TestElasticsearchDockerConfig:
    """测试 Docker Compose 中的 ES 配置"""

    @pytest.fixture
    def compose_config(self) -> Dict[str, Any]:
        """读取 docker-compose.yml 配置"""
        import yaml
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_es_service_exists(self, compose_config):
        """测试 ES 服务存在"""
        services = compose_config.get("services", {})
        assert "elasticsearch" in services, "应该配置 elasticsearch 服务"

    def test_es_image_version(self, compose_config):
        """测试 ES 镜像版本"""
        es = compose_config["services"]["elasticsearch"]
        assert "8." in es["image"], "应该使用 ES 8.x 版本"

    def test_es_security_disabled(self, compose_config):
        """测试 ES 安全禁用"""
        es = compose_config["services"]["elasticsearch"]
        env = es.get("environment", {})
        assert any("xpack.security.enabled=false" in str(e) for e in env), "应该禁用 xpack 安全"


class TestElasticsearchHealthCheck:
    """测试 ES 健康检查"""

    @pytest.fixture
    def es_health_file(self) -> str:
        """读取 app/services/es_health.py 或相关文件"""
        health_path = Path(__file__).parent.parent / "app" / "services" / "es_health.py"
        if health_path.exists():
            with open(health_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_es_health_check_exists(self):
        """测试健康检查文件存在"""
        health_path = Path(__file__).parent.parent / "app" / "services" / "es_health.py"
        assert health_path.exists(), "app/services/es_health.py 应该存在"

    def test_health_check_function(self, es_health_file):
        """测试健康检查函数"""
        assert "health" in es_health_file.lower() or "ping" in es_health_file.lower(), "应该有健康检查函数"

    def test_cluster_status_check(self, es_health_file):
        """测试集群状态检查"""
        assert "cluster" in es_health_file.lower() or "green" in es_health_file.lower() or "yellow" in es_health_file.lower(), "应该检查集群状态"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
