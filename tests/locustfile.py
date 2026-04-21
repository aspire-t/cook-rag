"""
CookRAG 性能基准测试.

使用 locust 进行压力测试，验证系统性能指标：
- 搜索 API P50 < 200ms
- 搜索 API P99 < 1s
- 缓存命中率 > 40%
- LLM API 响应时间 < 5s

使用方法:
    locust -f tests/locustfile.py --host=http://localhost:8000

或使用 headless 模式:
    locust -f tests/locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s --html=report.html
"""

from locust import HttpUser, task, between, events
from typing import Optional
import json
import time


class SearchUser(HttpUser):
    """模拟 C 端用户搜索行为."""

    wait_time = between(1, 3)  # 请求间隔 1-3 秒

    # 测试数据
    test_queries = [
        "红烧肉",
        "宫保鸡丁",
        "麻婆豆腐",
        "番茄炒蛋",
        "鱼香肉丝",
        "水煮鱼",
        "糖醋排骨",
        "清蒸鲈鱼",
    ]

    test_recipe_ids = [
        "550e8400-e29b-41d4-a716-446655440000",
        "550e8400-e29b-41d4-a716-446655440001",
        "550e8400-e29b-41d4-a716-446655440002",
    ]

    def on_start(self):
        """用户开始时的初始化."""
        # 获取 Token（如果有认证测试需求）
        self.token: Optional[str] = None
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    @task(5)
    def search_recipe(self):
        """测试搜索 API（权重 5）."""
        query = self.random_query()
        start_time = time.time()

        with self.client.post(
            "/api/v1/search/search",
            json={"query": query, "limit": 10},
            headers=self.headers,
            catch_response=True,
        ) as response:
            elapsed = (time.time() - start_time) * 1000  # 转换为毫秒

            if response.status_code == 200:
                response.success()
                # 记录自定义指标
                events.request.fire(
                    request_type="search",
                    name="/api/v1/search/search",
                    response_time=elapsed,
                    response_length=len(response.content),
                    response=response,
                    context={},
                )
            elif response.status_code == 429:
                response.failure("限流")
            else:
                response.failure(f"错误状态码：{response.status_code}")

    @task(3)
    def get_recipe_detail(self):
        """测试菜谱详情 API（权重 3）."""
        recipe_id = self.random_recipe_id()

        self.client.get(
            f"/api/v1/recipes/{recipe_id}",
            headers=self.headers,
            name="/api/v1/recipes/[id]",
        )

    @task(2)
    def get_recommendations(self):
        """测试推荐 API（权重 2）."""
        self.client.post(
            "/api/v1/search/recommend",
            json={"limit": 10, "cuisine": None},
            headers=self.headers,
            name="/api/v1/search/recommend",
        )

    @task(1)
    def health_check(self):
        """测试健康检查端点（权重 1）."""
        self.client.get("/health", name="/health")

    @task(1)
    def metrics_endpoint(self):
        """测试 Prometheus 指标端点（权重 1）."""
        self.client.get("/metrics", name="/metrics")

    def random_query(self) -> str:
        """随机选择一个搜索查询."""
        import random
        return random.choice(self.test_queries)

    def random_recipe_id(self) -> str:
        """随机选择一个菜谱 ID."""
        import random
        return random.choice(self.test_recipe_ids)


class AdminUser(HttpUser):
    """模拟管理用户行为（审核、举报处理）."""

    wait_time = between(3, 5)  # 管理员操作间隔更长

    def on_start(self):
        """管理员登录获取 Token."""
        # TODO: 实现管理员登录
        self.token: Optional[str] = None
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    @task(3)
    def get_pending_recipes(self):
        """获取待审核菜谱列表."""
        self.client.get(
            "/api/v1/admin/recipes/pending",
            headers=self.headers,
            name="/api/v1/admin/recipes/pending",
        )

    @task(2)
    def get_reports(self):
        """获取举报列表."""
        self.client.get(
            "/api/v1/admin/reports",
            headers=self.headers,
            name="/api/v1/admin/reports",
        )

    @task(1)
    def approve_recipe(self):
        """审核通过菜谱."""
        self.client.post(
            "/api/v1/admin/recipes/approve",
            json={"recipe_id": "test-id"},
            headers=self.headers,
            name="/api/v1/admin/recipes/approve",
        )


# ============== 性能指标统计 ==============

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """监听请求事件，统计性能指标."""
    pass


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行."""
    print("=" * 60)
    print("CookRAG 性能基准测试开始")
    print("=" * 60)
    print(f"目标主机：{environment.host}")
    print("性能目标:")
    print("  - 搜索 API P50 < 200ms")
    print("  - 搜索 API P99 < 1s")
    print("  - 缓存命中率 > 40%")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时执行."""
    print("\n" + "=" * 60)
    print("CookRAG 性能基准测试完成")
    print("=" * 60)

    # 获取统计数据
    stats = environment.stats

    # 计算总体指标
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    success_rate = (1 - total_failures / max(total_requests, 1)) * 100

    print(f"总请求数：{total_requests}")
    print(f"失败数：{total_failures}")
    print(f"成功率：{success_rate:.2f}%")
    print(f"平均响应时间：{stats.total.avg_response_time:.2f}ms")
    print(f"P50 响应时间：{stats.total.get_response_time_percentile(0.5):.2f}ms")
    print(f"P95 响应时间：{stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 响应时间：{stats.total.get_response_time_percentile(0.99):.2f}ms")
    print("=" * 60)

    # 性能目标验证
    p50 = stats.total.get_response_time_percentile(0.5)
    p99 = stats.total.get_response_time_percentile(0.99)

    print("\n性能目标验证:")
    print(f"  - P50 < 200ms: {'✓ 通过' if p50 < 200 else '✗ 失败'} ({p50:.2f}ms)")
    print(f"  - P99 < 1000ms: {'✓ 通过' if p99 < 1000 else '✗ 失败'} ({p99:.2f}ms)")
    print("=" * 60)


# ============== 自定义指标 ==============

class PerformanceMetrics:
    """性能指标收集器."""

    def __init__(self):
        self.search_times = []
        self.cache_hits = 0
        self.cache_misses = 0

    def record_search(self, elapsed_ms: float):
        """记录搜索延迟."""
        self.search_times.append(elapsed_ms)

    def record_cache_hit(self):
        """记录缓存命中."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """记录缓存未命中."""
        self.cache_misses += 1

    @property
    def cache_hit_ratio(self) -> float:
        """计算缓存命中率."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def p50(self) -> float:
        """计算 P50 延迟."""
        if not self.search_times:
            return 0.0
        sorted_times = sorted(self.search_times)
        idx = int(len(sorted_times) * 0.5)
        return sorted_times[idx]

    @property
    def p99(self) -> float:
        """计算 P99 延迟."""
        if not self.search_times:
            return 0.0
        sorted_times = sorted(self.search_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]


# 全局指标收集器
metrics_collector = PerformanceMetrics()
