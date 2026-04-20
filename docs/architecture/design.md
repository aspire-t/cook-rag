# CookRAG 企业级菜谱检索增强生成系统 - 架构设计文档

**版本：** v1.0  
**日期：** 2026-04-19  
**状态：** 设计评审  
**作者：** System Architect  
**文档密级：** 内部公开

---

## 目录

1. [系统概述](#1-系统概述)
2. [系统架构](#2-系统架构)
3. [核心模块详细设计](#3-核心模块详细设计)
4. [数据模型设计](#4-数据模型设计)
5. [API 接口规范](#5-api-接口规范)
6. [RAG 引擎设计](#6-rag-引擎设计)
7. [部署架构](#7-部署架构)
8. [安全与合规](#8-安全与合规)
9. [监控与可观测性](#9-监控与可观测性)
10. [性能指标与 SLA](#10-性能指标与-sla)
11. [成本估算](#11-成本估算)
12. [实施计划](#12-实施计划)
13. [风险与应急预案](#13-风险与应急预案)
14. [附录](#14-附录)

---

## 1. 系统概述

### 1.1 产品定位

CookRAG 是一套基于检索增强生成（RAG）技术的企业级菜谱智能服务系统，同时服务 C 端消费者和 B 端餐饮企业。系统通过 AI 技术实现菜谱的智能搜索、个性化推荐、标准化生成等功能，降低家庭烹饪门槛，提升餐饮企业运营效率。

### 1.2 目标用户画像

#### C 端用户

| 用户类型 | 特征描述 | 核心需求 | 使用频率 |
|----------|----------|----------|----------|
| **烹饪新手** | 25-35 岁，城市白领，烹饪经验<1 年 | 简单易懂的菜谱、步骤引导、食材替代建议 | 每周 2-3 次 |
| **家庭主妇/夫** | 30-50 岁，有家庭，烹饪经验>3 年 | 菜谱多样性、营养搭配、快手菜 | 每日 1-2 次 |
| **健康饮食者** | 20-45 岁，健身人群，有饮食限制 | 低卡/高蛋白/无麸质等特殊饮食菜谱 | 每周 3-5 次 |
| **美食爱好者** | 25-40 岁，喜欢尝试新菜式 | 创意菜谱、地方特色、异国料理 | 每周 1-2 次 |

#### B 端用户

| 用户类型 | 特征描述 | 核心需求 | 付费意愿 |
|----------|----------|----------|----------|
| **中小型餐厅** | 3-10 张桌，标准化程度低 | 标准化配方、成本核算、采购清单 | 中（500-2000 元/月）|
| **连锁餐饮** | 10+ 门店，需要统一管理 | 中央厨房配方、多店协同、合规文档 | 高（5000+ 元/月）|
| **团餐企业** | 学校/企业食堂 | 营养配餐、大批量采购、成本控制 | 中（2000-5000 元/月）|
| **食品工厂** | 预包装菜品生产 | 工业化配方、保质期计算、标签合规 | 高（10000+ 元/月）|

### 1.3 设计原则

| 原则 | 说明 | 具体实践 |
|------|------|----------|
| **数据隔离** | C/B 端数据逻辑隔离，B 端敏感数据加密 | 独立的数据库 schema，字段级加密 |
| **渐进式扩展** | 从单机平滑过渡到分布式 | Docker Compose → K8s，无状态设计 |
| **成本优先** | MVP 阶段充分利用免费资源 | 通义千问免费额度，开源模型部署 |
| **可观测性** | 全链路监控和追踪 | OpenTelemetry + Prometheus + Grafana |
| **故障自愈** | 常见故障自动恢复 | 健康检查 + 自动重启 + 熔断降级 |

### 1.4 术语定义

| 术语 | 定义 |
|------|------|
| **RAG** | Retrieval-Augmented Generation，检索增强生成 |
| **UGC** | User Generated Content，用户生成内容 |
| **SOP** | Standard Operating Procedure，标准作业程序 |
| **QPS** | Queries Per Second，每秒查询数 |
| **P99** | 99% 的请求延迟低于此值 |
| **CTR** | Click-Through Rate，点击通过率 |

---

## 2. 系统架构

### 2.1 总体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   客户端层                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │   C 端 H5        │  │   微信小程序      │  │   B 端 Web 后台    │              │
│  │   React + H5    │  │   Taro/Uni-app   │  │   React + AntD   │              │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘              │
└───────────┼─────────────────────┼─────────────────────┼────────────────────────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
            ┌─────────────────────▼─────────────────────┐
            │            API Gateway (Kong)              │
            │   - 路由转发  - 限流熔断  - 认证鉴权        │
            │   - 请求日志  - API 版本管理                │
            └─────────────────────┬─────────────────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────────────────────┐
│                                   应用层                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    FastAPI 应用集群 (无状态)                             │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │
│  │  │ C 端 API     │ │ B 端 API     │ │ 管理 API     │ │ WebSocket   │       │ │
│  │  │ :8001       │ │ :8002       │ │ :8003       │ │ :8004       │       │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                                   服务层                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  SearchService  │  │   RAGService    │  │  RecService     │             │
│  │  - 查询解析     │  │  - Prompt 组装   │  │  - 用户画像     │             │
│  │  - 多路召回     │  │  - 上下文管理    │  │  - 推荐策略     │             │
│  │  - 重排序       │  │  - 响应生成     │  │  - A/B 测试      │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                     │                      │
│  ┌────────▼────────────────────▼─────────────────────▼────────┐            │
│  │                    Service Mesh (Istio)                     │            │
│  └────────┬────────────────────────────────────────────────────┘            │
│           │                                                                 │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │ RecipeService │ │ CostService   │ │ AuditService  │ │ UserService   │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
│                                                                             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                                   数据层                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │  PostgreSQL   │ │    Qdrant     │ │     Redis     │ │     MinIO     │   │
│  │  业务数据     │ │  向量检索     │ │  缓存/会话    │ │  对象存储     │   │
│  │  主从复制     │ │  分布式集群   │ │  Cluster 模式  │ │  多副本       │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                                   外部服务                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │  通义千问 API    │ │  BGE-M3 模型    │ │  内容安全 API    │               │
│  │  (LLM 生成)      │ │  (本地部署)      │ │  (阿里云)       │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

#### 2.2.1 后端技术栈

| 层级 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| **运行环境** | Python | 3.11+ | 性能提升、类型系统完善 |
| **Web 框架** | FastAPI | 0.109+ | 异步支持、自动 OpenAPI 文档 |
| **ORM** | SQLAlchemy | 2.0+ | 异步支持、类型安全 |
| **数据迁移** | Alembic | 1.13+ | 与 SQLAlchemy 深度集成 |
| **任务队列** | Celery | 5.3+ | 成熟稳定、支持定时任务 |
| **消息中间件** | Redis Stream | - | 轻量级、与缓存复用 |
| **API 网关** | Kong | 3.x | 插件生态丰富、性能优秀 |
| **服务网格** | Istio | 1.20+ | 流量管理、可观测性 |

#### 2.2.2 数据层技术栈

| 组件 | 技术选型 | 版本 | 配置建议 |
|------|----------|------|----------|
| **关系数据库** | PostgreSQL | 16 + pgvector | 4C8G 起步，SSD 存储 |
| **向量数据库** | Qdrant | 1.7+ | 4C8G，SSD，分布式 3 节点 |
| **缓存** | Redis | 7.x | Cluster 模式，3 主 3 从 |
| **对象存储** | MinIO | 2024.x | 4 节点纠删码 |

#### 2.2.3 前端技术栈

| 端点 | 技术栈 | 说明 |
|------|--------|------|
| **C 端 H5** | React 18 + Vite + TailwindCSS | 轻量快速、移动端优化 |
| **微信小程序** | Taro 3.x | 一套代码多端运行 |
| **B 端后台** | React + Ant Design Pro | 企业级 UI 组件库 |
| **管理后台** | React + Ant Design Pro | 与 B 端复用 |

#### 2.2.4 AI/ML 技术栈

| 组件 | 技术选型 | 部署方式 | 成本 |
|------|----------|----------|------|
| **LLM** | 通义千问 (Qwen-Plus) | API 调用 | 免费 100 万 tokens/月 |
| **嵌入模型** | BGE-M3 | 本地部署 | 0 元 (需 GPU) |
| **重排模型** | BGE-Reranker-v2-m3 | 本地部署 | 0 元 (需 GPU) |
| **推理框架** | vLLM / ONNX Runtime | - | 开源免费 |

### 2.3 基础设施

#### 2.3.1 开发环境

```
MacBook Pro / Windows 11
├── Docker Desktop
├── VS Code + Python 插件
├── Postman / Insomnia
└── DBeaver (数据库管理)
```

#### 2.3.2 测试环境

```
云服务器 (4C8G x 3)
├── Kubernetes Cluster (k3s)
├── CI/CD: GitHub Actions
├── 测试数据库：PostgreSQL (主从)
└── 测试 Qdrant: 单节点
```

#### 2.3.3 生产环境

```
云服务器 (8C16G x 5 应用节点)
├── Kubernetes Cluster (生产级)
├── PostgreSQL: 主从复制 + 读写分离
├── Qdrant: 3 节点分布式
├── Redis: 3 主 3 从 Cluster
├── MinIO: 4 节点纠删码
├── SLB: 负载均衡
└── CDN: 静态资源加速
```

---

## 3. 核心模块详细设计

### 3.1 数据接入层 (Data Ingestion Layer)

#### 3.1.1 HowToCook 数据导入流程

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

**步骤 1: 抓取**
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

**步骤 2: 解析**
```python
# Markdown 解析器
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

**步骤 3: 清洗**
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

**步骤 4: 校验**
```python
# 质量校验规则
VALIDATION_RULES = [
    {"field": "name", "rule": "not_empty", "action": "reject"},
    {"field": "ingredients", "rule": "min_length_1", "action": "reject"},
    {"field": "steps", "rule": "min_length_3", "action": "reject"},
    {"field": "ingredients", "rule": "valid_unit", "action": "fix_or_reject"},
]
```

**步骤 5-6: 入库与向量化**
```python
# 向量化流水线
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

#### 3.1.2 UGC 用户上传流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            UGC 上传审核流程                                  │
└─────────────────────────────────────────────────────────────────────────────┘

用户提交 ──► 内容安全检测 ──► AI 结构化 ──► 人工审核 (可选) ──► 发布上线
              │              │              │
              ▼              ▼              ▼
         敏感词过滤    提取食材步骤    可疑内容复审
         图片鉴黄     自动打标签      版权检查
```

### 3.2 嵌入与索引层 (Embedding & Index Layer)

#### 3.2.1 多向量索引策略

**设计原理：**
菜谱搜索是多维度的——用户可能搜索菜名（"宫保鸡丁"）、食材（"鸡肉怎么做"）、口味（"辣的菜"）、场景（"快手菜"）。单一向量难以覆盖所有维度。

**向量配置：**

| 向量名 | 输入内容 | 模型 | 维度 | 权重 |
|--------|----------|------|------|------|
| `name_vec` | 菜谱名称 | BGE-M3 | 1024 | 1.5 |
| `desc_vec` | 描述 + 食材列表 | BGE-M3 | 1024 | 1.2 |
| `step_vec` | 步骤详情 | BGE-M3 | 1024 | 0.8 |
| `tag_vec` | 标签 + 菜系 + 口味 | BGE-M3 | 1024 | 1.0 |

**Qdrant Collection Schema：**

```python
from qdrant_client.http.models import (
    VectorParams, Distance,
    PayloadSchemaType, KeywordIndexParams, IntegerIndexParams,
    BinaryQuantization, BinaryQuantizationConfig
)

collection_config = {
    "vectors": {
        "name_vec": VectorParams(size=1024, distance=Distance.COSINE),
        "desc_vec": VectorParams(size=1024, distance=Distance.COSINE),
        "step_vec": VectorParams(size=1024, distance=Distance.COSINE),
        "tag_vec": VectorParams(size=1024, distance=Distance.COSINE),
    },
    "payload_schema": {
        "cuisine": KeywordIndexParams(is_tenant=False),
        "difficulty": KeywordIndexParams(is_tenant=False),
        "taste": KeywordIndexParams(is_tenant=False),
        "prep_time": IntegerIndexParams(),
        "cook_time": IntegerIndexParams(),
        "user_id": KeywordIndexParams(is_tenant=True),  # 多租户隔离
        "enterprise_id": KeywordIndexParams(is_tenant=True),
        "is_public": KeywordIndexParams(),
        "audit_status": KeywordIndexParams(),
        "tags": KeywordIndexParams(),
    },
    "quantization": BinaryQuantization(
        binary=BinaryQuantizationConfig(always_ram=True)
    ),
}
```

#### 3.2.2 嵌入模型部署

```yaml
# docker-compose.embedding.yml
services:
  embedding-api:
    image: flagembedding/bge-m3:latest
    ports:
      - "8100:8000"
    volumes:
      - ./models:/app/models
    environment:
      - MODEL_NAME=BAAI/bge-m3
      - DEVICE=cuda
      - MAX_LENGTH=8192
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 3.3 检索服务层 (Retrieval Service Layer)

#### 3.3.1 混合检索架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              混合检索架构                                    │
└─────────────────────────────────────────────────────────────────────────────┘

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
│  Step 2: 多路召回 (并行执行)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ 路数 1: 语义检索 │  │ 路数 2: 关键词   │  │ 路数 3: 标签过滤 │            │
│  │ desc_vec        │  │ BM25            │  │ tag_vec         │            │
│  │ TopK=50         │  │ TopK=50         │  │ TopK=50         │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
└───────────┼─────────────────────┼─────────────────────┼───────────────────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3: 结果融合 (RRF 倒排融合)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Reciprocal Rank Fusion:                                                    │
│  score = 1 / (k + rank)                                                     │
│  合并三路结果，去重，生成候选集 (约 100-150 条)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 4: 重排序 (Cross-Encoder)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  模型：bge-reranker-v2-m3                                                   │
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

#### 3.3.2 检索服务类设计

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class SearchIntent(Enum):
    RECIPE_NAME = "recipe_name"      # 搜菜名
    INGREDIENT = "ingredient"        # 搜食材
    CUISINE = "cuisine"              # 搜菜系
    TASTE = "taste"                  # 搜口味
    SCENARIO = "scenario"            # 搜场景 (快手菜/宴客菜)
    UNKNOWN = "unknown"

@dataclass
class SearchFilters:
    """搜索过滤条件"""
    cuisines: Optional[List[str]] = None
    difficulties: Optional[List[str]] = None
    tastes: Optional[List[str]] = None
    max_prep_time: Optional[int] = None
    max_cook_time: Optional[int] = None
    include_ingredients: Optional[List[str]] = None
    exclude_ingredients: Optional[List[str]] = None
    user_id: Optional[str] = None
    enterprise_id: Optional[str] = None

@dataclass
class SearchResult:
    """搜索结果项"""
    recipe_id: str
    name: str
    score: float
    cuisine: str
    difficulty: str
    prep_time: int
    cook_time: int
    image_url: Optional[str]
    match_reasons: List[str]  # 匹配原因

class SearchService:
    """
    搜索服务
    
    职责:
    1. Query 理解与改写
    2. 多路召回执行
    3. 结果融合与重排序
    4. 返回结构化结果
    """
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_model: EmbeddingModel,
        rerank_model: RerankModel,
        redis_client: Redis,
    ):
        self.qdrant = qdrant_client
        self.embedder = embedding_model
        self.reranker = rerank_model
        self.cache = redis_client
    
    async def search(
        self,
        query: str,
        filters: SearchFilters,
        limit: int = 10,
        user_profile: Optional[UserProfile] = None,
    ) -> List[SearchResult]:
        """
        执行搜索
        
        流程:
        1. 检查缓存
        2. Query 理解
        3. 多路召回
        4. 融合 + 重排序
        5. 应用过滤
        6. 写入缓存
        """
        pass
    
    async def _query_understanding(self, query: str) -> QueryIntent:
        """Query 理解：意图识别 + 实体抽取"""
        pass
    
    async def _multi_channel_recall(
        self,
        intent: QueryIntent,
        filters: SearchFilters,
        top_k: int = 50,
    ) -> List[RecallResult]:
        """多路召回"""
        pass
    
    async def _fuse_results(
        self,
        results: List[List[RecallResult]],
        method: str = "rrf",
    ) -> List[RecallResult]:
        """结果融合"""
        pass
    
    async def _rerank(
        self,
        query: str,
        candidates: List[RecallResult],
        user_profile: Optional[UserProfile],
    ) -> List[SearchResult]:
        """重排序"""
        pass
```

### 3.4 RAG 生成层 (RAG Generation Layer)

#### 3.4.1 RAG  Pipeline 设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAG 生成 Pipeline                               │
└─────────────────────────────────────────────────────────────────────────────┘

用户问题："今晚想吃辣的，有什么推荐？"
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 1: 上下文检索                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  - 用户画像检索：口味偏好、饮食限制、历史收藏                                 │
│  - 菜谱检索：taste=辣，按用户偏好排序                                        │
│  - 会话历史：最近对话上下文                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 2: Prompt 组装                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ System Prompt:                                                       │   │
│  │ 你是一位专业的美食顾问，擅长根据用户偏好推荐菜谱。                     │   │
│  │ 请用友好、热情的语气，给出 3-5 个推荐，并说明理由。                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ User Context:                                                        │   │
│  │ - 口味偏好：辣度 0.8，偏好川菜、湘菜                                   │   │
│  │ - 饮食限制：无                                                        │   │
│  │ - 历史收藏：宫保鸡丁、水煮鱼、麻婆豆腐                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Retrieved Recipes:                                                   │   │
│  │ 1. 宫保鸡丁 (川菜，辣度 0.7, 30 分钟)                                   │   │
│  │ 2. 水煮肉片 (川菜，辣度 0.9, 40 分钟)                                   │   │
│  │ 3. 剁椒鱼头 (湘菜，辣度 0.8, 35 分钟)                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3: LLM 生成                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  模型：通义千问 Qwen-Plus                                                   │
│  参数：temperature=0.7, max_tokens=1024                                    │
│  流式输出：True                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 4: 后处理                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  - 结构化提取：从生成文本中提取菜谱 ID 列表                                    │
│  - 安全过滤：检查生成内容合规性                                              │
│  - 引用标注：为每个推荐添加来源链接                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.4.2 Prompt 模板库

**C 端 - 智能推荐 Prompt**

```python
C_END_RECOMMENDATION_PROMPT = """
# Role
你是一位专业的美食顾问，名叫"小厨"。你擅长根据用户的口味偏好、饮食限制和当前场景，推荐最合适的菜谱。

# Tone
- 友好、热情、专业
- 使用生活化的语言，避免过于正式
- 像朋友一样给出建议

# User Profile
## 口味偏好
{taste_preferences}
示例：辣度 0.8 (喜欢辣)，甜度 0.3 (不太喜欢甜)

## 饮食限制
{dietary_restrictions}
示例：素食主义者，不吃牛肉

## 历史收藏
{favorite_recipes}
示例：宫保鸡丁、水煮鱼、麻婆豆腐 (推测喜欢川菜)

# Retrieved Recipes
{retrieved_recipes}
格式：
- 菜谱名称 | 菜系 | 辣度 | 准备时间 | 难度
- 宫保鸡丁 | 川菜 | 0.7 | 30 分钟 | 中等

# Current Context
{user_context}
示例："今晚想做点简单的，一个人吃"

# Output Format
请按以下格式输出：

## 为你推荐

### 1. 【菜谱名称】
**推荐理由**：1-2 句话说明为什么适合用户
**关键信息**：
- 准备时间：X 分钟
- 难度：X
- 辣度：X/1.0

### 2. 【菜谱名称】
...

## 小贴士
- 1-2 条实用建议（如食材替代、做法技巧）

# Constraints
- 推荐 3-5 个菜谱
- 不要推荐用户明确不吃的食物
- 如果用户说"简单"，优先推荐准备时间<30 分钟的
"""
```

**B 端 - 标准化配方生成 Prompt**

```python
B_STANDARDIZE_PROMPT = """
# Role
你是一位餐饮行业标准化专家，拥有 10 年以上中央厨房和连锁餐饮管理经验。
你的任务是将家庭菜谱转化为可工业化生产的标准化配方。

# Input
{recipe_content}

# Output Requirements

## 1. 标准配料表
| 食材 | 规格 | 用量 (g) | 允许误差 | 备注 |
|------|------|----------|----------|------|
| 鸡胸肉 | 去骨去皮 | 500.0 | ±5g | 新鲜/冷冻均可 |
| 花生米 | 去皮熟花生 | 80.0 | ±3g | 可用腰果替代 |

## 2. 标准操作流程 (SOP)
### 步骤 1: 食材预处理 (5 分钟)
- 操作：鸡胸肉切成 2cm 见方的丁
- 关键控制点：大小均匀，确保熟度一致
- 质量检查：随机抽取 10 块，重量差异<10%

### 步骤 2: 腌制 (15 分钟)
- 操作：加入料酒 10ml、盐 3g、淀粉 5g，抓匀
- 关键控制点：腌制时间不得少于 15 分钟
- ...

## 3. 成本核算
基于当前市场价格（数据来源：{market_date}）：
| 食材 | 单价 (元/kg) | 用量 (g) | 成本 (元) |
|------|-------------|----------|----------|
| 鸡胸肉 | 18.00 | 500 | 9.00 |
| 花生米 | 25.00 | 80 | 2.00 |
| ... | ... | ... | ... |
| **合计** | - | - | **15.50** |

建议售价：45.00 元 (毛利率 65%)

## 4. 营养成分表 (每 100g 可食部)
| 项目 | 含量 | NRV% |
|------|------|------|
| 能量 | 180 kcal | 9% |
| 蛋白质 | 22.5 g | 38% |
| 脂肪 | 8.2 g | 14% |
| 碳水化合物 | 5.6 g | 2% |
| 钠 | 450 mg | 23% |

## 5. 过敏原信息
⚠️ 含有：花生
⚠️ 可能含有：大豆（如使用酱油）

## 6. 保质期与储存
- 冷藏 (0-4°C): 24 小时
- 冷冻 (-18°C): 30 天
- 解冻方式：冷藏解冻，不得室温解冻
"""
```

**B 端 - 采购规划生成 Prompt**

```python
B_PURCHASE_PLAN_PROMPT = """
# Role
你是一位资深采购经理，擅长根据餐厅经营数据制定最优采购计划。

# Context
## 当前库存
{current_inventory}

## 未来 7 天预测销量
{sales_forecast}

## 供应商信息
{suppliers}

## 菜谱配方
{recipe_formulas}

# Task
生成未来 7 天的采购计划，目标：
1. 确保食材充足，不断货
2. 最小化库存积压，减少损耗
3. 利用供应商优惠，降低成本

# Output Format

## 采购清单
| 食材 | 需求量 | 当前库存 | 需采购 | 优先供应商 | 单价 | 总价 | 建议下单日期 |
|------|--------|----------|--------|------------|------|------|-------------|
| 鸡胸肉 | 50kg | 15kg | 35kg | XX 农贸 | 18 元/kg | 630 元 | 周一/周四 |

## 成本分析
- 预计采购总额：XXXX 元
- 对比上周：+X% / -X%
- 成本优化建议：...

## 风险提示
- 需要重点关注的食材（价格波动大/供应不稳定）
- 备选供应商建议
"""
```

#### 3.4.3 RAG 上下文管理器

```python
class RAGContextManager:
    """
    RAG 上下文管理器
    
    职责:
    1. 管理多轮对话历史
    2. 动态调整检索策略
    3. 组装 Prompt 上下文
    4. 处理 Token 超限
    """
    
    MAX_CONTEXT_TOKENS = 4096
    MAX_HISTORY_TURNS = 10
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.tokenizer = get_tokenizer()
    
    async def get_context(self, session_id: str) -> RAGContext:
        """获取会话上下文"""
        pass
    
    async def add_message(self, session_id: str, role: str, content: str):
        """添加消息到历史"""
        pass
    
    def build_prompt(
        self,
        context: RAGContext,
        retrieved_docs: List[Document],
        template: str,
    ) -> str:
        """
        构建 Prompt
        
        Token 管理策略:
        1. 优先保留 System Prompt
        2. 保留最近 3 轮对话
        3. 按相关性降序保留文档
        4. 超出限制时截断
        """
        pass
    
    def _truncate_context(
        self,
        context: RAGContext,
        docs: List[Document],
        max_tokens: int,
    ) -> Tuple[RAGContext, List[Document]]:
        """截断上下文以适应 Token 限制"""
        pass
```

---

## 4. 数据模型设计

### 4.1 ER 图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CookRAG 数据模型 ER 图                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │  enterprises    │       │    suppliers    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ phone           │       │ name            │       │ name            │
│ nickname        │       │ license_number  │       │ contact_person  │
│ avatar_url      │       │ contact_person  │       │ contact_phone   │
│ taste_prefs     │       │ contact_phone   │       │ address         │
│ dietary_limits  │       │ address         │       │ categories      │
│ created_at      │       │ status          │       │ payment_terms   │
└────────┬────────┘       │ created_at      │       │ created_at      │
         │                └────────┬────────┘       └─────────────────┘
         │                         │
         │                ┌────────┴────────┐
         │                │ enterprise_users│
         │                ├─────────────────┤
         │                │ enterprise_id   │
         │                │ user_id         │
         │                │ role            │
         │                └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                         recipes                             │
         │  ├─────────────────────────────────────────────────────────────┤
         │  │ id (PK)              │ cuisine         │ source_url        │
         │  │ name                 │ difficulty      │ is_public         │
         │  │ description          │ prep_time       │ audit_status      │
         │  │ user_id (FK)         │ cook_time       │ view_count        │
         │  │ enterprise_id (FK)   │ servings        │ favorite_count    │
         │  │ tags (JSONB)         │ vector_id       │ created_at        │
         │  └─────────────────────────────────────────────────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                    recipe_ingredients                       │
         │  ├─────────────────────────────────────────────────────────────┤
         │  │ id (PK) | recipe_id (FK) | name | amount | unit | sequence  │
         │  └─────────────────────────────────────────────────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                      recipe_steps                           │
         │  ├─────────────────────────────────────────────────────────────┤
         │  │ id (PK) | recipe_id (FK) | step_no | description | image_id│
         │  └─────────────────────────────────────────────────────────────┘
         │
         │  ┌─────────────────┐       ┌─────────────────────────────────┐
         │  │    favorites    │       │        search_history           │
         │  ├─────────────────┤       ├─────────────────────────────────┤
         │  │ user_id (PK,FK) │       │ id (PK)                         │
         │  │ recipe_id (PK,FK)│      │ user_id (FK)                    │
         │  │ created_at      │       │ query                           │
         │  └─────────────────┘       │ clicked_recipe_id (FK)          │
         │                            │ created_at                      │
         │                            └─────────────────────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                   standard_recipes (B 端)                    │
         │  ├─────────────────────────────────────────────────────────────┤
         │  │ id (PK) | recipe_id (FK) | enterprise_id (FK) | version    │
         │  │ cost_per_serving | shelf_life | storage_condition          │
         │  │ sop_document_url | nutrition_json | allergen_json         │
         │  └─────────────────────────────────────────────────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                    inventory (B 端库存)                       │
         │  ├─────────────────────────────────────────────────────────────┤
         │  │ id (PK) | enterprise_id | ingredient_name | quantity       │
         │  │ unit | min_stock | max_stock | expiry_date | location      │
         │  └─────────────────────────────────────────────────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                 purchase_orders (B 端采购)                    │
         │  ├─────────────────────────────────────────────────────────────┤
         │  │ id (PK) | enterprise_id | supplier_id (FK) | status        │
         │  │ order_date | expected_date | total_amount | items (JSONB)  │
         │  └─────────────────────────────────────────────────────────────┘
         │
         └─────────────────────────────────────────────────────────────────┘
```

### 4.2 PostgreSQL DDL

```sql
-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 模糊查询

-- ===========================================
-- 用户表 (C 端)
-- ===========================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    nickname VARCHAR(50),
    avatar_url VARCHAR(255),
    taste_prefs JSONB DEFAULT '{}',  -- {"spicy": 0.8, "sweet": 0.3}
    dietary_restrictions JSONB DEFAULT '[]',  -- ["素食", "无麸质"]
    wechat_openid VARCHAR(100),  -- 微信小程序 OpenID
    wechat_unionid VARCHAR(100), -- 微信 UnionID
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_wechat ON users(wechat_openid);

-- 用户口味偏好更新触发器
CREATE OR REPLACE FUNCTION update_user_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_user_timestamp();

-- ===========================================
-- 企业表 (B 端)
-- ===========================================
CREATE TABLE enterprises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    license_number VARCHAR(50) UNIQUE,
    license_image_url VARCHAR(255),
    contact_person VARCHAR(50),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(100),
    address TEXT,
    business_type VARCHAR(50),  -- restaurant/chain/canteen/factory
    employee_count INTEGER,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/active/suspended
    approved_at TIMESTAMP,
    approved_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_enterprises_status ON enterprises(status);

-- ===========================================
-- 企业 - 用户关联表
-- ===========================================
CREATE TABLE enterprise_users (
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- admin/chef/manager/purchaser
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accepted_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (enterprise_id, user_id)
);

CREATE INDEX idx_enterprise_users_user ON enterprise_users(user_id);

-- ===========================================
-- 菜谱表
-- ===========================================
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    enterprise_id UUID REFERENCES enterprises(id) ON DELETE CASCADE,
    cuisine VARCHAR(50),
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    prep_time INTEGER CHECK (prep_time >= 0),  -- 分钟
    cook_time INTEGER CHECK (cook_time >= 0),  -- 分钟
    servings INTEGER DEFAULT 1 CHECK (servings > 0),
    tags JSONB DEFAULT '[]',
    source_url VARCHAR(255),
    source_type VARCHAR(20) DEFAULT 'system',  -- system/howtocook/ugc
    is_public BOOLEAN DEFAULT true,
    audit_status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    rejected_reason TEXT,
    view_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    vector_id VARCHAR(100),  -- Qdrant 向量 ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 全文搜索索引
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', name), 'A') ||
        setweight(to_tsvector('simple', description), 'B') ||
        setweight(to_tsvector('simple', array_to_string(tags, ' ')), 'C')
    ) STORED
);

CREATE INDEX idx_recipes_user ON recipes(user_id);
CREATE INDEX idx_recipes_enterprise ON recipes(enterprise_id);
CREATE INDEX idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_tags ON recipes USING GIN(tags);
CREATE INDEX idx_recipes_search ON recipes USING GIN(search_vector);
CREATE INDEX idx_recipes_public_audit ON recipes(is_public, audit_status) WHERE is_public = true;

-- ===========================================
-- 菜谱 - 食材表
-- ===========================================
CREATE TABLE recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2),
    unit VARCHAR(20),
    sequence INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_name ON recipe_ingredients USING GIN(to_tsvector('simple', name));

-- ===========================================
-- 菜谱 - 步骤表
-- ===========================================
CREATE TABLE recipe_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL,
    description TEXT NOT NULL,
    image_id UUID,  -- MinIO 对象 ID
    duration_seconds INTEGER,  -- 预估耗时
    tips TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_recipe_steps_recipe ON recipe_steps(recipe_id);
CREATE UNIQUE INDEX idx_recipe_steps_unique ON recipe_steps(recipe_id, step_no);

-- ===========================================
-- 收藏表
-- ===========================================
CREATE TABLE favorites (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, recipe_id)
);

CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_recipe ON favorites(recipe_id);

-- ===========================================
-- 搜索历史表
-- ===========================================
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(100),
    query TEXT NOT NULL,
    clicked_recipe_id UUID REFERENCES recipes(id),
    position_clicked INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_session ON search_history(session_id);
CREATE INDEX idx_search_history_created ON search_history(created_at);

-- ===========================================
-- 标准化配方表 (B 端)
-- ===========================================
CREATE TABLE standard_recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    cost_per_serving DECIMAL(10, 2),
    suggested_price DECIMAL(10, 2),
    gross_margin DECIMAL(5, 2),  -- 毛利率 %
    shelf_life_days INTEGER,
    storage_condition TEXT,
    sop_document_url VARCHAR(255),
    nutrition_json JSONB,
    allergen_json JSONB,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_standard_recipes_recipe ON standard_recipes(recipe_id);
CREATE INDEX idx_standard_recipes_enterprise ON standard_recipes(enterprise_id);
CREATE UNIQUE INDEX idx_standard_recipes_unique ON standard_recipes(recipe_id, enterprise_id, version);

-- ===========================================
-- 库存表 (B 端)
-- ===========================================
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    ingredient_name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    min_stock DECIMAL(10, 2),
    max_stock DECIMAL(10, 2),
    expiry_date DATE,
    location VARCHAR(100),
    batch_number VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_inventory_enterprise ON inventory(enterprise_id);
CREATE INDEX idx_inventory_ingredient ON inventory(ingredient_name);
CREATE INDEX idx_inventory_expiry ON inventory(expiry_date);

-- ===========================================
-- 采购订单表 (B 端)
-- ===========================================
CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/received/cancelled
    order_date DATE NOT NULL,
    expected_date DATE,
    received_date DATE,
    total_amount DECIMAL(10, 2),
    items JSONB NOT NULL,  -- [{"ingredient": "鸡肉", "quantity": 10, "unit": "kg", "price": 18}]
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_purchase_orders_enterprise ON purchase_orders(enterprise_id);
CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_purchase_orders_date ON purchase_orders(order_date);
```

### 4.3 Redis 数据结构设计

```python
# Redis Key 命名规范
REDIS_KEYS = {
    # 会话缓存
    "session:{session_id}": "TTL: 30min, Hash: {user_id, last_active, context}",
    
    # 用户画像缓存
    "user:profile:{user_id}": "TTL: 24h, JSON: {taste_prefs, dietary_limits, favorites}",
    
    # 搜索缓存
    "search:cache:{query_hash}": "TTL: 1h, List: [recipe_id1, recipe_id2, ...]",
    
    # 热门菜谱缓存
    "cache:hot:recipes:{cuisine}": "TTL: 6h, ZSet: {recipe_id: score}",
    
    # 限流器
    "ratelimit:{user_id}:{api}": "TTL: 1min, Counter",
    
    # 分布式锁
    "lock:{resource}:{id}": "TTL: 10s, String: random_value",
    
    # 任务队列
    "queue:embedding": "List: [task_id, ...]",
    "queue:audit": "List: [task_id, ...]",
}

# 用户画像缓存结构
USER_PROFILE_CACHE = {
    "user_id": "uuid",
    "taste_prefs": {
        "spicy": 0.8,
        "sweet": 0.3,
        "sour": 0.5,
        "salty": 0.6,
    },
    "dietary_restrictions": ["素食", "无麸质"],
    "favorite_cuisines": ["川菜", "粤菜"],
    "avg_cooking_time": 30,
    "skill_level": "intermediate",
    "last_updated": "2026-04-19T10:00:00Z",
}
```

---

## 5. API 接口规范

### 5.1 API 设计规范

#### 5.1.1 版本管理

```
/api/v1/c/*    - C 端 API
/api/v1/b/*    - B 端 API
/api/v1/admin/* - 管理后台 API
```

#### 5.1.2 响应格式

```json
{
    "code": 0,
    "message": "success",
    "data": {},
    "meta": {
        "request_id": "req_abc123",
        "timestamp": 1713513600,
        "latency_ms": 45
    }
}
```

#### 5.1.3 错误码定义

| 错误码 | 说明 | HTTP 状态 |
|--------|------|----------|
| 0 | 成功 | 200 |
| 1001 | 参数错误 | 400 |
| 1002 | 认证失败 | 401 |
| 1003 | 权限不足 | 403 |
| 1004 | 资源不存在 | 404 |
| 1005 | 重复请求 | 409 |
| 2001 | 内部错误 | 500 |
| 2002 | 服务不可用 | 503 |
| 2003 | 外部服务超时 | 504 |
| 3001 | 限流 | 429 |

### 5.2 C 端 API

#### 5.2.1 智能搜索

```http
POST /api/v1/c/search
Content-Type: application/json
Authorization: Bearer {token}

# Request
{
    "query": "有什么可以用鸡肉和土豆做的简单菜",
    "filters": {
        "cuisines": [],
        "difficulties": ["easy"],
        "max_prep_time": 30,
        "exclude_ingredients": ["辣椒", "香菜"]
    },
    "limit": 10,
    "offset": 0
}

# Response 200
{
    "code": 0,
    "message": "success",
    "data": {
        "query_intent": "ingredient_search",
        "total": 128,
        "recipes": [
            {
                "id": "recipe_001",
                "name": "土豆烧鸡块",
                "cuisine": "家常菜",
                "difficulty": "easy",
                "prep_time": 15,
                "cook_time": 25,
                "servings": 3,
                "image_url": "https://cdn.cookrag.com/recipes/001.jpg",
                "score": 0.95,
                "match_reasons": ["含鸡肉", "含土豆", "简单快手"],
                "tags": ["家常菜", "下饭", "一锅出"]
            },
            ...
        ]
    },
    "meta": {
        "request_id": "req_search_001",
        "timestamp": 1713513600,
        "latency_ms": 89
    }
}
```

#### 5.2.2 菜谱详情

```http
GET /api/v1/c/recipes/{recipe_id}
Authorization: Bearer {token}

# Response 200
{
    "code": 0,
    "data": {
        "id": "recipe_001",
        "name": "土豆烧鸡块",
        "description": "一道经典的家常菜，鸡肉鲜嫩，土豆软糯...",
        "cuisine": "家常菜",
        "difficulty": "easy",
        "prep_time": 15,
        "cook_time": 25,
        "total_time": 40,
        "servings": 3,
        "calories_per_serving": 285,
        "ingredients": [
            {"name": "鸡块", "amount": 500, "unit": "g", "notes": "切块"},
            {"name": "土豆", "amount": 300, "unit": "g", "notes": "滚刀块"},
            ...
        ],
        "steps": [
            {"step_no": 1, "description": "鸡块冷水下锅焯水", "image_url": "..."},
            ...
        ],
        "tags": ["家常菜", "下饭"],
        "nutrition": {
            "calories": 285,
            "protein": 22.5,
            "fat": 8.2,
            "carbs": 25.6
        },
        "tips": [
            "鸡块焯水时加入料酒和姜片去腥",
            "土豆可以先煎一下更香"
        ],
        "user_actions": {
            "is_favorited": false,
            "can_edit": false,
            "can_delete": false
        }
    }
}
```

#### 5.2.3 个性化推荐

```http
GET /api/v1/c/recommend
Authorization: Bearer {token}

# Query Parameters
# - scenario: dinner/snack/party/quick (可选)
# - limit: 返回数量 (可选，默认 10)

# Response 200
{
    "code": 0,
    "data": {
        "recommendation_type": "personalized",
        "reason": "基于您的口味偏好和浏览历史",
        "recipes": [...]
    }
}
```

#### 5.2.4 收藏管理

```http
# 收藏菜谱
POST /api/v1/c/favorites
Content-Type: application/json

{
    "recipe_id": "recipe_001"
}

# 取消收藏
DELETE /api/v1/c/favorites/{recipe_id}

# 收藏列表
GET /api/v1/c/favorites
Query: ?page=1&limit=20&sort=created_at desc
```

### 5.3 B 端 API

#### 5.3.1 标准化配方生成

```http
POST /api/v1/b/recipes/{recipe_id}/standardize
Authorization: Bearer {token}

# Request (可选覆盖参数)
{
    "market_date": "2026-04-19",
    "region": "beijing"
}

# Response 200
{
    "code": 0,
    "data": {
        "standard_recipe_id": "std_001",
        "version": "1.0",
        "status": "completed",
        "ingredients": [...],
        "sop": [...],
        "cost_analysis": {
            "total_cost": 15.50,
            "cost_per_serving": 5.17,
            "suggested_price": 45.00,
            "gross_margin": 65.3
        },
        "nutrition": {...},
        "allergens": ["花生", "大豆"]
    }
}

# 异步任务 (长时间运行)
# Response 202
{
    "code": 0,
    "data": {
        "task_id": "task_std_001",
        "status": "processing",
        "estimated_seconds": 30
    }
}
```

#### 5.3.2 采购规划

```http
POST /api/v1/b/purchase-plans
Authorization: Bearer {token}

{
    "start_date": "2026-04-22",
    "end_date": "2026-04-28",
    "include_suppliers": true
}

# Response
{
    "code": 0,
    "data": {
        "plan_id": "plan_001",
        "period": "2026-04-22 ~ 2026-04-28",
        "total_items": 25,
        "total_amount": 2850.00,
        "items": [
            {
                "ingredient": "鸡胸肉",
                "required_quantity": 50,
                "current_stock": 15,
                "purchase_quantity": 35,
                "unit": "kg",
                "supplier": "XX 农贸",
                "unit_price": 18.00,
                "total_price": 630.00,
                "suggested_order_date": "2026-04-21"
            },
            ...
        ],
        "suppliers_summary": [
            {"supplier_id": "sup_001", "name": "XX 农贸", "total_amount": 1200.00},
            ...
        ]
    }
}
```

### 5.4 WebSocket API (跟做模式)

```javascript
// 连接
const ws = new WebSocket('wss://api.cookrag.com/ws/v1/cooking/' + recipeId);

// 认证
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'Bearer xxx'
    }));
};

// 接收步骤更新
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch(data.type) {
        case 'step_update':
            // 更新当前步骤
            break;
        case 'timer':
            // 倒计时更新
            break;
        case 'tip':
            // 小贴士
            break;
    }
};

// 发送用户操作
ws.send(JSON.stringify({
    type: 'next_step'  // 下一步
}));

ws.send(JSON.stringify({
    type: 'repeat'  // 重复当前步骤
}));
```

---

## 6. RAG 引擎设计

### 6.1 检索策略配置

```python
# config/retrieval.py

RETRIEVAL_CONFIG = {
    "multi_channel": {
        "semantic": {
            "enabled": True,
            "vector_field": "desc_vec",
            "top_k": 50,
            "weight": 1.0,
        },
        "keyword": {
            "enabled": True,
            "method": "bm25",
            "top_k": 50,
            "weight": 0.8,
        },
        "tag_filter": {
            "enabled": True,
            "vector_field": "tag_vec",
            "top_k": 50,
            "weight": 0.6,
        },
    },
    "fusion": {
        "method": "rrf",  # Reciprocal Rank Fusion
        "k": 60,  # RRF 参数
    },
    "rerank": {
        "enabled": True,
        "model": "bge-reranker-v2-m3",
        "top_k": 10,
        "batch_size": 64,
    },
    "cache": {
        "enabled": True,
        "ttl_seconds": 3600,
        "min_query_length": 5,
    },
}
```

### 6.2 重排序模型部署

```python
# services/rerank_service.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class RerankService:
    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            torch_dtype=torch.float16,  # 半精度推理
            device_map="cuda:0",
        )
        self.model.eval()
    
    @torch.no_grad()
    def rerank(
        self,
        query: str,
        documents: List[str],
        batch_size: int = 64,
    ) -> List[Tuple[int, float]]:
        """
        重排序
        
        Returns:
            List[(doc_index, score)] 按分数降序
        """
        pairs = [(query, doc) for doc in documents]
        scores = []
        
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i+batch_size]
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self.model.device)
            
            outputs = self.model(**inputs)
            batch_scores = torch.softmax(logits, dim=1)[:, 1].cpu().tolist()
            scores.extend(batch_scores)
        
        # 返回索引和分数的元组列表
        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True
        )
        return ranked
```

### 6.3 缓存策略

```python
# services/cache_service.py

import hashlib
import json
from typing import Optional, List

class SearchCacheService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 小时
    
    def _generate_key(self, query: str, filters: SearchFilters) -> str:
        """生成缓存 Key"""
        content = json.dumps({
            "query": query,
            "filters": filters.dict(),
        }, sort_keys=True)
        query_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"search:cache:{query_hash}"
    
    async def get(self, key: str) -> Optional[List[str]]:
        """获取缓存"""
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(
        self,
        key: str,
        recipe_ids: List[str],
        ttl: Optional[int] = None,
    ):
        """设置缓存"""
        await self.redis.set(
            key,
            json.dumps(recipe_ids),
            ex=ttl or self.default_ttl,
        )
    
    async def invalidate(self, pattern: str):
        """失效缓存"""
        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)
```

---

## 7. 部署架构

### 7.1 Docker Compose (开发环境)

```yaml
# docker-compose.yml
version: '3.9'

services:
  # ===========================================
  # 应用服务
  # ===========================================
  app:
    build:
      context: ./app
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - DATABASE_URL=postgresql://cookrag:password@postgres:5432/cookrag
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379/0
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - LOG_LEVEL=DEBUG
    volumes:
      - ./app:/app
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  # 嵌入模型服务
  embedding:
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-0.3.0
    ports:
      - "8100:80"
    volumes:
      - ./models:/models
    environment:
      - MODEL_ID=BAAI/bge-m3
      - MAX_BATCH_PREFILL_LENGTH=8192
    restart: unless-stopped

  # ===========================================
  # 数据服务
  # ===========================================
  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_DB=cookrag
      - POSTGRES_USER=cookrag
      - POSTGRES_PASSWORD=password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cookrag"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:v1.7.0
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # 对象存储
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    restart: unless-stopped

  # ===========================================
  # 可观测性
  # ===========================================
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped

volumes:
  pgdata:
  qdrant_storage:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:
```

### 7.2 Kubernetes 部署 (生产环境)

```yaml
# k8s/app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cookrag-app
  namespace: cookrag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cookrag-app
  template:
    metadata:
      labels:
        app: cookrag-app
    spec:
      containers:
        - name: app
          image: registry.cookrag.com/app:v1.0.0
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cookrag-secrets
                  key: database-url
            - name: QDRANT_URL
              value: "http://qdrant-head:6333"
            - name: REDIS_URL
              value: "redis://redis-cluster:6379/0"
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: cookrag-app
  namespace: cookrag
spec:
  selector:
    app: cookrag-app
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cookrag-app-hpa
  namespace: cookrag
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cookrag-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## 8. 安全与合规

### 8.1 认证与授权

#### 8.1.1 JWT Token 结构

```python
# JWT Payload
{
    "sub": "user_id",
    "type": "access",  # access/refresh
    "role": "user",  # user/admin/enterprise_admin
    "exp": 1713517200,
    "iat": 1713513600,
    "jti": "unique_token_id"
}
```

#### 8.1.2 权限矩阵

| 角色 | C 端功能 | B 端功能 | 管理后台 |
|------|----------|----------|----------|
| **user** | 全部 | 无 | 无 |
| **enterprise_user** | 全部 | 只读 | 无 |
| **enterprise_admin** | 全部 | 全部 | 无 |
| **admin** | 只读 | 只读 | 全部 |
| **super_admin** | 全部 | 全部 | 全部 |

### 8.2 数据加密

```python
# 敏感字段加密
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()

# 数据库字段
class Enterprise(Base):
    license_number = Column(EncryptedType(String, key))  # 营业执照加密
    contact_phone = Column(EncryptedType(String, key))   # 手机号加密
```

### 8.3 内容安全

```python
# 接入阿里云内容安全 API
class ContentAuditService:
    def __init__(self, access_key: str, secret_key: str):
        self.client = Green(client_config={
            "accessKeyId": access_key,
            "accessKeySecret": secret_key,
        })
    
    async def audit_text(self, text: str) -> AuditResult:
        """文本审核"""
        task = {
            "dataId": str(uuid4()),
            "content": text,
        }
        response = self.client.do_action(
            "TextModeration",
            {"scenes": ["spam", "ad"], "tasks": [task]}
        )
        # 解析结果
        return AuditResult(
            is_safe=response["code"] == 200,
            label=response["data"]["results"][0]["label"],
        )
    
    async def audit_image(self, image_url: str) -> AuditResult:
        """图片审核"""
        pass
```

---

## 9. 监控与可观测性

### 9.1 指标体系

#### 9.1.1 业务指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| DAU | 日活跃用户 | 环比下降>20% |
| Search PV | 搜索次数 | - |
| Search CTR | 搜索点击率 | <30% |
| Favorite Rate | 收藏转化率 | <5% |
| Avg Session Duration | 平均会话时长 | <2 分钟 |

#### 9.1.2 技术指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| API P99 Latency | API P99 延迟 | >2s |
| API Error Rate | API 错误率 | >1% |
| QDRANT Search P99 | 向量检索 P99 | >500ms |
| Cache Hit Rate | 缓存命中率 | <50% |
| LLM API Error Rate | LLM 调用错误率 | >5% |

### 9.2 Grafana 仪表盘

```json
{
    "dashboard": {
        "title": "CookRAG 核心指标",
        "panels": [
            {
                "title": "QPS Trend",
                "type": "graph",
                "targets": [{"expr": "rate(http_requests_total[5m])"}]
            },
            {
                "title": "P99 Latency",
                "type": "graph",
                "targets": [{"expr": "histogram_quantile(0.99, http_request_duration_seconds_bucket)"}]
            },
            {
                "title": "Search CTR",
                "type": "stat",
                "targets": [{"expr": "sum(search_clicks) / sum(search_impressions)"}]
            }
        ]
    }
}
```

---

## 10. 性能指标与 SLA

### 10.1 性能目标

| 指标 | MVP 目标 | 生产目标 | 测量方法 |
|------|----------|----------|----------|
| 搜索延迟 P50 | <200ms | <100ms | Prometheus |
| 搜索延迟 P99 | <1s | <500ms | Prometheus |
| RAG 生成延迟 | <5s | <3s | 应用日志 |
| 系统可用性 | 99% | 99.9% | Uptime 监控 |
| 数据持久性 | 99.99% | 99.999% | 备份验证 |

### 10.2 SLA 承诺

| 服务等级 | 可用性 | 赔偿方案 |
|----------|--------|----------|
| 基础版 | 99% | 服务时长延期 |
| 企业版 | 99.9% | 服务费减免 10% |
| 旗舰版 | 99.99% | 服务费减免 25% |

---

## 11. 成本估算

### 11.1 MVP 阶段 (月)

| 项目 | 配置 | 单价 | 数量 | 小计 |
|------|------|------|------|------|
| 云服务器 | 4C8G | 200 元 | 3 | 600 元 |
| 数据库 | RDS 基础版 | 300 元 | 1 | 300 元 |
| 对象存储 | 50GB | 10 元 | 1 | 10 元 |
| LLM API | 免费额度 | 0 元 | - | 0 元 |
| 域名 SSL | - | 50 元 | 1 | 50 元 |
| **合计** | - | - | - | **960 元/月** |

### 11.2 生产阶段 (月)

| 项目 | 配置 | 单价 | 数量 | 小计 |
|------|------|------|------|------|
| 应用服务器 | 8C16G | 500 元 | 5 | 2500 元 |
| 数据库 | RDS 高可用 | 1500 元 | 1 | 1500 元 |
| Qdrant 集群 | 4C8G x3 | 500 元 | 3 | 1500 元 |
| Redis 集群 | 2C4G x6 | 200 元 | 6 | 1200 元 |
| 对象存储 | 500GB | 100 元 | 1 | 100 元 |
| SLB | - | 200 元 | 1 | 200 元 |
| CDN | 1TB | 100 元 | 1 | 100 元 |
| LLM API | 付费 | 500 元 | 1 | 500 元 |
| **合计** | - | - | - | **7600 元/月** |

---

## 12. 实施计划

### Phase 1: 基础架构 (2 周)

| 任务 | 负责人 | 开始日期 | 结束日期 | 交付物 |
|------|--------|----------|----------|--------|
| 项目脚手架 | - | D1 | D3 | 代码仓库、CI/CD |
| Docker Compose 环境 | - | D2 | D5 | 本地开发环境 |
| 数据库设计评审 | - | D3 | D5 | DDL 定稿 |
| HowToCook 导入脚本 | - | D6 | D10 | 数据导入工具 |

### Phase 2: 核心功能 (3 周)

| 任务 | 负责人 | 开始日期 | 结束日期 | 交付物 |
|------|--------|----------|----------|--------|
| 搜索服务开发 | - | D11 | D17 | SearchService |
| RAG 服务开发 | - | D11 | D20 | RAGService |
| C 端 API 开发 | - | D18 | D24 | /api/c/* 端点 |

### Phase 3-6: (略，参照原始文档)

---

## 13. 风险与应急预案

### 13.1 风险矩阵

| 风险 | 概率 | 影响 | 等级 | 应对措施 |
|------|------|------|------|----------|
| LLM 额度不足 | 高 | 高 | P0 | 本地部署降级模型 |
| 向量检索慢 | 中 | 高 | P1 | 查询缓存 + 预计算 |
| UGC 违规 | 中 | 高 | P1 | 严格审核流程 |
| 数据泄露 | 低 | 高 | P1 | 加密 + 审计 |

### 13.2 应急预案

#### 13.2.1 LLM API 故障

```python
# 降级策略
async def generate_with_fallback(prompt: str) -> str:
    try:
        # 尝试主 LLM
        return await call_qwen_api(prompt)
    except Exception:
        try:
            # 降级到备用 LLM
            return await call_backup_llm(prompt)
        except Exception:
            # 降级到规则引擎
            return await rule_based_response(prompt)
```

#### 13.2.2 数据库故障

| 场景 | 应对措施 |
|------|----------|
| 主库宕机 | 自动切换到从库 |
| 数据损坏 | 从备份恢复 (RPO<1h) |
| 连接数满 | 限流 + 排队 |

---

## 14. 附录

### 14.1 参考文档

- HowToCook: https://github.com/Anduin2017/HowToCook
- Qdrant Docs: https://qdrant.tech/documentation/
- FastAPI Docs: https://fastapi.tiangolo.com/
- LangChain Docs: https://python.langchain.com/

### 14.2 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-04-19 | System | 初始版本 |
| v1.0 | 2026-04-19 | System | 完整设计稿 |

---

**文档结束**

请审阅以上设计文档。如有疑问或需要调整的地方，请指出。
