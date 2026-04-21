# CookRAG RAG 检索架构设计文档

**版本：** v1.0  
**日期：** 2026-04-21  
**状态：** 讨论中  
**作者：** System Architect

---

## 1. 概述

本文档描述 CookRAG 系统的 RAG 检索架构设计，重点说明混合检索、结果融合和重排序的技术选型与实现方案。

---

## 2. 架构决策汇总

### 2.1 已确认的技术选型

| 决策点 | 选型方案 | 备注 |
|--------|----------|------|
| **检索引擎架构** | ES + Qdrant 双引擎 | ES 负责 BM25，Qdrant 负责向量 |
| **融合策略** | RRF（Reciprocal Rank Fusion） | k=60，无需训练 |
| **重排序部署** | 本地部署（PyTorch + MPS） | 适配 M1 Max，开发 MVP 用 |
| **备选方案** | 云端 API（阿里云百炼） | 生产阶段或 M1 性能不足时使用 |

---

## 3. 检索引擎架构

### 3.1 双引擎架构图

```
用户查询："有什么可以用鸡肉和土豆做的简单菜"
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 1: Query 理解与改写                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  - 意图识别：食材搜索                                                       │
│  - 实体抽取：{ingredients: ["鸡肉", "土豆"], difficulty: "简单"}             │
│  - Query 扩展：鸡肉 → 鸡/鸡翅/鸡腿，土豆 → 马铃薯                            │
│  - 改写后："鸡肉 土豆 简单 快手菜"                                           │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 2: 双路召回 (并行执行)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐                 │
│  │ Elasticsearch (BM25)    │  │   Qdrant (向量检索)      │                 │
│  │ - 关键词匹配            │  │   - name_vec (权重 1.5)  │                 │
│  │ - 全文检索              │  │   - desc_vec (权重 1.2)  │                 │
│  │ - TopK=50               │  │   - step_vec (权重 0.8)  │                 │
│  │                         │  │   - tag_vec (权重 1.0)   │                 │
│  │                         │  │   - TopK=50 (每路)       │                 │
│  └───────────┬─────────────┘  └───────────┬─────────────┘                 │
└──────────────┼─────────────────────────────┼───────────────────────────────┘
               │                             │
               └──────────────┬──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3: 结果融合 (RRF 倒排融合)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Reciprocal Rank Fusion:                                                    │
│  score = 1 / (k + rank)  , k=60                                             │
│  合并两路结果，去重，生成候选集 (约 80-100 条)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 4: 重排序 (Cross-Encoder) - 本地部署                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  模型：BAAI/bge-reranker-v2-m3                                              │
│  部署：PyTorch + MPS (M1 Max 本地)                                           │
│  输入：(Query, Candidate) 对                                                 │
│  输出：相关性分数 0-1                                                        │
│  附加权重：                                                                   │
│    - 用户偏好匹配度 x1.2                                                    │
│    - 菜谱热度 (收藏数) x(1 + log(fav_count)/100)                           │
│    - 时间衰减 (新鲜菜谱) x1.1                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 5: 返回 TopK                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  最终返回：Top 10 菜谱 (ID + 基础信息 + 分数)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 技术选型详细说明

### 4.1 为什么选择 ES + Qdrant 双引擎？

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| ES + Qdrant 双引擎 | 职责清晰、独立扩展、专业性强 | 运维两套系统 | ✅ 选定 |
| ES 统一检索 | 简化架构、单一运维 | ES 负载高、向量性能弱 | ❌ |
| ES + PG(pgvector) | 复用 PG、减少组件 | pgvector 性能弱于 Qdrant | ❌ |

**决策理由：**
1. Qdrant 在向量检索上的 HNSW 索引性能优于 ES 的向量能力
2. ES 的 BM25 是业界标准，与 Qdrant 形成互补
3. 两引擎独立，可单独扩缩容，故障时也可互相降级

---

### 4.2 为什么选择 RRF 融合？

| 方案 | 说明 | 决策 |
|------|------|------|
| RRF | 基于排名倒数融合，无需训练 | ✅ 选定 |
| 加权分数融合 | 需要归一化和调参 | ❌ |
| 学习排序 (LTR) | 需要标注数据 | ❌ |

**RRF 公式：**
```
score = 1 / (k + rank)
```
- `k` 为常数，通常设为 60
- `rank` 为文档在某路召回中的排名（从 1 开始）

**优点：**
1. 无需训练，开箱即用
2. 业界标准，Google、Netflix 都在用
3. 只需一个参数，易于调优

---

### 4.3 重排序模型部署方案

#### 4.3.1 本地部署（首选）

| 项目 | 配置 |
|------|------|
| **模型** | BAAI/bge-reranker-v2-m3 |
| **框架** | PyTorch 2.0+ + MPS 后端 |
| **硬件** | Apple M1 Max（32 核 GPU） |
| **预估延迟** | ~50-80ms/批次（batch=16） |
| **内存占用** | ~1.1GB |

**优势：**
- 零调用成本
- 延迟可控
- 开发调试方便
- 可利用 M1 Max 统一内存优势

**代码示例：**
```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class RerankService:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model = self.model.to("mps")  # Apple Silicon 加速
        self.model.eval()
    
    @torch.no_grad()
    def rerank(self, query: str, documents: List[str]) -> List[Tuple[int, float]]:
        """
        重排序服务
        
        Args:
            query: 用户查询
            documents: 候选文档列表
        
        Returns:
            [(doc_index, score), ...] 按分数降序
        """
        pairs = [(query, doc) for doc in documents]
        scores = []
        
        # 批处理推理
        batch_size = 16
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i+batch_size]
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to("mps")
            
            outputs = self.model(**inputs)
            batch_scores = torch.softmax(outputs.logits, dim=1)[:, 1].cpu().tolist()
            scores.extend(batch_scores)
        
        # 返回索引和分数的元组列表（降序）
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked
```

#### 4.3.2 云端 API（备选）

| 项目 | 配置 |
|------|------|
| **服务商** | 阿里云百炼 |
| **模型** | qwen3-rerank / Qwen3-Reranker-8B |
| **价格** | ¥0.72 / 百万 Token |
| **免费额度** | 100 万 Token（90 天有效期） |

**成本估算：**

| 日搜索量 | 月费用（元） |
|---------|-------------|
| 1,000 次 | ¥1.44 |
| 10,000 次 | ¥14.4 |
| 100,000 次 | ¥144 |

**降级策略：**
```python
async def generate_with_fallback(query: str, documents: List[str]) -> List[Tuple[int, float]]:
    try:
        # 尝试本地 Rerank
        return await local_rerank_service.rerank(query, documents)
    except Exception as e:
        logger.warning(f"Local rerank failed: {e}, falling back to cloud API")
        # 降级到云端 API
        return await cloud_rerank_api.rerank(query, documents)
```

---

## 5. 已确认技术细节

### 5.1 Elasticsearch 配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **版本** | 8.x | 最新稳定版 |
| **分词器** | IK Analyzer | `elasticsearch-analysis-ik` 插件 |
| **BM25 k1** | 1.2 | 默认值 |
| **BM25 b** | 0.75 | 默认值 |

### 5.2 四路向量权重（Qdrant）

| 向量 | 权重 | 说明 |
|------|------|------|
| `name_vec` | 1.5 | 菜名匹配最重要 |
| `desc_vec` | 1.2 | 描述 + 食材，次重要 |
| `tag_vec` | 1.0 | 标签/菜系/口味，基准 |
| `step_vec` | 0.8 | 步骤详情，相关性较弱 |

### 5.3 RRF 融合参数

| 参数 | 值 | 说明 |
|------|-----|------|
| **k** | 60 | 业界默认值 |
| **公式** | `score = 1 / (k + rank)` | rank 从 1 开始 |

### 5.4 缓存策略（Redis）

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **TTL** | 3600 秒（1 小时） | 平衡命中率与新鲜度 |
| **Key 格式** | `search:cache:{query_hash}` | Query+Filters 联合哈希 |
| **缓存内容** | 菜谱 ID 列表 | 最小化缓存占用 |

### 5.5 Qdrant Collection Schema

```python
{
    "vectors": {
        "name_vec": VectorParams(size=1024, distance=COSINE),
        "desc_vec": VectorParams(size=1024, distance=COSINE),
        "step_vec": VectorParams(size=1024, distance=COSINE),
        "tag_vec": VectorParams(size=1024, distance=COSINE),
    },
    "payload_schema": {
        "cuisine": KeywordIndexParams(),
        "difficulty": KeywordIndexParams(),
        "taste": KeywordIndexParams(),
        "prep_time": IntegerIndexParams(),
        "cook_time": IntegerIndexParams(),
        "user_id": KeywordIndexParams(is_tenant=True),
        "enterprise_id": KeywordIndexParams(is_tenant=True),
        "is_public": KeywordIndexParams(),
        "audit_status": KeywordIndexParams(),
    },
    "quantization": BinaryQuantization(always_ram=True),
    "shard_number": 1,  # MVP 阶段
    "replication_factor": 1,  # MVP 阶段
}
```

### 5.6 Query 改写策略

| 策略 | 状态 | 说明 |
|------|------|------|
| **同义词扩展** | ✅ 启用 | 鸡肉→鸡/鸡翅/鸡腿，土豆→马铃薯 |
| **停用词过滤** | ✅ 启用 | 过滤"的"、"有什么"等 |
| **拼写纠错** | ⏸️ 暂不启用 | 后续迭代 |
| **意图识别** | ⏸️ 暂不启用 | 后续迭代 |

### 5.7 用户画像与个性化加权策略

**决策：采用 Rerank 后加权方案（非 Fine-tuning）**

#### 加权公式

```python
final_score = rerank_score * user_pref_weight * popularity_weight

# 用户偏好匹配度（如用户喜欢辣，菜谱是辣味）
user_pref_weight = 1.0 + 0.2 * taste_match_score

# 菜谱热度
popularity_weight = 1.0 + 0.1 * log(favorite_count + 1)
```

#### 为什么不用 Fine-tuning？

| 原因 | 说明 |
|------|------|
| **数据不足** | 需要数千条标注数据（用户搜索 + 点击/收藏记录），MVP 阶段没有 |
| **成本高** | 训练需要 GPU 资源，每次微调约 ¥100-500 元 |
| **维护复杂** | 用户偏好变化需要重新训练 |
| **收益有限** | MVP 阶段用户量少，优化效果不明显 |

#### 何时考虑 Fine-tuning？

- 日搜索量 > 10,000 次
- 有足够的用户行为数据（点击、收藏、停留时长）
- 通用排序效果遇到瓶颈

### 5.8 性能基准测试方案

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **搜索 P50 延迟** | < 200ms | 50% 的请求应在此时间内完成 |
| **搜索 P99 延迟** | < 1s | 99% 的请求应在此时间内完成 |
| **Rerank 延迟** | < 100ms/批次 | 批处理 (batch=16) 平均延迟 |
| **缓存命中率** | > 40% | 热门查询的缓存命中比例 |

**测试工具：**

| 工具 | 用途 | 推荐度 |
|------|------|--------|
| **locust** | 整体压力测试，模拟并发用户 | ⭐⭐⭐⭐⭐ |
| **esrally** | Elasticsearch 基准测试 | ⭐⭐⭐⭐ |
| **qdrant-benchmark** | Qdrant 性能测试 | ⭐⭐⭐⭐ |

**执行策略：** 每次代码变更前跑基准测试，确保性能不衰退

---

## 6. Harness Agent 协作模式集成

### 6.1 RAG 检索服务作为 Sprint 分解

根据现有 Harness 架构，RAG 检索系统的实现分解为以下 Sprint：

| Sprint | 功能模块 | Generator 职责 | Evaluator 验收标准 |
|--------|----------|----------------|-------------------|
| **Sprint 1** | Elasticsearch 基础搭建 | 部署 ES，配置 IK Analyzer，导入测试数据 | ES 启动成功，中文分词测试通过 |
| **Sprint 2** | Qdrant 向量索引搭建 | 创建 Collection，配置四路向量，导入 embedding 数据 | 向量检索返回结果，延迟<100ms |
| **Sprint 3** | 双路召回实现 | 实现 ES BM25 + Qdrant 向量检索接口 | 两路召回各自返回 Top50 结果 |
| **Sprint 4** | RRF 融合实现 | 实现 RRF 算法，合并两路结果 | 融合后结果数量正确，去重完成 |
| **Sprint 5** | Rerank 服务集成 | 本地部署 BGE-Reranker，MPS 加速 | Rerank 推理成功，延迟<100ms/批次 |
| **Sprint 6** | 缓存与优化 | Redis 缓存层，性能优化 | 缓存命中率>40%，P99<1s |

### 6.2 Sprint Contract 示例（Sprint 1）

```markdown
# Sprint 1 Contract

## Feature: Elasticsearch 基础搭建

### Implementation Plan
1. Docker Compose 配置 ES 8.x
2. 安装 elasticsearch-analysis-ik 插件
3. 创建索引，配置 BM25 参数
4. 导入 100 条测试菜谱数据

### Acceptance Criteria
- [ ] ES 容器启动成功，健康检查通过
- [ ] IK Analyzer 分词测试通过（"宫保鸡丁"→["宫保","鸡丁"]）
- [ ] BM25 搜索测试通过
- [ ] 查询延迟 P99 < 50ms

### Verification Tests
- pytest test_es_health.py
- pytest test_ik_tokenizer.py
- pytest test_bm25_search.py
```

### 6.3 Agent 间通信机制

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Planner    │ --> │  Generator  │ --> │  Evaluator  │
│  (规划)      │     │  (生成)      │     │  (评估)      │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      │   spec.md         │   Code            │   qa_report.md
      │   sprint_plan.md  │   Test Results    │   Bug List      │
      ▼                   ▼                   ▼
  harness/artifacts/  app/              harness/artifacts/
```

**文件通信规范：**
- Planner 输出 → `harness/artifacts/spec.md`, `sprint_plan.md`
- Generator 输出 → 实际代码 + `harness/contracts/sprint_N.md`
- Evaluator 输出 → `harness/artifacts/qa_report.md`, `bug_list.md`

---

## 7. 数据导入流水线方案

### 7.1 HowToCook 数据导入流程

**方案选择：增量式导入（推荐）**

| 方案 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| **全量导入** | 一次性导入所有 2000+ 菜谱 | 简单直接 | 耗时长，失败成本高 |
| **增量式导入** | 分批导入，每批 100 个菜谱 | 可监控，易回滚 | 需要断点续传逻辑 |
| **流式导入** | 边抓取边导入 | 内存占用低 | 依赖外部 API 稳定性 |

### 7.2 增量式导入流水线设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HowToCook 数据导入流程                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. 抓取  │ -> │ 2. 解析  │ -> │ 3. 清洗  │ -> │ 4. 校验  │ -> │ 5. 入库  │
│ Markdown │    │ 结构化   │    │ 标准化   │    │ 质量检查 │    │ 向量化   │
└──────────┘    └──────────┘    └──────────┘    ┌──────────┘    └──────────┘
                              ┌─────────────────┘
                              │
                              ▼
                        ┌──────────┐
                        │ 6. 索引  │
                        │ Qdrant   │
                        └──────────┘
```

### 7.3 各步骤详细设计

#### 步骤 1: 抓取
```python
# 从 GitHub 仓库同步数据
# https://github.com/Anduin2017/HowToCook
# 约 2000+ 菜谱 Markdown 文件

目录结构:
HowToCook/
├── dishes/
│   ├── home/           # 家常菜
│   ├── seafood/        # 海鲜
│   ├── meat/           # 肉类
│   ├── vegetable/      # 蔬菜
│   └── ...
└── README.md
```

#### 步骤 2: 解析
```python
class RecipeMarkdownParser:
    """
    解析 HowToCook Markdown 格式
    
    输入示例:
    ## 食材
    - 鸡肉 500g
    - 土豆 2 个
    
    ## 步骤
    1. 鸡肉切块
    2. ...
    
    输出:
    {
        "ingredients": [{"name": "鸡肉", "amount": 500, "unit": "g"}],
        "steps": [{"step": 1, "description": "鸡肉切块"}]
    }
    """
```

#### 步骤 3: 清洗
```python
# 数据清洗规则
CLEANING_RULES = [
    "去除重复菜谱 (基于名称 + 食材相似度)",
    "统一计量单位 (两 -> 克，勺 -> 毫升)",
    "标准化菜系分类 (川菜/粤菜/苏菜...)",
    "提取口味标签 (辣/甜/酸/咸/鲜)",
    "估算准备时间和烹饪时间",
    "难度分级 (基于步骤数和技法)",
]
```

#### 步骤 4: 校验
```python
# 质量校验规则
VALIDATION_RULES = [
    {"field": "name", "rule": "not_empty", "action": "reject"},
    {"field": "ingredients", "rule": "min_length_1", "action": "reject"},
    {"field": "steps", "rule": "min_length_3", "action": "reject"},
    {"field": "ingredients", "rule": "valid_unit", "action": "fix_or_reject"},
]
```

#### 步骤 5-6: 入库与向量化
```python
class EmbeddingPipeline:
    """
    多向量嵌入流水线
    """
    def process(self, recipe: Recipe) -> List[VectorRecord]:
        vectors = {
            "name_vec": self.embed(recipe.name, model="bge-m3"),
            "desc_vec": self.embed(recipe.description + ingredients_text),
            "step_vec": self.embed(steps_text),
            "tag_vec": self.embed(" ".join(recipe.tags)),
        }
        return vectors
```

### 7.4 Sprint 分解建议

数据导入流水线可作为独立的 Sprint 分解：

| Sprint | 任务 | 验收标准 |
|--------|------|----------|
| **Data-1** | Markdown 解析器 | 解析成功率>95% |
| **Data-2** | 数据清洗模块 | 单位标准化完成，菜系分类准确 |
| **Data-3** | 质量校验器 | 无效菜谱拒绝率 100% |
| **Data-4** | Embedding Pipeline | 向量化成功，Qdrant 索引完成 |
| **Data-5** | 增量导入脚本 | 断点续传，失败重试 |
3. **用户画像与个性化加权策略**
4. **性能基准测试方案**

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-04-21 | System | 初始版本，记录已确认的架构决策 |
| v1.0 | 2026-04-21 | System | 补充完整技术细节：ES 配置、向量权重、RRF 参数、缓存策略、Qdrant Schema |
| v1.1 | 2026-04-21 | System | 补充个性化加权策略、Fine-tuning 决策说明、性能基准指标 |
| v1.2 | 2026-04-21 | System | 补充 Harness Agent 协作模式集成、数据导入流水线方案 |

---

**文档结束**

**下一步讨论议题（可选）：**
1. API 接口详细设计 - 请求/响应格式、错误码定义
2. RAG 生成层架构 - Prompt 组装、LLM 调用、流式输出
3. 数据模型与数据库设计 - PostgreSQL DDL、Redis 数据结构
