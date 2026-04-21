# CookRAG 数据模型设计文档

**版本：** v1.0  
**日期：** 2026-04-21  
**状态：** 已确认  
**作者：** System Architect

---

## 1. 概述

本文档描述 CookRAG 系统的数据模型设计，包括 PostgreSQL、Redis、Qdrant 三种数据存储的 Schema 定义。

---

## 2. 架构决策汇总

### 2.1 数据库选型

| 数据库 | 用途 | 版本 |
|--------|------|------|
| **PostgreSQL** | 业务数据（用户、菜谱、订单） | 16 + pgvector |
| **Redis** | 缓存、会话、计数 | 7.x |
| **Qdrant** | 向量检索 | 1.7+ |

**决策理由：**
1. Qdrant 向量检索性能优于 pgvector（HNSW 索引）
2. 职责分离：PG 负责事务，Qdrant 负责检索，Redis 负责缓存
3. 三个组件都可以独立扩缩容

### 2.2 数据表优先级

| 优先级 | 表名 | 说明 | Sprint |
|--------|------|------|--------|
| **P0** | `users` | C 端用户 | 1-2 |
| **P0** | `recipes` | 菜谱主表 | 1-2 |
| **P0** | `recipe_ingredients` | 菜谱 - 食材 | 1-2 |
| **P0** | `recipe_steps` | 菜谱 - 步骤 | 1-2 |
| **P1** | `favorites` | 用户收藏 | 3-4 |
| **P1** | `search_history` | 搜索历史 | 3-4 |
| **P2** | B 端表 | 企业、标准化配方、库存、采购 | 后续迭代 |

---

## 3. PostgreSQL 数据模型

### 3.1 ER 图（MVP 阶段）

```
┌─────────────────┐       ┌─────────────────┐
│     users       │       │    recipes      │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ phone           │       │ name            │
│ nickname        │       │ cuisine         │
│ avatar_url      │       │ difficulty      │
│ taste_prefs     │       │ prep_time       │
│ dietary_limits  │       │ cook_time       │
│ created_at      │       │ tags (JSONB)    │
└────────┬────────┘       │ vector_id       │
         │                │ source_type     │
         │                │ created_at      │
         │                └────────┬────────┘
         │                         │
         │         ┌───────────────┼───────────────┐
         │         │               │               │
         ▼         ▼               ▼               ▼
┌─────────────────┐       ┌─────────────────┐
│   favorites     │       │recipe_ingredients│
├─────────────────┤       ├─────────────────┤
│ user_id (PK,FK) │       │ id (PK)         │
│ recipe_id (PK,FK)│      │ recipe_id (FK)  │
│ created_at      │       │ name            │
└─────────────────┘       │ amount          │
                          │ unit            │
                          │ sequence        │
                          │ notes           │
                          └─────────────────┘

         │
         ▼
┌─────────────────┐
│  recipe_steps   │
├─────────────────┤
│ id (PK)         │
│ recipe_id (FK)  │
│ step_no         │
│ description     │
│ duration_seconds│
│ tips            │
└─────────────────┘
```

---

### 3.2 DDL - users 表

```sql
-- 用户表 (C 端)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    nickname VARCHAR(50),
    avatar_url VARCHAR(255),
    
    -- 口味偏好 (JSONB)
    -- 示例：{"spicy": 0.8, "sweet": 0.3, "sour": 0.5, "salty": 0.6}
    taste_prefs JSONB DEFAULT '{}',
    
    -- 饮食限制 (JSONB 数组)
    -- 示例：["素食", "无麸质", "无牛肉"]
    dietary_restrictions JSONB DEFAULT '[]',
    
    -- 微信相关（小程序登录用）
    wechat_openid VARCHAR(100),
    wechat_unionid VARCHAR(100),
    
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_wechat ON users(wechat_openid);
CREATE INDEX idx_users_taste_prefs ON users USING GIN(taste_prefs);

-- 自动更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

---

### 3.3 DDL - recipes 表

```sql
-- 菜谱主表
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 关联用户/企业（可选，系统菜谱为 NULL）
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    enterprise_id UUID,  -- MVP 阶段暂不实现
    
    -- 菜系分类
    cuisine VARCHAR(50),  -- 川菜/粤菜/苏菜/浙菜/闽菜/湘菜/徽菜/鲁菜
    
    -- 难度和时间
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    prep_time INTEGER CHECK (prep_time >= 0),  -- 准备时间（分钟）
    cook_time INTEGER CHECK (cook_time >= 0),  -- 烹饪时间（分钟）
    servings INTEGER DEFAULT 1 CHECK (servings > 0),  -- 几人份
    
    -- 标签 (JSONB 数组)
    -- 示例：["辣", "快手菜", "一锅出", "下饭"]
    tags JSONB DEFAULT '[]',
    
    -- 来源
    source_url VARCHAR(255),
    source_type VARCHAR(20) DEFAULT 'system',  -- system/howtocook/ugc
    
    -- 公开状态
    is_public BOOLEAN DEFAULT true,
    
    -- 审核状态（UGC 菜谱用）
    audit_status VARCHAR(20) DEFAULT 'approved',  -- pending/approved/rejected
    rejected_reason TEXT,
    
    -- 统计
    view_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    
    -- Qdrant 向量 ID（用于检索关联）
    vector_id VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 全文搜索向量（PostgreSQL 原生搜索，作为 Qdrant 的补充）
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', name), 'A') ||
        setweight(to_tsvector('simple', COALESCE(description, '')), 'B') ||
        setweight(to_tsvector('simple', array_to_string(tags, ' ')), 'C')
    ) STORED
);

-- 索引
CREATE INDEX idx_recipes_user ON recipes(user_id);
CREATE INDEX idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_tags ON recipes USING GIN(tags);
CREATE INDEX idx_recipes_search ON recipes USING GIN(search_vector);
CREATE INDEX idx_recipes_public_audit ON recipes(is_public, audit_status) 
    WHERE is_public = true;
CREATE INDEX idx_recipes_vector_id ON recipes(vector_id) WHERE vector_id IS NOT NULL;

-- 自动更新时间触发器
CREATE TRIGGER trg_recipes_updated
BEFORE UPDATE ON recipes
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

---

### 3.4 DDL - recipe_ingredients 表

```sql
-- 菜谱 - 食材表
CREATE TABLE recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,  -- 食材名称
    amount DECIMAL(10, 2),       -- 用量
    unit VARCHAR(20),            -- 单位 (g/ml/个/勺...)
    sequence INTEGER DEFAULT 0,  -- 排序序号
    notes TEXT,                  -- 备注（如"切块"、"去皮"）
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_name ON recipe_ingredients USING GIN(to_tsvector('simple', name));

-- 唯一索引（防止同一菜谱同一食材重复）
CREATE UNIQUE INDEX idx_recipe_ingredients_unique 
ON recipe_ingredients(recipe_id, name, sequence);
```

---

### 3.5 DDL - recipe_steps 表

```sql
-- 菜谱 - 步骤表
CREATE TABLE recipe_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    
    step_no INTEGER NOT NULL,        -- 步骤序号
    description TEXT NOT NULL,       -- 步骤描述
    duration_seconds INTEGER,        -- 预估耗时（秒）
    tips TEXT,                       -- 小贴士
    image_url VARCHAR(255),          -- 步骤图片 URL（MVP 后可选）
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_recipe_steps_recipe ON recipe_steps(recipe_id);
CREATE UNIQUE INDEX idx_recipe_steps_unique ON recipe_steps(recipe_id, step_no);
```

---

### 3.6 DDL - favorites 表（P1）

```sql
-- 用户收藏表
CREATE TABLE favorites (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, recipe_id)
);

-- 索引
CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_recipe ON favorites(recipe_id);
```

---

### 3.7 DDL - search_history 表（P1）

```sql
-- 搜索历史表
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(100),  -- 匿名用户会话 ID
    query TEXT NOT NULL,
    clicked_recipe_id UUID REFERENCES recipes(id),
    position_clicked INTEGER,  -- 点击位置（用于 CTR 分析）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_session ON search_history(session_id);
CREATE INDEX idx_search_history_created ON search_history(created_at);
```

---

## 4. Redis 数据结构设计

### 4.1 Key 命名规范

| 用途 | Key 格式 | 数据类型 | TTL | 示例 |
|------|---------|----------|-----|------|
| **会话缓存** | `session:{session_id}` | Hash | 1800s (30 分钟) | `session:abc123` |
| **用户画像** | `user:profile:{user_id}` | JSON | 86400s (24h) | `user:profile:uuid-123` |
| **搜索缓存** | `search:cache:{query_hash}` | List | 3600s (1h) | `search:cache:md5abc` |
| **LLM 响应缓存** | `llm:cache:{query_hash}` | String | 86400s (24h) | `llm:cache:md5xyz` |
| **限流计数器** | `ratelimit:{user_id}:{api}` | Counter | 60s | `ratelimit:uuid:search` |
| **热门菜谱** | `cache:hot:recipes:{cuisine}` | ZSet | 21600s (6h) | `cache:hot:recipes:川菜` |

---

### 4.2 数据结构详解

#### 4.2.1 会话缓存 (Hash)

```python
# Key: session:{session_id}
# TTL: 1800s

HSET session:abc123 {
    "user_id": "uuid-123",
    "last_active": "2026-04-21T10:30:00Z",
    "dialogue_history": "[{\"role\":\"user\",\"content\":\"...\"}]",  # JSON 字符串
    "last_search_results": "[\"recipe_001\",\"recipe_002\"]",  # JSON 字符串
    "context": "{\"current_recipe_id\": null}"  # JSON 字符串
}

EXPIRE session:abc123 1800
```

#### 4.2.2 用户画像 (JSON)

```python
# Key: user:profile:{user_id}
# TTL: 86400s

{
    "user_id": "uuid-123",
    "taste_prefs": {
        "spicy": 0.8,
        "sweet": 0.3,
        "sour": 0.5,
        "salty": 0.6
    },
    "dietary_restrictions": ["素食", "无麸质"],
    "favorite_cuisines": ["川菜", "粤菜"],
    "avg_cooking_time": 30,
    "skill_level": "intermediate",
    "last_updated": "2026-04-21T10:00:00Z"
}
```

#### 4.2.3 搜索缓存 (List)

```python
# Key: search:cache:{query_hash}
# TTL: 3600s

# 缓存搜索结果（菜谱 ID 列表）
LPUSH search:cache:md5abc "recipe_001" "recipe_002" "recipe_003"
EXPIRE search:cache:md5abc 3600

# 读取
LRANGE search:cache:md5abc 0 -1
```

#### 4.2.4 LLM 响应缓存 (String)

```python
# Key: llm:cache:{query_hash}
# TTL: 86400s

# 缓存 LLM 完整响应
SET llm:cache:md5xyz '{"response": "推荐您尝试宫保鸡丁..."}' EX 86400

# 读取
GET llm:cache:md5xyz
```

#### 4.2.5 限流计数器 (Counter)

```python
# Key: ratelimit:{user_id}:{api}
# TTL: 60s

# 每次请求递增
INCR ratelimit:uuid-123:search
EXPIRE ratelimit:uuid-123:search 60

# 检查是否超限
GET ratelimit:uuid-123:search  # 返回 > 10 则限流
```

---

## 5. Qdrant Collection 设计

### 5.1 Collection 配置

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
        # 菜系过滤
        "cuisine": KeywordIndexParams(is_tenant=False),
        # 难度过滤
        "difficulty": KeywordIndexParams(is_tenant=False),
        # 口味标签
        "taste": KeywordIndexParams(is_tenant=False),
        # 时间范围过滤
        "prep_time": IntegerIndexParams(),
        "cook_time": IntegerIndexParams(),
        # 多租户隔离
        "user_id": KeywordIndexParams(is_tenant=True),
        "enterprise_id": KeywordIndexParams(is_tenant=True),
        # 公开状态
        "is_public": KeywordIndexParams(),
        # 审核状态
        "audit_status": KeywordIndexParams(),
    },
    # 二进制量化，减少内存占用
    "quantization": BinaryQuantization(
        binary=BinaryQuantizationConfig(always_ram=True)
    ),
    # MVP 阶段单分片
    "shard_number": 1,
    "replication_factor": 1,
}
```

---

### 5.2 向量写入示例

```python
from qdrant_client.http.models import PointStruct

# 菜谱向量化
recipe_vectors = {
    "name_vec": embed(recipe.name),           # 菜名向量
    "desc_vec": embed(recipe.description + ingredients_text),  # 描述 + 食材
    "step_vec": embed(steps_text),            # 步骤详情
    "tag_vec": embed(" ".join(recipe.tags)),  # 标签
}

# 写入 Qdrant
client.upsert(
    collection_name="recipes",
    points=[
        PointStruct(
            id=recipe.id,  # 与 PostgreSQL 的 recipe.id 一致
            vector=recipe_vectors,
            payload={
                "recipe_id": str(recipe.id),
                "name": recipe.name,
                "cuisine": recipe.cuisine,
                "difficulty": recipe.difficulty,
                "prep_time": recipe.prep_time,
                "cook_time": recipe.cook_time,
                "taste": recipe.tags,  # 口味标签
                "user_id": str(recipe.user_id) if recipe.user_id else None,
                "is_public": recipe.is_public,
                "audit_status": recipe.audit_status,
            }
        )
    ]
)
```

---

## 6. 数据导入流水线

### 6.1 HowToCook 数据导入流程

```
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

### 6.2 增量导入策略

- **批次大小**: 每批 100 个菜谱
- **断点续传**: 记录已导入的文件列表
- **失败重试**: 单个菜谱失败不影响整批
- **进度监控**: 实时显示导入进度

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-04-21 | System | 初始版本，PostgreSQL DDL、Redis 数据结构、Qdrant Schema |

---

**文档结束**

**下一步讨论议题（可选）：**
1. API 接口设计 - RESTful 路由、请求/响应格式、错误码
2. 跟做模式 (WebSocket) - 实时步骤引导
3. 安全与限流 - JWT 认证、API 限流、内容审核
