"""
测试 B 端采购规划 (Task #34)

Sprint B 端 Phase 2
TDD: 测试供应商模型、采购订单、采购清单生成
"""

import pytest
from pathlib import Path


class TestSupplierModels:
    """测试供应商数据模型"""

    @pytest.fixture
    def supplier_model_file(self) -> str:
        """读取 app/models/supplier.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "supplier.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_supplier_model_file_exists(self):
        """测试供应商模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "supplier.py"
        assert model_path.exists(), "app/models/supplier.py 应该存在"

    def test_supplier_table_name(self, supplier_model_file):
        """测试表名"""
        assert '__tablename__ = "suppliers"' in supplier_model_file, "表名应该是 suppliers"

    def test_supplier_fields(self, supplier_model_file):
        """测试供应商标段"""
        assert "enterprise_id" in supplier_model_file, "应该有 enterprise_id 字段"
        assert "name" in supplier_model_file, "应该有供应商名称字段"
        assert "contact_person" in supplier_model_file, "应该有联系人字段"
        assert "contact_phone" in supplier_model_file, "应该有联系电话字段"
        assert "address" in supplier_model_file, "应该有地址字段"

    def test_supplier_status_fields(self, supplier_model_file):
        """测试供应商状态字段"""
        assert "is_active" in supplier_model_file, "应该有激活状态字段"
        assert "rating" in supplier_model_file or "level" in supplier_model_file, "应该有评级字段"


class TestPurchaseOrderModels:
    """测试采购订单数据模型"""

    @pytest.fixture
    def purchase_order_model_file(self) -> str:
        """读取 app/models/purchase_order.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "purchase_order.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_purchase_order_model_file_exists(self):
        """测试采购订单模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "purchase_order.py"
        assert model_path.exists(), "app/models/purchase_order.py 应该存在"

    def test_purchase_order_table_name(self, purchase_order_model_file):
        """测试表名"""
        assert '__tablename__ = "purchase_orders"' in purchase_order_model_file, "表名应该是 purchase_orders"

    def test_purchase_order_fields(self, purchase_order_model_file):
        """测试采购订单字段"""
        assert "enterprise_id" in purchase_order_model_file, "应该有 enterprise_id 字段"
        assert "supplier_id" in purchase_order_model_file, "应该有 supplier_id 字段"
        assert "order_number" in purchase_order_model_file, "应该有订单号字段"
        assert "status" in purchase_order_model_file, "应该有状态字段"
        assert "total_amount" in purchase_order_model_file, "应该有总金额字段"
        assert "items" in purchase_order_model_file, "应该有订单物品字段 (JSON)"

    def test_purchase_order_status_values(self, purchase_order_model_file):
        """测试订单状态值"""
        assert "pending" in purchase_order_model_file, "应该有 pending 状态"
        assert "approved" in purchase_order_model_file or "confirmed" in purchase_order_model_file, "应该有确认状态"
        assert "received" in purchase_order_model_file or "completed" in purchase_order_model_file, "应该有已完成状态"


class TestPurchaseMigration:
    """测试采购迁移文件"""

    @pytest.fixture
    def migration_file(self) -> str:
        """读取 alembic/versions/007_purchase_orders.py"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "007_purchase_orders.py"
        if migration_path.exists():
            with open(migration_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_migration_file_exists(self):
        """测试迁移文件存在"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "007_purchase_orders.py"
        assert migration_path.exists(), "alembic/versions/007_purchase_orders.py 应该存在"

    def test_create_suppliers_table(self, migration_file):
        """测试创建供应商表"""
        assert "create_table" in migration_file, "应该有创建表操作"
        assert "'suppliers'" in migration_file, "应该创建 suppliers 表"

    def test_create_purchase_orders_table(self, migration_file):
        """测试创建采购订单表"""
        assert "'purchase_orders'" in migration_file, "应该创建 purchase_orders 表"

    def test_foreign_keys(self, migration_file):
        """测试外键约束"""
        assert "ForeignKeyConstraint" in migration_file, "应该有外键约束"
        assert "supplier_id" in migration_file, "应该有 supplier_id 外键"


class TestPurchaseService:
    """测试采购服务"""

    @pytest.fixture
    def purchase_service_file(self) -> str:
        """读取 app/services/purchase_service.py"""
        service_path = Path(__file__).parent.parent / "app" / "services" / "purchase_service.py"
        if service_path.exists():
            with open(service_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_purchase_service_file_exists(self):
        """测试采购服务文件存在"""
        service_path = Path(__file__).parent.parent / "app" / "services" / "purchase_service.py"
        assert service_path.exists(), "app/services/purchase_service.py 应该存在"

    def test_purchase_plan_generation(self, purchase_service_file):
        """测试采购清单生成功能"""
        assert "generate" in purchase_service_file.lower() or "plan" in purchase_service_file.lower() or "采购" in purchase_service_file, "应该有采购清单生成功能"

    def test_create_purchase_order(self, purchase_service_file):
        """测试创建采购订单功能"""
        assert "create" in purchase_service_file.lower() or "order" in purchase_service_file.lower() or "订单" in purchase_service_file, "应该有创建采购订单功能"


class TestPurchaseAPI:
    """测试采购 API"""

    @pytest.fixture
    def purchase_api_file(self) -> str:
        """读取 app/api/v1/purchase.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "purchase.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_purchase_api_file_exists(self):
        """测试采购 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "purchase.py"
        assert api_path.exists(), "app/api/v1/purchase.py 应该存在"

    def test_purchase_plan_endpoint(self, purchase_api_file):
        """测试采购清单生成端点"""
        assert "router.post" in purchase_api_file, "应该有 POST 端点"
        assert "plan" in purchase_api_file.lower() or "purchase" in purchase_api_file.lower(), "应该有采购规划端点"

    def test_create_order_endpoint(self, purchase_api_file):
        """测试创建订单端点"""
        assert "/orders" in purchase_api_file, "应该有订单端点"

    def test_list_orders_endpoint(self, purchase_api_file):
        """测试订单列表端点"""
        assert "router.get" in purchase_api_file, "应该有 GET 端点"


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

    def test_purchase_router_registered(self, routes_file):
        """测试采购路由已注册"""
        assert "purchase" in routes_file, "应该导入 purchase 模块"
        assert 'prefix="/purchase"' in routes_file or "prefix='/purchase'" in routes_file, "应该注册采购路由"

    @pytest.fixture
    def models_init_file(self) -> str:
        """读取 app/models/__init__.py"""
        init_path = Path(__file__).parent.parent / "app" / "models" / "__init__.py"
        if init_path.exists():
            with open(init_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_purchase_models_exported(self, models_init_file):
        """测试采购模型已导出"""
        assert "Supplier" in models_init_file, "应该导出 Supplier 模型"
        assert "PurchaseOrder" in models_init_file, "应该导出 PurchaseOrder 模型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
