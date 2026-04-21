"""
测试 Docker Compose 配置和项目结构

TDD: 先写测试，再实现
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


class TestDockerComposeConfig:
    """测试 Docker Compose 配置"""

    @pytest.fixture
    def compose_config(self) -> Dict[str, Any]:
        """加载 docker-compose.yml 配置"""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        with open(compose_path, "r") as f:
            return yaml.safe_load(f)

    def test_compose_file_exists(self):
        """测试 docker-compose.yml 文件存在"""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml 应该存在"

    def test_compose_version(self, compose_config):
        """测试 Compose 版本"""
        assert compose_config.get("version") is not None, "应该指定 compose 版本"

    def test_postgres_service_exists(self, compose_config):
        """测试 PostgreSQL 服务配置"""
        services = compose_config.get("services", {})
        assert "postgres" in services, "应该配置 postgres 服务"

    def test_postgres_image(self, compose_config):
        """测试 PostgreSQL 镜像版本"""
        postgres = compose_config["services"]["postgres"]
        assert "pgvector" in postgres["image"], "应该使用 pgvector 镜像"

    def test_postgres_environment(self, compose_config):
        """测试 PostgreSQL 环境变量"""
        postgres = compose_config["services"]["postgres"]
        env = postgres.get("environment", {})
        assert any("POSTGRES_DB" in str(e) for e in env), "应该设置 POSTGRES_DB"
        assert any("POSTGRES_USER" in str(e) for e in env), "应该设置 POSTGRES_USER"
        assert any("POSTGRES_PASSWORD" in str(e) for e in env), "应该设置 POSTGRES_PASSWORD"

    def test_redis_service_exists(self, compose_config):
        """测试 Redis 服务配置"""
        services = compose_config.get("services", {})
        assert "redis" in services, "应该配置 redis 服务"

    def test_redis_image(self, compose_config):
        """测试 Redis 镜像版本"""
        redis = compose_config["services"]["redis"]
        assert "redis" in redis["image"], "应该使用 redis 镜像"
        assert "7" in redis["image"], "应该使用 Redis 7.x 版本"

    def test_qdrant_service_exists(self, compose_config):
        """测试 Qdrant 服务配置"""
        services = compose_config.get("services", {})
        assert "qdrant" in services, "应该配置 qdrant 服务"

    def test_qdrant_image(self, compose_config):
        """测试 Qdrant 镜像版本"""
        qdrant = compose_config["services"]["qdrant"]
        assert "qdrant" in qdrant["image"], "应该使用 qdrant 镜像"

    def test_elasticsearch_service_exists(self, compose_config):
        """测试 Elasticsearch 服务配置"""
        services = compose_config.get("services", {})
        assert "elasticsearch" in services, "应该配置 elasticsearch 服务"

    def test_elasticsearch_image(self, compose_config):
        """测试 Elasticsearch 镜像版本"""
        es = compose_config["services"]["elasticsearch"]
        assert "elasticsearch" in es["image"], "应该使用 elasticsearch 镜像"
        assert "8" in es["image"], "应该使用 ES 8.x 版本"

    def test_app_service_exists(self, compose_config):
        """测试应用服务配置"""
        services = compose_config.get("services", {})
        assert "app" in services, "应该配置 app 服务"

    def test_app_depends_on(self, compose_config):
        """测试应用服务依赖"""
        app = compose_config["services"]["app"]
        depends_on = app.get("depends_on", [])
        assert "postgres" in depends_on, "app 应该依赖 postgres"
        assert "redis" in depends_on, "app 应该依赖 redis"
        assert "qdrant" in depends_on, "app 应该依赖 qdrant"


class TestProjectStructure:
    """测试项目结构"""

    def test_app_directory_exists(self):
        """测试 app 目录存在"""
        app_path = Path(__file__).parent.parent / "app"
        assert app_path.exists(), "app 目录应该存在"
        assert app_path.is_dir(), "app 应该是一个目录"

    def test_app_main_exists(self):
        """测试 app/main.py 存在"""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        assert main_path.exists(), "app/main.py 应该存在"

    def test_app_core_directory_exists(self):
        """测试 app/core 目录存在"""
        core_path = Path(__file__).parent.parent / "app" / "core"
        assert core_path.exists(), "app/core 目录应该存在"

    def test_app_services_directory_exists(self):
        """测试 app/services 目录存在"""
        services_path = Path(__file__).parent.parent / "app" / "services"
        assert services_path.exists(), "app/services 目录应该存在"

    def test_app_api_directory_exists(self):
        """测试 app/api 目录存在"""
        api_path = Path(__file__).parent.parent / "app" / "api"
        assert api_path.exists(), "app/api 目录应该存在"

    def test_app_models_directory_exists(self):
        """测试 app/models 目录存在"""
        models_path = Path(__file__).parent.parent / "app" / "models"
        assert models_path.exists(), "app/models 目录应该存在"

    def test_tests_directory_exists(self):
        """测试 tests 目录存在"""
        tests_path = Path(__file__).parent.parent / "tests"
        assert tests_path.exists(), "tests 目录应该存在"

    def test_docs_directory_exists(self):
        """测试 docs 目录存在"""
        docs_path = Path(__file__).parent.parent / "docs"
        assert docs_path.exists(), "docs 目录应该存在"

    def test_requirements_exists(self):
        """测试 requirements.txt 存在"""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        assert req_path.exists(), "requirements.txt 应该存在"

    def test_env_example_exists(self):
        """测试 .env.example 存在"""
        env_path = Path(__file__).parent.parent / ".env.example"
        assert env_path.exists(), ".env.example 应该存在"


class TestRequirements:
    """测试依赖配置"""

    @pytest.fixture
    def requirements(self) -> str:
        """读取 requirements.txt"""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        with open(req_path, "r") as f:
            return f.read()

    def test_fastapi_required(self, requirements):
        """测试 FastAPI 依赖"""
        assert "fastapi" in requirements.lower(), "应该包含 fastapi"

    def test_sqlalchemy_required(self, requirements):
        """测试 SQLAlchemy 依赖"""
        assert "sqlalchemy" in requirements.lower(), "应该包含 sqlalchemy"
        assert "2.0" in requirements or "asyncpg" in requirements.lower(), "应该支持异步"

    def test_redis_required(self, requirements):
        """测试 Redis 依赖"""
        assert "redis" in requirements.lower(), "应该包含 redis"

    def test_qdrant_required(self, requirements):
        """测试 Qdrant 依赖"""
        assert "qdrant-client" in requirements.lower(), "应该包含 qdrant-client"

    def test_elasticsearch_required(self, requirements):
        """测试 Elasticsearch 依赖"""
        assert "elasticsearch" in requirements.lower(), "应该包含 elasticsearch"

    def test_loguru_required(self, requirements):
        """测试 Loguru 依赖"""
        assert "loguru" in requirements.lower(), "应该包含 loguru"

    def test_pytest_required(self, requirements):
        """测试 Pytest 依赖"""
        assert "pytest" in requirements.lower(), "应该包含 pytest"

    def test_pydantic_required(self, requirements):
        """测试 Pydantic 依赖"""
        assert "pydantic" in requirements.lower(), "应该包含 pydantic"
        assert "2" in requirements, "应该使用 pydantic v2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
