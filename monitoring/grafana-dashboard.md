# Grafana 仪表盘配置

## 概述

CookRAG 系统监控仪表盘，包含核心性能指标、业务指标和系统健康状态。

## 数据源

- **Prometheus**: `http://prometheus:9090`

## 仪表盘面板

### 1. 核心性能指标 (Row 1)

#### QPS (Queries Per Second)
- **Panel Type**: Graph
- **Query**: `rate(http_requests_total{endpoint!="/metrics"}[1m])`
- **Legend**: `{{method}} {{endpoint}}`
- **Thresholds**: 
  - Warning: > 100
  - Critical: > 500

#### P99 延迟
- **Panel Type**: Graph
- **Query**: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`
- **Unit**: Seconds
- **Thresholds**:
  - Warning: > 0.5s
  - Critical: > 1s

#### P50 延迟
- **Panel Type**: Graph
- **Query**: `histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))`
- **Unit**: Seconds
- **Thresholds**:
  - Warning: > 0.1s
  - Critical: > 0.2s

### 2. 搜索性能 (Row 2)

#### 搜索延迟分布
- **Panel Type**: Heatmap
- **Query**: `rate(rag_search_duration_seconds_bucket[5m])`
- **Unit**: Seconds

#### 搜索结果数量
- **Panel Type**: Graph
- **Query**: `rate(rag_results_count_sum[5m]) / rate(rag_results_count_count[5m])`
- **Legend**: 平均结果数

#### 搜索 CTR (Click-Through Rate)
- **Panel Type**: Stat
- **Query**: `sum(rate(search_queries_total{source="user"}[1h]))`
- **Unit**: queries/hour

### 3. 缓存性能 (Row 3)

#### 缓存命中率
- **Panel Type**: Gauge
- **Query**: `cache_hit_ratio`
- **Unit**: Percent (0-100)
- **Thresholds**:
  - Good: > 40%
  - Warning: 20-40%
  - Critical: < 20%

#### 缓存命中/未命中
- **Panel Type**: Graph
- **Queries**:
  - `rate(cache_hits_total[1m])` - 命中
  - `rate(cache_misses_total[1m])` - 未命中

### 4. LLM 性能 (Row 4)

#### LLM 请求延迟
- **Panel Type**: Graph
- **Query**: `rate(llm_duration_seconds_sum[5m]) / rate(llm_duration_seconds_count[5m])`
- **Unit**: Seconds

#### LLM Token 消耗
- **Panel Type**: Graph
- **Queries**:
  - `rate(llm_tokens_total{type="prompt"}[1m])` - Prompt Tokens
  - `rate(llm_tokens_total{type="completion"}[1m])` - Completion Tokens

#### LLM 请求状态
- **Panel Type**: Pie Chart
- **Query**: `sum by (status) (rate(llm_requests_total[1h]))`

### 5. 业务指标 (Row 5)

#### 菜谱上传趋势
- **Panel Type**: Graph
- **Query**: `sum by (status) (rate(recipe_uploads_total[1h]))`
- **Legend**: `{{status}}`

#### 菜谱举报统计
- **Panel Type**: Graph
- **Query**: `sum by (auto_offline) (rate(recipe_reports_total[1h]))`
- **Legend**: `自动下架：{{auto_offline}}`

#### 热门搜索查询
- **Panel Type**: Table
- **Query**: `topk(10, sum by (query) (rate(search_queries_total[1h])))`

### 6. 系统健康 (Row 6)

#### HTTP 错误率
- **Panel Type**: Graph
- **Query**: `sum(rate(http_request_errors_total[5m])) by (error_type)`
- **Legend**: `{{error_type}}`

#### 并发请求数
- **Panel Type**: Graph
- **Query**: `sum(http_requests_in_progress)`

#### 数据库连接池
- **Panel Type**: Graph
- **Query**: (根据实际数据库连接池指标配置)

## 告警规则

### P99 延迟告警
```yaml
- alert: HighP99Latency
  expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P99 延迟过高"
    description: "P99 延迟超过 1 秒，当前值：{{ $value }}s"
```

### 缓存命中率告警
```yaml
- alert: LowCacheHitRatio
  expr: cache_hit_ratio < 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "缓存命中率过低"
    description: "缓存命中率低于 20%，当前值：{{ $value | humanizePercentage }}"
```

### LLM 错误率告警
```yaml
- alert: HighLLMErrorRate
  expr: sum(rate(llm_requests_total{status="error"}[5m])) / sum(rate(llm_requests_total[5m])) > 0.1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "LLM 错误率过高"
    description: "LLM 错误率超过 10%，当前值：{{ $value | humanizePercentage }}"
```

## 导入方法

1. 打开 Grafana，进入 Dashboards
2. 点击 "Import"
3. 上传 dashboard.json 文件或粘贴 JSON 内容
4. 选择 Prometheus 数据源
5. 点击 "Import"

## 变量配置

| 变量名 | 类型 | 查询 |
|--------|------|------|
| datasource | Prometheus | prometheus |
| interval | Interval | 1m,5m,10m,30m,1h |
| environment | Custom | dev,staging,prod |
