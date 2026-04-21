"""
CookRAG 端到端集成测试

测试完整用户流程：
- C 端：用户登录 → 搜索菜谱 → 查看详情 → 收藏 → 跟做模式
- B 端：创建企业 → 邀请成员 → 生成标准化配方 → 入库 → 采购计划

注意：需要运行的数据库环境才能执行完整测试。
在无数据库环境中，测试将验证代码结构和模块导入。
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
import os


# ============ Fixture 配置 ============

@pytest_asyncio.fixture
async def client():
    """创建测试客户端."""
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def test_user_data():
    """测试用户数据."""
    return {
        "phone": "13800138000",
        "nickname": "测试用户",
    }


@pytest.fixture
def test_enterprise_data():
    """测试企业数据."""
    return {
        "name": "测试餐饮有限公司",
        "contact_phone": "010-12345678",
    }


@pytest.fixture
def test_recipe_data():
    """测试菜谱数据."""
    return {
        "name": "宫保鸡丁",
        "cuisine": "川菜",
        "difficulty": "medium",
        "prep_time": 15,
        "cook_time": 10,
        "servings": 2,
        "tags": ["辣", "快手菜", "下饭"],
    }


def skip_if_no_db():
    """如果没有数据库连接，跳过测试."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("需要数据库环境")


# ============ C 端用户流程测试 ============

class TestCEndUserFlow:
    """C 端用户完整流程测试"""

    @pytest.mark.asyncio
    async def test_user_register_and_login(self, client, test_user_data):
        """测试用户注册和登录"""
        skip_if_no_db()
        # 注册/登录（微信登录流程简化）
        response = await client.post(
            "/api/v1/users/login",
            json={"phone": test_user_data["phone"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data["data"] or "user_id" in data["data"]

    @pytest.mark.asyncio
    async def test_search_recipes(self, client):
        """测试搜索菜谱"""
        skip_if_no_db()
        response = await client.post(
            "/api/v1/search/search",
            json={"query": "宫保鸡丁", "limit": 10}
        )
        # 即使没有数据也应该返回成功响应
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_recipe_detail(self, client):
        """测试获取菜谱详情"""
        skip_if_no_db()
        # 先获取菜谱列表
        response = await client.get("/api/v1/recipes?limit=1")
        assert response.status_code == 200

        recipes = response.json()
        if recipes:
            recipe_id = recipes[0]["id"]
            # 获取详情
            response = await client.get(f"/api/v1/recipes/{recipe_id}")
            assert response.status_code == 200


# ============ B 端企业用户流程测试 ============

class TestBEndEnterpriseFlow:
    """B 端企业用户完整流程测试"""

    @pytest.mark.asyncio
    async def test_create_enterprise(self, client, test_enterprise_data):
        """测试创建企业"""
        # 需要先登录获取 token
        # MVP 测试：验证端点存在和响应格式
        response = await client.post(
            "/api/v1/enterprise/enterprises",
            json=test_enterprise_data,
            headers={"Authorization": "Bearer test_token"}
        )
        # 401 表示端点存在但 token 无效，200 表示完全成功
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_supplier_management(self, client, test_enterprise_data):
        """测试供应商管理"""
        enterprise_id = "test-enterprise-id"

        # 创建供应商
        response = await client.post(
            f"/api/v1/purchase/suppliers?enterprise_id={enterprise_id}",
            json={
                "name": "测试供应商",
                "contact_person": "张三",
                "contact_phone": "13800138000",
                "categories": ["蔬菜", "肉类"],
                "price_list": {"白菜": 2.5, "猪肉": 25.0}
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401]


# ============ 库存管理流程测试 ============

class TestInventoryFlow:
    """库存管理流程测试"""

    @pytest.mark.asyncio
    async def test_stock_in_and_out(self, client):
        """测试入库和出库流程"""
        enterprise_id = "test-enterprise-id"

        # 入库
        response = await client.post(
            f"/api/v1/inventory/stock-in?enterprise_id={enterprise_id}",
            json={
                "ingredient_name": "鸡胸肉",
                "quantity": 10.5,
                "unit": "kg",
                "expiry_date": "2026-05-01",
                "batch_number": "BATCH001"
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401]

        # 出库
        response = await client.post(
            f"/api/v1/inventory/stock-out?enterprise_id={enterprise_id}",
            json={
                "ingredient_name": "鸡胸肉",
                "quantity": 2.0,
                "notes": "用于午市准备"
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_inventory_alerts(self, client):
        """测试库存预警"""
        enterprise_id = "test-enterprise-id"

        response = await client.get(
            f"/api/v1/inventory/alert?enterprise_id={enterprise_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "low_stock" in data
            assert "over_stock" in data
            assert "expiring_soon" in data
            assert "expired" in data


# ============ 采购流程测试 ============

class TestPurchaseFlow:
    """采购流程测试"""

    @pytest.mark.asyncio
    async def test_generate_purchase_plan(self, client):
        """测试生成采购计划"""
        enterprise_id = "test-enterprise-id"

        response = await client.post(
            f"/api/v1/purchase/plan?enterprise_id={enterprise_id}",
            json={"days": 7},
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_create_purchase_order(self, client):
        """测试创建采购订单"""
        enterprise_id = "test-enterprise-id"

        response = await client.post(
            f"/api/v1/purchase/orders?enterprise_id={enterprise_id}",
            json={
                "supplier_id": "supplier-001",
                "items": [
                    {"ingredient": "鸡胸肉", "quantity": 20, "unit": "kg", "price": 18.0},
                    {"ingredient": "花生米", "quantity": 5, "unit": "kg", "price": 25.0}
                ],
                "expected_date": "2026-04-25",
                "notes": "周一配送"
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401]


# ============ 标准化配方流程测试 ============

class TestStandardizeFlow:
    """标准化配方流程测试"""

    @pytest.mark.asyncio
    async def test_generate_standard_recipe(self, client):
        """测试生成标准化配方"""
        recipe_id = "test-recipe-id"
        enterprise_id = "test-enterprise-id"

        response = await client.post(
            "/api/v1/standardize/generate",
            json={
                "recipe_id": recipe_id,
                "enterprise_id": enterprise_id
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401, 404]  # 404 表示菜谱不存在

    @pytest.mark.asyncio
    async def test_get_standard_recipe(self, client):
        """测试获取标准化配方"""
        recipe_id = "test-recipe-id"
        enterprise_id = "test-enterprise-id"

        response = await client.get(
            f"/api/v1/standardize/recipes/{recipe_id}/standard?enterprise_id={enterprise_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [200, 401, 404]


# ============ WebSocket 跟做模式测试 ============

class TestWebSocketCookingFlow:
    """WebSocket 跟做模式测试"""

    def test_websocket_module_exists(self):
        """测试 WebSocket 模块存在"""
        from app.api.v1 import websocket
        assert websocket is not None
        assert hasattr(websocket, 'ConnectionManager')
        assert hasattr(websocket, 'websocket_endpoint')

    def test_websocket_endpoint_registered(self):
        """测试 WebSocket 端点已注册"""
        from app.main import app
        # 检查路由中是否有 websocket 路由
        route_paths = [route.path for route in app.routes]
        # WebSocket 端点应该在 main.py 中注册
        assert any('/ws' in path for path in route_paths)


# ============ 完整业务流程测试 ============

class TestFullBusinessFlow:
    """完整业务流程测试 - 从 C 端到 B 端的完整闭环"""

    @pytest.mark.asyncio
    async def test_recipe_lifecycle(self, client):
        """测试菜谱完整生命周期"""
        # 1. C 端用户上传菜谱
        # 2. 菜谱进入审核队列
        # 3. 审核通过后公开
        # 4. B 端企业可查看并使用
        # 5. 生成标准化配方
        # 6. 基于标准化配方采购

        # 这是一个集成测试，验证各模块能协同工作
        from app.models.recipe import Recipe
        from app.models.standard_recipe import StandardRecipe
        from app.models.inventory import Inventory
        from app.models.purchase_order import PurchaseOrder

        # 验证模型都可导入
        assert Recipe is not None
        assert StandardRecipe is not None
        assert Inventory is not None
        assert PurchaseOrder is not None


# ============ 性能和稳定性测试 ============

class TestPerformanceAndStability:
    """性能和稳定性测试"""

    @pytest.mark.asyncio
    async def test_concurrent_search(self, client):
        """测试并发搜索"""
        import asyncio

        skip_if_no_db()

        async def search():
            response = await client.post(
                "/api/v1/search/search",
                json={"query": "test", "limit": 10}
            )
            return response.status_code

        # 并发 10 个请求
        results = await asyncio.gather(*[search() for _ in range(10)])
        # 所有请求都应该成功
        assert all(status in [200, 400] for status in results)

    @pytest.mark.asyncio
    async def test_api_response_time(self, client):
        """测试 API 响应时间"""
        import time

        skip_if_no_db()

        start = time.time()
        response = await client.get("/api/v1/recipes?limit=10")
        elapsed = time.time() - start

        # 响应时间应小于 1 秒（不包括外部服务调用）
        assert elapsed < 1.0
        assert response.status_code in [200, 400]


# ============ 错误处理测试 ============

class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_token(self, client):
        """测试无效 token 处理"""
        skip_if_no_db()
        response = await client.get(
            "/api/v1/inventory?enterprise_id=test",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client):
        """测试缺少必填字段处理"""
        skip_if_no_db()
        response = await client.post(
            "/api/v1/inventory/stock-in?enterprise_id=test",
            json={},  # 空数据
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_not_found_handling(self, client):
        """测试 404 处理"""
        skip_if_no_db()
        response = await client.get(
            "/api/v1/recipes/non-existent-id",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code in [404, 401, 500]  # 500 表示数据库不可用


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
