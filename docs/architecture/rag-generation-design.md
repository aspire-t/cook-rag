# CookRAG RAG 生成层架构设计文档

**版本：** v1.0  
**日期：** 2026-04-21  
**状态：** 讨论中  
**作者：** System Architect

---

## 1. 概述

本文档描述 CookRAG 系统的 RAG 生成层架构设计，涵盖 Prompt 管理、LLM 调用、上下文管理等核心模块。

---

## 2. 架构决策汇总

### 2.1 已确认的技术选型

| 决策点 | 选型方案 | 备注 |
|--------|----------|------|
| **Prompt 存储** | 独立文件（Jinja2 模板） | 便于产品修改，Git 版本管理 |
| **Token 裁剪** | 固定优先级策略 | System > 用户画像 > 对话历史 > 检索结果 |
| **变量注入** | Jinja2 模板引擎 | 支持简单逻辑，可读性好 |
| **会话管理** | Redis（带 TTL） | 支持分布式，自动过期 |
| **LLM 服务商** | 阿里云百炼（通义千问） | 免费额度 100 万 Token/90 天 |
| **降级策略** | 本地规则引擎 | API 故障时降级响应 |

---

## 3. Prompt 组装与管理

### 3.1 Prompt 模板库结构

```
prompts/
├── c_end/
│   ├── recommendation.md    # C 端智能推荐
│   ├── cooking_guide.md     # 跟做模式引导
│   └── chat.md              # 闲聊对话
├── b_end/
│   ├── standardize.md       # B 端标准化配方
│   ├── purchase_plan.md     # 采购规划
│   └── cost_analysis.md     # 成本分析
└── system/
    ├── tokenizer.md         # Token 裁剪规则
    └── fallback.md          # 降级响应模板
```

### 3.2 Prompt 模板示例（C 端智能推荐）

```jinja2
# Role
你是一位专业的美食顾问，名叫"小厨"。你擅长根据用户的口味偏好、饮食限制和当前场景，推荐最合适的菜谱。

# Tone
- 友好、热情、专业
- 使用生活化的语言，避免过于正式
- 像朋友一样给出建议

# User Profile
{% if user.taste_prefs %}
## 口味偏好
- 辣度：{{user.taste_prefs.spicy}}
- 甜度：{{user.taste_prefs.sweet}}
- 酸度：{{user.taste_prefs.sour}}
{% endif %}

{% if user.dietary_restrictions %}
## 饮食限制
{{user.dietary_restrictions | join(', ')}}
{% endif %}

{% if user.favorite_recipes %}
## 历史收藏
{{user.favorite_recipes | join(', ')}}
{% endif %}

# Retrieved Recipes
{% for recipe in recipes %}
{{loop.index}}. {{recipe.name}} | {{recipe.cuisine}} | 辣度{{recipe.spiciness}} | {{recipe.prep_time}}分钟 | {{recipe.difficulty}}
{% endfor %}

# Current Context
{{user_context}}

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
```

---

## 4. Token 裁剪策略

### 4.1 优先级顺序

| 优先级 | 内容 | 保留策略 |
|--------|------|----------|
| 1 | System Prompt | 100% 保留（~500 tokens） |
| 2 | 用户画像 | 100% 保留（~200 tokens） |
| 3 | 对话历史 | 保留最近 3 轮（~1000 tokens） |
| 4 | 检索结果 | 填满剩余 Token（约 10-15 个菜谱） |

### 4.2 Token 预算分配（以 8K 模型为例）

```
总预算：8192 tokens

预留输出空间：-1024 tokens (生成响应)
可用输入预算：7168 tokens

分配:
- System Prompt:     ~500 tokens (固定)
- 用户画像：~200 tokens (固定)
- 对话历史：~1000 tokens (3 轮)
- 检索结果：~5468 tokens (剩余空间)
```

### 4.3 裁剪实现

```python
class TokenBudget:
    """Token 预算管理"""
    
    MAX_INPUT_TOKENS = 7168
    RESERVE_OUTPUT_TOKENS = 1024
    
    # 固定预算
    SYSTEM_PROMPT_BUDGET = 500
    USER_PROFILE_BUDGET = 200
    DIALOGUE_HISTORY_BUDGET = 1000
    
    # 动态预算（剩余给检索结果）
    RETRIEVAL_BUDGET = MAX_INPUT_TOKENS - SYSTEM_PROMPT_BUDGET - USER_PROFILE_BUDGET - DIALOGUE_HISTORY_BUDGET
    # = 5468 tokens
    
    def build_context(self, system_prompt, user_profile, dialogue_history, retrieval_results):
        """
        构建上下文，自动裁剪超出部分
        """
        context_parts = []
        
        # 1. System Prompt（100% 保留）
        context_parts.append(system_prompt)
        
        # 2. 用户画像（100% 保留）
        context_parts.append(self._format_user_profile(user_profile))
        
        # 3. 对话历史（保留最近 3 轮）
        recent_history = dialogue_history[-6:]  # 3 轮 = 6 条消息
        context_parts.append(self._format_dialogue_history(recent_history))
        
        # 4. 检索结果（填满剩余预算）
        remaining_tokens = self.RETRIEVAL_BUDGET
        for recipe in retrieval_results:
            recipe_tokens = self._count_tokens(recipe)
            if recipe_tokens <= remaining_tokens:
                context_parts.append(self._format_recipe(recipe))
                remaining_tokens -= recipe_tokens
            else:
                break
        
        return "\n\n".join(context_parts)
```

---

## 5. 上下文管理器（Redis）

### 5.1 会话数据结构

```python
# Redis Key: session:{session_id}
# TTL: 1800 秒（30 分钟）

SESSION_SCHEMA = {
    "user_id": "uuid",
    "last_active": "ISO8601 timestamp",
    "dialogue_history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        # 最多保留 10 轮，FIFO 淘汰
    ],
    "last_search_results": ["recipe_001", "recipe_002", ...],  # 菜谱 ID 列表
    "context": {
        "current_recipe_id": None,  # 如果用户在跟做模式
        "preferences_snapshot": {...}  # 用户偏好快照
    }
}
```

### 5.2 会话管理器实现

```python
class SessionManager:
    """会话上下文管理器"""
    
    def __init__(self, redis_client: Redis, ttl_seconds: int = 1800):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.max_history_turns = 10  # 最多 10 轮对话
    
    async def get_session(self, session_id: str) -> dict:
        """获取会话"""
        key = f"session:{session_id}"
        data = await self.redis.get(key)
        if data:
            session = json.loads(data)
            # 刷新 TTL
            await self.redis.expire(key, self.ttl)
            return session
        return self._create_new_session(session_id)
    
    async def add_message(self, session_id: str, role: str, content: str):
        """添加消息到对话历史"""
        session = await self.get_session(session_id)
        
        session["dialogue_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持最多 10 轮（20 条消息）
        if len(session["dialogue_history"]) > self.max_history_turns * 2:
            session["dialogue_history"] = session["dialogue_history"][-self.max_history_turns * 2:]
        
        await self._save_session(session_id, session)
    
    async def set_search_results(self, session_id: str, recipe_ids: List[str]):
        """保存搜索结果为会话上下文"""
        session = await self.get_session(session_id)
        session["last_search_results"] = recipe_ids[:20]  # 最多 20 个
        await self._save_session(session_id, session)
    
    async def _save_session(self, session_id: str, session: dict):
        """保存会话到 Redis"""
        key = f"session:{session_id}"
        await self.redis.set(key, json.dumps(session, ensure_ascii=False), ex=self.ttl)
    
    def _create_new_session(self, session_id: str) -> dict:
        """创建新会话"""
        return {
            "session_id": session_id,
            "user_id": None,
            "last_active": datetime.now().isoformat(),
            "dialogue_history": [],
            "last_search_results": [],
            "context": {}
        }
```

---

## 6. LLM 调用与降级策略

### 6.1 输出方式选择

| 端点 | 输出方式 | 说明 |
|------|----------|------|
| **C 端** | 流式输出 (SSE) | 首字延迟<500ms，提升用户体验 |
| **B 端** | 一次性输出 | 生成长文档，一次性返回更方便 |

### 6.2 超时与重试策略

| 配置 | 值 | 说明 |
|------|-----|------|
| **单次请求超时** | 30 秒 | 通义千问 P99 延迟约 2-5 秒 |
| **重试次数** | 3 次 | 指数退避（1s, 2s, 4s） |
| **降级触发** | 3 次重试失败 | 进入降级流程 |

### 6.3 三级降级策略

```
┌─────────────────┐
│  Level 1:       │
│  通义千问 API    │
│  (主流程)       │
└────────┬────────┘
         │ 失败
         ▼
┌─────────────────┐
│  Level 2:       │
│  Web Search     │
│  (获取菜谱内容)  │
└────────┬────────┘
         │ 失败
         ▼
┌─────────────────┐
│  Level 3:       │
│  规则引擎       │
│  (最终兜底)     │
└─────────────────┘
```

**降级实现：**

```python
async def generate_with_fallback(query: str, context: dict) -> str:
    """
    三级降级策略
    """
    # Level 1: 通义千问 API
    try:
        return await call_qwen_api(query, context, timeout=30, retry=3)
    except Exception as e:
        logger.warning(f"LLM API failed after 3 retries: {e}")
    
    # Level 2: Web Search
    try:
        search_results = await web_search(query)
        return _generate_from_search_results(search_results)
    except Exception as e:
        logger.warning(f"Web Search failed: {e}")
    
    # Level 3: 规则引擎
    return _fallback_rule_engine(query, context)


def _fallback_rule_engine(query: str, context: dict) -> str:
    """
    规则引擎降级响应
    """
    if "推荐" in query or "有什么" in query:
        # 搜索类查询 → 返回检索结果列表
        recipes = context.get("last_search_results", [])
        if recipes:
            return f"""【服务繁忙提示】
当前咨询用户较多，智能推荐服务暂时繁忙。

根据您的搜索，我们为您找到以下菜谱：
{chr(10).join(f"{i+1}. {r['name']} ({r['cuisine']}，辣度{'★' * int(r['spiciness'])})" for i, r in enumerate(recipes[:5]))}

点击菜谱查看详情，或尝试更具体的搜索词。"""
        else:
            return "【服务繁忙提示】\n智能推荐服务暂时繁忙，请稍后再试。"
    
    elif "怎么做" in query or "步骤" in query:
        # 菜谱查询 → 返回预设提示
        return "【服务繁忙提示】\n菜谱步骤加载失败，请稍后刷新页面重试。"
    
    else:
        # 未知查询 → 返回友好提示
        return "【服务繁忙提示】\n智能助手暂时繁忙，请您稍后再试，或尝试更具体的问题。"
```

---

## 7. 成本优化

### 7.1 响应缓存（优先实施）

**缓存策略：**

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **缓存 Key** | `llm:cache:{query_hash}` | Query + 用户偏好哈希 |
| **TTL** | 86400 秒（24 小时） | 平衡缓存命中率与内容新鲜度 |
| **最小查询长度** | 10 字 | 少于 10 字不缓存（太个性化） |
| **缓存对象** | LLM 完整响应 | 包含结构化格式 |

**预期效果：**
- 热门查询（如"辣一点的菜推荐"）命中率可达 80%+
- 整体 LLM 调用量减少 **30-50%**
- 月成本从 ¥15 元降至 **¥7-10 元**（1 万日搜索量场景）

### 7.2 小模型过滤（后续迭代）

**方案：** 简单查询用小模型（Qwen-Turbo），复杂查询用大模型（Qwen-Plus）

| 查询类型 | 模型 | 成本 |
|----------|------|------|
| 简单问候/闲聊 | Qwen-Turbo | ¥0.2/百万 Token |
| 菜谱推荐/搜索 | Qwen-Plus | ¥0.8/百万 Token |
| 标准化配方生成 | Qwen-Plus | ¥0.8/百万 Token |

**实现：**
```python
def route_to_model(query: str) -> str:
    """根据查询类型路由到合适模型"""
    simple_patterns = ["你好", "你是谁", "谢谢", "再见", "在吗"]
    if any(p in query for p in simple_patterns):
        return "qwen-turbo"
    return "qwen-plus"
```

### 7.3 Token 使用监控

**监控指标：**
- 日均 Token 消耗量
- 缓存命中率
- 各功能模块 Token 占比
- 异常检测（突增告警）

---

## 8. Web Search 集成

### 8.1 搜索引擎选择

| 引擎 | 优点 | 缺点 |
|------|------|------|
| **Google Custom Search** | 结果质量高，API 稳定 | 免费额度有限（100 次/天） |
| **Bing Search API** | 中文结果好，价格低 | 需要国际信用卡 |
| **百度自定义搜索** | 中文内容最全 | API 较复杂 |

**建议：MVP 阶段用 Bing Search API**（性价比高，$15/月无限次）

### 8.2 搜索结果解析策略

```python
async def _generate_from_search_results(search_results: list) -> str:
    """
    从 Web 搜索结果生成响应
    """
    # 1. 提取菜谱网站内容（如下厨房、美食杰）
    recipe_sites = ["xiachufang.com", "meishi.cc", "douguo.com"]
    
    # 2. 解析菜谱结构（名称、食材、步骤）
    recipes = []
    for result in search_results[:5]:  # 最多 5 个结果
        if any(site in result['url'] for site in recipe_sites):
            recipe = await fetch_and_parse_recipe(result['url'])
            if recipe:
                recipes.append(recipe)
    
    # 3. 生成响应
    if recipes:
        return format_recipes_as_response(recipes)
    else:
        return _fallback_rule_engine(...)
```

---

## 9. 待确认细节

以下细节待后续讨论确认：

### 9.1 跟做模式 (WebSocket)
- [ ] WebSocket 连接管理
- [ ] 实时步骤推送
- [ ] 倒计时功能

### 9.2 安全与限流
- [ ] API 限流策略
- [ ] 防滥用机制
- [ ] 内容安全审核

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-04-21 | System | 初始版本，Prompt 组装与管理部分 |
| v1.0 | 2026-04-21 | System | 补充 LLM 调用策略、三级降级、成本优化、Web Search 集成 |

---

**文档结束**

**下一步讨论议题（可选）：**
1. 跟做模式 (WebSocket) - 实时步骤引导、倒计时
2. 安全与限流 - API 限流、防滥用、内容审核
3. 数据模型与数据库设计 - PostgreSQL DDL、Redis 数据结构
