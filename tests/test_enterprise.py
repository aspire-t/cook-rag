"""
测试 B 端企业用户管理 (Task #31)

Sprint B 端 Phase 1
TDD: 测试企业模型、API、角色权限
"""

import pytest
from pathlib import Path


class TestEnterpriseModels:
    """测试企业数据模型"""

    @pytest.fixture
    def enterprise_model_file(self) -> str:
        """读取 app/models/enterprise.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "enterprise.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_enterprise_model_file_exists(self):
        """测试企业模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "enterprise.py"
        assert model_path.exists(), "app/models/enterprise.py 应该存在"

    def test_enterprise_table_name(self, enterprise_model_file):
        """测试企业表名"""
        assert '__tablename__ = "enterprises"' in enterprise_model_file, "表名应该是 enterprises"

    def test_enterprise_fields(self, enterprise_model_file):
        """测试企业字段"""
        assert "name" in enterprise_model_file, "应该有 name 字段"
        assert "unified_social_credit_code" in enterprise_model_file, "应该有统一社会信用代码字段"
        assert "legal_representative" in enterprise_model_file, "应该有法人代表字段"
        assert "contact_phone" in enterprise_model_file, "应该有联系电话字段"
        assert "contact_email" in enterprise_model_file, "应该有联系邮箱字段"
        assert "address" in enterprise_model_file, "应该有地址字段"

    def test_enterprise_status_fields(self, enterprise_model_file):
        """测试企业状态字段"""
        assert "is_verified" in enterprise_model_file, "应该有认证状态字段"
        assert "verified_at" in enterprise_model_file, "应该有认证时间字段"
        assert "is_active" in enterprise_model_file, "应该有激活状态字段"

    def test_enterprise_plan_fields(self, enterprise_model_file):
        """测试企业套餐字段"""
        assert "plan_type" in enterprise_model_file, "应该有套餐类型字段"
        assert "plan_expires_at" in enterprise_model_file, "应该有套餐过期时间字段"

    def test_enterprise_user_table_name(self, enterprise_model_file):
        """测试企业用户关联表名"""
        assert '__tablename__ = "enterprise_users"' in enterprise_model_file, "表名应该是 enterprise_users"

    def test_enterprise_user_fields(self, enterprise_model_file):
        """测试企业用户字段"""
        assert "user_id" in enterprise_model_file, "应该有 user_id 字段"
        assert "enterprise_id" in enterprise_model_file, "应该有 enterprise_id 字段"
        assert "role" in enterprise_model_file, "应该有 role 字段"
        assert "is_primary" in enterprise_model_file, "应该有 is_primary 字段"
        assert "joined_at" in enterprise_model_file, "应该有 joined_at 字段"

    def test_role_values(self, enterprise_model_file):
        """测试角色值"""
        assert "admin" in enterprise_model_file, "应该有 admin 角色"
        assert "chef" in enterprise_model_file, "应该有 chef 角色"
        assert "manager" in enterprise_model_file, "应该有 manager 角色"
        assert "purchaser" in enterprise_model_file, "应该有 purchaser 角色"
        assert "member" in enterprise_model_file, "应该有 member 角色"

    def test_unique_constraint(self, enterprise_model_file):
        """测试唯一约束"""
        assert "unique=True" in enterprise_model_file or "unique" in enterprise_model_file.lower(), "应该有用户 - 企业唯一约束"


class TestEnterpriseMigration:
    """测试企业迁移文件"""

    @pytest.fixture
    def migration_file(self) -> str:
        """读取 alembic/versions/004_enterprises.py"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "004_enterprises.py"
        if migration_path.exists():
            with open(migration_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_migration_file_exists(self):
        """测试迁移文件存在"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "004_enterprises.py"
        assert migration_path.exists(), "alembic/versions/004_enterprises.py 应该存在"

    def test_create_enterprises_table(self, migration_file):
        """测试创建企业表"""
        assert "create_table" in migration_file, "应该有创建表操作"
        assert "'enterprises'" in migration_file, "应该创建 enterprises 表"

    def test_create_enterprise_users_table(self, migration_file):
        """测试创建企业用户表"""
        assert "'enterprise_users'" in migration_file, "应该创建 enterprise_users 表"

    def test_foreign_keys(self, migration_file):
        """测试外键约束"""
        assert "ForeignKeyConstraint" in migration_file, "应该有外键约束"
        assert "ondelete='CASCADE'" in migration_file, "应该有级联删除"

    def test_indexes(self, migration_file):
        """测试索引"""
        assert "create_index" in migration_file, "应该创建索引"
        assert "user_id" in migration_file, "应该有 user_id 索引"
        assert "enterprise_id" in migration_file, "应该有 enterprise_id 索引"


class TestEnterpriseAPI:
    """测试企业 API"""

    @pytest.fixture
    def enterprise_api_file(self) -> str:
        """读取 app/api/v1/enterprise.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "enterprise.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_enterprise_api_file_exists(self):
        """测试企业 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "enterprise.py"
        assert api_path.exists(), "app/api/v1/enterprise.py 应该存在"

    def test_create_enterprise_endpoint(self, enterprise_api_file):
        """测试创建企业端点"""
        assert "POST" in enterprise_api_file or "router.post" in enterprise_api_file, "应该有创建企业端点"
        assert "/enterprises" in enterprise_api_file, "应该有 /enterprises 路径"

    def test_get_enterprise_endpoint(self, enterprise_api_file):
        """测试获取企业详情端点"""
        assert "router.get" in enterprise_api_file, "应该有获取企业端点"
        assert "/enterprises/{enterprise_id}" in enterprise_api_file, "应该有企业详情路径"

    def test_list_enterprises_endpoint(self, enterprise_api_file):
        """测试获取企业列表端点"""
        assert "router.get" in enterprise_api_file, "应该有获取企业列表端点"

    def test_invite_member_endpoint(self, enterprise_api_file):
        """测试邀请成员端点"""
        assert "/invite" in enterprise_api_file, "应该有邀请成员端点"
        assert "router.post" in enterprise_api_file, "邀请应该是 POST 请求"

    def test_update_role_endpoint(self, enterprise_api_file):
        """测试更新角色端点"""
        assert "/role" in enterprise_api_file, "应该有更新角色端点"
        assert "router.put" in enterprise_api_file, "更新角色应该是 PUT 请求"

    def test_remove_member_endpoint(self, enterprise_api_file):
        """测试移除成员端点"""
        assert "router.delete" in enterprise_api_file, "应该有删除成员端点"

    def test_admin_permission_check(self, enterprise_api_file):
        """测试管理员权限检查"""
        assert "admin" in enterprise_api_file, "应该有管理员权限检查"
        assert "role" in enterprise_api_file, "应该有角色检查"


class TestIntegration:
    """测试集成"""

    @pytest.fixture
    def routes_file(self) -> str:
        """读取 app/api/routes.py"""
        routes_path = Path(__file__).parent.parent / "app" / "api" / "routes.py"
        if routes_path.exists():
            with open(routes_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_enterprise_router_registered(self, routes_file):
        """测试企业路由已注册"""
        assert "enterprise" in routes_file, "应该导入 enterprise 模块"
        assert 'prefix="/enterprise"' in routes_file or "prefix='/enterprise'" in routes_file, "应该注册企业路由"

    @pytest.fixture
    def models_init_file(self) -> str:
        """读取 app/models/__init__.py"""
        init_path = Path(__file__).parent.parent / "app" / "models" / "__init__.py"
        if init_path.exists():
            with open(init_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_enterprise_model_exported(self, models_init_file):
        """测试企业模型已导出"""
        assert "Enterprise" in models_init_file, "应该导出 Enterprise 模型"
        assert "EnterpriseUser" in models_init_file, "应该导出 EnterpriseUser 模型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
