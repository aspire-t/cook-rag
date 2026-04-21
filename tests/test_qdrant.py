"""
测试 Qdrant 向量索引配置

Task #5 - Sprint 2
TDD: 先写测试，再实现
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class TestQdrantConfig:
    """测试 Qdrant 配置"""

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

    def test_qdrant_url_configured(self, config_file):
        """测试 Qdrant URL 配置"""
        assert "QDRANT" in config_file, "应该配置 QDRANT_URL"

    def test_qdrant_collection_configured(self, config_file):
        """测试 Qdrant Collection 配置"""
        assert "COLLECTION" in config_file or "collection" in config_file.lower(), "应该配置 Qdrant Collection 名称"


class TestQdrantService:
    """测试 Qdrant 服务"""

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

    def test_qdrant_client_initialization(self, qdrant_service_file):
        """测试 Qdrant 客户端初始化"""
        assert "QdrantClient" in qdrant_service_file or "qdrant_client" in qdrant_service_file.lower(), "应该初始化 Qdrant 客户端"

    def test_collection_creation(self, qdrant_service_file):
        """测试 Collection 创建"""
        assert "create_collection" in qdrant_service_file.lower(), "应该创建 Collection"

    def test_collection_exists_check(self, qdrant_service_file):
        """测试 Collection 存在检查"""
        assert "collection_exists" in qdrant_service_file.lower() or "exists" in qdrant_service_file.lower(), "应该检查 Collection 是否存在"


class TestQdrantCollectionSchema:
    """测试 Qdrant Collection Schema"""

    @pytest.fixture
    def qdrant_schema_file(self) -> str:
        """读取 app/services/qdrant_schema.py"""
        schema_path = Path(__file__).parent.parent / "app" / "services" / "qdrant_schema.py"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_qdrant_schema_file_exists(self):
        """测试 Schema 文件存在"""
        schema_path = Path(__file__).parent.parent / "app" / "services" / "qdrant_schema.py"
        assert schema_path.exists(), "app/services/qdrant_schema.py 应该存在"

    def test_four_vector_fields(self, qdrant_schema_file):
        """测试四路向量字段"""
        assert "name_vec" in qdrant_schema_file.lower(), "应该定义 name_vec 向量"
        assert "desc_vec" in qdrant_schema_file.lower(), "应该定义 desc_vec 向量"
        assert "step_vec" in qdrant_schema_file.lower(), "应该定义 step_vec 向量"
        assert "tag_vec" in qdrant_schema_file.lower(), "应该定义 tag_vec 向量"

    def test_vector_size(self, qdrant_schema_file):
        """测试向量维度"""
        assert "size" in qdrant_schema_file.lower() and ("1024" in qdrant_schema_file or "768" in qdrant_schema_file), "应该定义向量维度"

    def test_cosine_distance(self, qdrant_schema_file):
        """测试余弦距离"""
        assert "cosine" in qdrant_schema_file.lower() or "COSINE" in qdrant_schema_file, "应该使用余弦距离"

    def test_payload_schema(self, qdrant_schema_file):
        """测试 Payload Schema"""
        assert "payload" in qdrant_schema_file.lower() or "PayloadSchemaType" in qdrant_schema_file, "应该定义 Payload Schema"

    def test_payload_fields(self, qdrant_schema_file):
        """测试 Payload 字段"""
        assert "cuisine" in qdrant_schema_file.lower(), "应该定义 cuisine 字段"
        assert "difficulty" in qdrant_schema_file.lower(), "应该定义 difficulty 字段"
        assert "user_id" in qdrant_schema_file.lower(), "应该定义 user_id 字段"


class TestQdrantDockerConfig:
    """测试 Docker Compose 中的 Qdrant 配置"""

    @pytest.fixture
    def compose_config(self) -> Dict[str, Any]:
        """读取 docker-compose.yml 配置"""
        import yaml
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_qdrant_service_exists(self, compose_config):
        """测试 Qdrant 服务存在"""
        services = compose_config.get("services", {})
        assert "qdrant" in services, "应该配置 qdrant 服务"

    def test_qdrant_image_version(self, compose_config):
        """测试 Qdrant 镜像版本"""
        qdrant = compose_config["services"]["qdrant"]
        assert "qdrant" in qdrant["image"], "应该使用 qdrant 镜像"

    def test_qdrant_ports(self, compose_config):
        """测试 Qdrant 端口"""
        qdrant = compose_config["services"]["qdrant"]
        ports = qdrant.get("ports", [])
        assert any("6333" in str(p) for p in ports), "应该暴露 6333 端口"


class TestQdrantHealthCheck:
    """测试 Qdrant 健康检查"""

    @pytest.fixture
    def qdrant_health_file(self) -> str:
        """读取 app/services/qdrant_health.py"""
        health_path = Path(__file__).parent.parent / "app" / "services" / "qdrant_health.py"
        if health_path.exists():
            with open(health_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_qdrant_health_check_exists(self):
        """测试健康检查文件存在"""
        health_path = Path(__file__).parent.parent / "app" / "services" / "qdrant_health.py"
        assert health_path.exists(), "app/services/qdrant_health.py 应该存在"

    def test_health_check_function(self, qdrant_health_file):
        """测试健康检查函数"""
        assert "health" in qdrant_health_file.lower() or "check" in qdrant_health_file.lower(), "应该有健康检查函数"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
