"""
Prometheus 监控指标.

指标列表:
- http_requests_total: HTTP 请求总数 (counter)
- http_request_duration_seconds: HTTP 请求延迟 (histogram)
- http_requests_in_progress: 正在处理的请求数 (gauge)
- http_request_errors_total: HTTP 请求错误数 (counter)
- cache_hits_total: 缓存命中数 (counter)
- cache_misses_total: 缓存未命中数 (counter)
- rag_search_duration_seconds: RAG 搜索延迟 (histogram)
- llm_requests_total: LLM 请求数 (counter)
- llm_tokens_total: LLM Token 消耗数 (counter)
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY
import time
import os
from typing import Optional
from loguru import logger

# ============== 指标定义 ==============

# HTTP 请求指标
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

HTTP_REQUEST_ERRORS = Counter(
    "http_request_errors_total",
    "Total HTTP request errors",
    ["method", "endpoint", "error_type"],
)

# 缓存指标
CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

# RAG 搜索指标
RAG_SEARCH_DURATION = Histogram(
    "rag_search_duration_seconds",
    "RAG search duration in seconds",
    ["search_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

RAG_RESULTS_COUNT = Histogram(
    "rag_results_count",
    "Number of results returned by RAG search",
    ["search_type"],
    buckets=[1, 5, 10, 20, 50, 100],
)

# LLM 指标
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "status"],
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total tokens used by LLM API",
    ["model", "type"],  # type: prompt or completion
)

LLM_DURATION = Histogram(
    "llm_duration_seconds",
    "LLM API request duration in seconds",
    ["model"],
    buckets=[1, 5, 10, 30, 60, 120],
)

# 业务指标
RECIPE_UPLOADS = Counter(
    "recipe_uploads_total",
    "Total recipe uploads",
    ["status"],  # status: pending, approved, rejected
)

RECIPE_REPORTS = Counter(
    "recipe_reports_total",
    "Total recipe reports",
    ["auto_offline"],  # auto_offline: true, false
)

SEARCH_QUERIES = Counter(
    "search_queries_total",
    "Total search queries",
    ["source"],  # source: user, system
)


# ============== 指标记录函数 ==============

def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录 HTTP 请求指标."""
    HTTP_REQUESTS.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def record_http_error(method: str, endpoint: str, error_type: str):
    """记录 HTTP 错误指标."""
    HTTP_REQUEST_ERRORS.labels(method=method, endpoint=endpoint, error_type=error_type).inc()


def record_cache_hit(cache_type: str = "default"):
    """记录缓存命中."""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "default"):
    """记录缓存未命中."""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_rag_search(search_type: str, duration: float, results_count: int):
    """记录 RAG 搜索指标."""
    RAG_SEARCH_DURATION.labels(search_type=search_type).observe(duration)
    RAG_RESULTS_COUNT.labels(search_type=search_type).observe(results_count)


def record_llm_request(model: str, status: str, duration: float, prompt_tokens: int = 0, completion_tokens: int = 0):
    """记录 LLM 请求指标."""
    LLM_REQUESTS.labels(model=model, status=status).inc()
    LLM_DURATION.labels(model=model).observe(duration)
    if prompt_tokens > 0:
        LLM_TOKENS.labels(model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        LLM_TOKENS.labels(model=model, type="completion").inc(completion_tokens)


def record_recipe_upload(status: str):
    """记录菜谱上传指标."""
    RECIPE_UPLOADS.labels(status=status).inc()


def record_recipe_report(auto_offline: bool):
    """记录菜谱举报指标."""
    RECIPE_REPORTS.labels(auto_offline=str(auto_offline).lower()).inc()


def record_search_query(source: str = "user"):
    """记录搜索查询指标."""
    SEARCH_QUERIES.labels(source=source).inc()


# ============== Prometheus 指标端点 ==============

from fastapi import Request, Response
from fastapi.responses import PlainTextResponse


async def metrics_handler(request: Request) -> Response:
    """
    Prometheus 指标端点处理器.

    GET /metrics - 返回 Prometheus 格式的指标数据
    """
    try:
        metrics = generate_latest(REGISTRY)
        return PlainTextResponse(
            content=metrics.decode("utf-8"),
            media_type=CONTENT_TYPE_LATEST,
        )
    except Exception as e:
        logger.exception(f"Metrics generation failed: {e}")
        return PlainTextResponse(content="Error generating metrics", status_code=500)


# ============== Prometheus 监控中间件 ==============

async def prometheus_middleware(request: Request, call_next):
    """
    Prometheus 监控中间件.

    记录每个请求的:
    - 请求方法、路径
    - 响应状态码
    - 处理延迟
    - 并发请求数
    """
    # 跳过指标端点本身
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    endpoint = _simplify_endpoint(request.url.path)

    # 记录请求开始时间
    start_time = time.time()

    # 增加并发请求数
    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()

    try:
        response = await call_next(request)

        # 记录响应状态码
        status_code = response.status_code

        # 记录成功指标
        record_http_request(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration=time.time() - start_time,
        )

        return response

    except Exception as e:
        # 记录错误指标
        error_type = type(e).__name__
        record_http_error(method=method, endpoint=endpoint, error_type=error_type)
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        raise

    finally:
        # 减少并发请求数
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()


def _simplify_endpoint(path: str) -> str:
    """
    简化端点路径，避免高基数问题.

    例如:
    - /api/v1/recipes/123 -> /api/v1/recipes/{id}
    - /api/v1/users/456/favorites -> /api/v1/users/{id}/favorites
    """
    import re

    # 替换 UUID
    simplified = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", path, flags=re.IGNORECASE)
    # 替换纯数字 ID
    simplified = re.sub(r"/\d+", "/{id}", simplified)

    return simplified


# ============== 自定义指标收集器 ==============

class CacheHitRatioCollector:
    """
    缓存命中率收集器.

    计算并导出缓存命中率指标。
    """

    def __init__(self):
        self._hits = 0
        self._misses = 0

    def record_hit(self):
        self._hits += 1

    def record_miss(self):
        self._misses += 1

    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def collect(self):
        """Prometheus 收集器接口."""
        from prometheus_client import Metric

        metric = Metric("cache_hit_ratio", "Cache hit ratio", "gauge")
        metric.add_sample("cache_hit_ratio", {}, self.hit_ratio)
        yield metric


# 全局缓存命中率收集器
cache_collector = CacheHitRatioCollector()

# 注册自定义收集器
try:
    REGISTRY.register(cache_collector)
except Exception:
    # 可能已经注册过
    pass
