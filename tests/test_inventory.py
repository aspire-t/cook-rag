"""
测试 B 端库存管理 (Task #33)

Sprint B 端 Phase 2
TDD: 测试库存模型、入库/出库、库存预警、保质期管理
"""

import pytest
from pathlib import Path


class TestInventoryModels:
    """测试库存数据模型"""

    @pytest.fixture
    def inventory_model_file(self) -> str:
        """读取 app/models/inventory.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "inventory.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_inventory_model_file_exists(self):
        """测试库存模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "inventory.py"
        assert model_path.exists(), "app/models/inventory.py 应该存在"

    def test_inventory_table_name(self, inventory_model_file):
        """测试表名"""
        assert '__tablename__ = "inventory"' in inventory_model_file, "表名应该是 inventory"

    def test_inventory_fields(self, inventory_model_file):
        """测试库存核心字段"""
        assert "enterprise_id" in inventory_model_file, "应该有 enterprise_id 字段"
        assert "ingredient_name" in inventory_model_file, "应该有食材名称字段"
        assert "quantity" in inventory_model_file, "应该有数量字段"
        assert "unit" in inventory_model_file, "应该有单位字段"

    def test_stock_alert_fields(self, inventory_model_file):
        """测试库存预警字段"""
        assert "min_stock" in inventory_model_file, "应该有最低库存字段"
        assert "max_stock" in inventory_model_file, "应该有最高库存字段"

    def test_expiry_fields(self, inventory_model_file):
        """测试保质期字段"""
        assert "expiry_date" in inventory_model_file, "应该有保质期日期字段"
        assert "batch_number" in inventory_model_file, "应该有批次号字段"

    def test_location_field(self, inventory_model_file):
        """测试库位字段"""
        assert "location" in inventory_model_file, "应该有库位字段"


class TestInventoryTransaction:
    """测试库存交易记录"""

    @pytest.fixture
    def inventory_transaction_model_file(self) -> str:
        """读取 app/models/inventory_transaction.py"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "inventory_transaction.py"
        if model_path.exists():
            with open(model_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_inventory_transaction_model_file_exists(self):
        """测试库存交易模型文件存在"""
        model_path = Path(__file__).parent.parent / "app" / "models" / "inventory_transaction.py"
        assert model_path.exists(), "app/models/inventory_transaction.py 应该存在"

    def test_transaction_table_name(self, inventory_transaction_model_file):
        """测试表名"""
        assert '__tablename__ = "inventory_transactions"' in inventory_transaction_model_file, "表名应该是 inventory_transactions"

    def test_transaction_fields(self, inventory_transaction_model_file):
        """测试交易记录字段"""
        assert "enterprise_id" in inventory_transaction_model_file, "应该有 enterprise_id 字段"
        assert "ingredient_name" in inventory_transaction_model_file, "应该有食材名称字段"
        assert "change_quantity" in inventory_transaction_model_file, "应该有变动数量字段"
        assert "transaction_type" in inventory_transaction_model_file, "应该有交易类型字段"
        assert "before_quantity" in inventory_transaction_model_file, "应该有变动前数量字段"
        assert "after_quantity" in inventory_transaction_model_file, "应该有变动后数量字段"
        assert "created_by" in inventory_transaction_model_file, "应该有操作人字段"

    def test_transaction_type_values(self, inventory_transaction_model_file):
        """测试交易类型值"""
        assert "in" in inventory_transaction_model_file.lower() or "入库" in inventory_transaction_model_file, "应该有入库类型"
        assert "out" in inventory_transaction_model_file.lower() or "出库" in inventory_transaction_model_file, "应该有出库类型"


class TestInventoryMigration:
    """测试库存迁移文件"""

    @pytest.fixture
    def migration_file(self) -> str:
        """读取 alembic/versions/006_inventory.py"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "006_inventory.py"
        if migration_path.exists():
            with open(migration_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_migration_file_exists(self):
        """测试迁移文件存在"""
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "006_inventory.py"
        assert migration_path.exists(), "alembic/versions/006_inventory.py 应该存在"

    def test_create_inventory_table(self, migration_file):
        """测试创建库存表"""
        assert "create_table" in migration_file, "应该有创建表操作"
        assert "'inventory'" in migration_file, "应该创建 inventory 表"

    def test_create_transaction_table(self, migration_file):
        """测试创建交易记录表"""
        assert "'inventory_transactions'" in migration_file, "应该创建 inventory_transactions 表"

    def test_indexes(self, migration_file):
        """测试索引"""
        assert "create_index" in migration_file, "应该创建索引"
        assert "enterprise_id" in migration_file, "应该有 enterprise_id 索引"
        assert "expiry_date" in migration_file, "应该有 expiry_date 索引"


class TestInventoryService:
    """测试库存服务"""

    @pytest.fixture
    def inventory_service_file(self) -> str:
        """读取 app/services/inventory_service.py"""
        service_path = Path(__file__).parent.parent / "app" / "services" / "inventory_service.py"
        if service_path.exists():
            with open(service_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_inventory_service_file_exists(self):
        """测试库存服务文件存在"""
        service_path = Path(__file__).parent.parent / "app" / "services" / "inventory_service.py"
        assert service_path.exists(), "app/services/inventory_service.py 应该存在"

    def test_stock_in_method(self, inventory_service_file):
        """测试入库方法"""
        assert "stock_in" in inventory_service_file or "入库" in inventory_service_file, "应该有入库方法"

    def test_stock_out_method(self, inventory_service_file):
        """测试出库方法"""
        assert "stock_out" in inventory_service_file or "出库" in inventory_service_file, "应该有出库方法"

    def test_alert_check_method(self, inventory_service_file):
        """测试预警检查方法"""
        assert "alert" in inventory_service_file.lower() or "预警" in inventory_service_file, "应该有预警检查方法"

    def test_expiry_check_method(self, inventory_service_file):
        """测试保质期检查方法"""
        assert "expiry" in inventory_service_file.lower() or "保质" in inventory_service_file, "应该有保质期检查方法"


class TestInventoryAPI:
    """测试库存 API"""

    @pytest.fixture
    def inventory_api_file(self) -> str:
        """读取 app/api/v1/inventory.py"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "inventory.py"
        if api_path.exists():
            with open(api_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_inventory_api_file_exists(self):
        """测试库存 API 文件存在"""
        api_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "inventory.py"
        assert api_path.exists(), "app/api/v1/inventory.py 应该存在"

    def test_stock_in_endpoint(self, inventory_api_file):
        """测试入库端点"""
        assert "router.post" in inventory_api_file, "应该有 POST 端点"
        assert "/stock-in" in inventory_api_file or "stock_in" in inventory_api_file, "应该有入库端点"

    def test_stock_out_endpoint(self, inventory_api_file):
        """测试出库端点"""
        assert "/stock-out" in inventory_api_file or "stock_out" in inventory_api_file, "应该有出库端点"

    def test_inventory_list_endpoint(self, inventory_api_file):
        """测试库存列表端点"""
        assert "router.get" in inventory_api_file, "应该有 GET 端点"

    def test_alert_endpoint(self, inventory_api_file):
        """测试预警端点"""
        assert "/alert" in inventory_api_file or "alert" in inventory_api_file, "应该有预警端点"


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

    def test_inventory_router_registered(self, routes_file):
        """测试库存路由已注册"""
        assert "inventory" in routes_file, "应该导入 inventory 模块"
        assert 'prefix="/inventory"' in routes_file or "prefix='/inventory'" in routes_file, "应该注册库存路由"

    @pytest.fixture
    def models_init_file(self) -> str:
        """读取 app/models/__init__.py"""
        init_path = Path(__file__).parent.parent / "app" / "models" / "__init__.py"
        if init_path.exists():
            with open(init_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_inventory_model_exported(self, models_init_file):
        """测试库存模型已导出"""
        assert "Inventory" in models_init_file, "应该导出 Inventory 模型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
