# CookRAG 安全与限流架构设计文档

**版本：** v1.0  
**日期：** 2026-04-21  
**状态：** 已确认  
**作者：** System Architect

---

## 1. 概述

本文档描述 CookRAG 系统的安全认证、API 限流、内容审核等安全架构设计。

---

## 2. 架构决策汇总

| 决策点 | 选型方案 | 备注 |
|--------|----------|------|
| **认证方案** | JWT + Redis 黑名单（混合模式） | 支持分布式，支持主动注销 |
| **限流策略** | 滑动窗口限流 | Redis ZSet 实现，无临界问题 |
| **内容审核** | 先发后审 | MVP 阶段简化，后续加机审 |
| **错误码体系** | HTTP 状态码 + 业务错误码（混合） | 兼顾标准与精确 |

---

## 3. 认证与授权

### 3.1 JWT Token 配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **算法** | HS256 | 对称加密，性能好 |
| **Secret Key** | 环境变量 `JWT_SECRET` | 定期轮换（建议 90 天） |
| **Access Token** | 2 小时 | 短有效期，降低泄露风险 |
| **Refresh Token** | 7 天 | Redis 存储，支持注销 |
| **签发者** | `cookrag-api` | JWT `iss` 字段 |

### 3.2 JWT Payload 结构

```python
# Access Token Payload
{
    "sub": "user-uuid-123",      # 用户 ID
    "type": "access",             # token 类型
    "role": "user",               # 角色：user/admin/enterprise_user
    "iss": "cookrag-api",         # 签发者
    "exp": 1713517200,            # 过期时间（Unix 时间戳）
    "iat": 1713513600,            # 签发时间
    "jti": "unique-token-id"      # 唯一标识，用于黑名单
}

# HTTP Header
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3.3 Token 刷新流程

```
用户登录 → 颁发 Access + Refresh Token
     │
     ▼
Access Token 使用（2 小时内）
     │
     ▼
Access Token 过期
     │
     ▼
用 Refresh Token 刷新 → 新 Access Token
     │
     ▼
Refresh Token 过期（7 天）→ 重新登录
```

### 3.4 Token 注销（黑名单）

```python
class TokenBlacklist:
    """JWT 黑名单管理（Redis）"""
    
    def __init__(self, redis_client: Redis, ttl_hours: int = 3):
        self.redis = redis_client
        self.ttl = ttl_hours * 3600  # Access Token 2h + 缓冲 1h
    
    async def add_to_blacklist(self, jti: str, exp: int):
        """将 Token 加入黑名单"""
        key = f"token:blacklist:{jti}"
        # TTL 设置为 Token 剩余有效期
        ttl = max(exp - int(time.time()), 0)
        if ttl > 0:
            await self.redis.set(key, "1", ex=ttl)
    
    async def is_blacklisted(self, jti: str) -> bool:
        """检查 Token 是否在黑名单"""
        return await self.redis.exists(f"token:blacklist:{jti}")


# 登出时加入黑名单
@app.post("/api/v1/auth/logout")
async def logout(token: dict = Depends(get_current_token)):
    jti = token["jti"]
    exp = token["exp"]
    await TokenBlacklist(redis).add_to_blacklist(jti, exp)
    return {"message": "已退出登录"}
```

### 3.5 微信小程序登录

```python
@app.post("/api/v1/auth/wechat")
async def wechat_login(code: str):
    """
    微信小程序登录
    
    流程:
    1. 用 code 换取 openid 和 session_key
    2. 检查用户是否存在，不存在则创建
    3. 颁发 JWT Token
    """
    # 1. 微信 API 换取 openid
    response = await wechat_auth.code_to_token(code)
    openid = response["openid"]
    
    # 2. 查找或创建用户
    user = await get_or_create_user_by_wechat(openid)
    
    # 3. 颁发 JWT
    access_token = create_jwt_token(user.id, "user", expires_in_hours=2)
    refresh_token = create_jwt_token(user.id, "refresh", expires_in_days=7)
    
    # 4. Refresh Token 存 Redis
    await redis.set(f"refresh:{user.id}:{refresh_token['jti']}", "1", ex=7*86400)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user.id, "nickname": user.nickname}
    }
```

---

## 4. API 限流

### 4.1 限流配置

| API 类型 | 限流维度 | 阈值 | 说明 |
|----------|----------|------|------|
| **搜索 API** | 用户维度 | 30 次/分钟 | 防止恶意刷搜索 |
| **菜谱详情** | 用户维度 | 60 次/分钟 | 较高限额，允许浏览 |
| **LLM 生成** | 用户维度 | 10 次/分钟 | 成本高，严格限制 |
| **登录/注册** | IP 维度 | 5 次/分钟 | 防止短信轰炸 |
| **全局限流** | 全 API | 10000 次/分钟 | 保护系统整体 |

### 4.2 滑动窗口实现

```python
class SlidingWindowRateLimiter:
    """
    滑动窗口限流（Redis ZSet 实现）
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        检查请求是否允许
        
        Args:
            key: 限流 Key（user_id 或 IP）
            max_requests: 窗口内最大请求数
            window_seconds: 窗口大小（秒）
        
        Returns:
            (是否允许，剩余请求数)
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Redis Key
        redis_key = f"ratelimit:sliding:{key}"
        
        # 使用 Pipeline 原子操作
        pipe = self.redis.pipeline()
        
        # 1. 删除窗口外的请求
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # 2. 添加当前请求时间戳
        pipe.zadd(redis_key, {str(uuid.uuid4()): now})
        
        # 3. 设置过期时间
        pipe.expire(redis_key, window_seconds + 1)
        
        # 4. 计算窗口内请求数
        pipe.zcard(redis_key)
        
        results = pipe.execute()
        request_count = results[-1]
        
        allowed = request_count <= max_requests
        remaining = max(0, max_requests - request_count) if allowed else 0
        
        return allowed, remaining


# FastAPI 中间件
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 获取用户标识（未登录则用 IP）
    user_id = get_user_id_from_token(request)
    if not user_id:
        user_id = request.client.host
        limit_key = f"ip:{user_id}"
    else:
        limit_key = f"user:{user_id}"
    
    # 根据 API 类型选择限流阈值
    path = request.url.path
    if path.startswith("/api/v1/search"):
        max_requests = 30
    elif path.startswith("/api/v1/llm") or path.startswith("/api/v1/generate"):
        max_requests = 10
    elif path.startswith("/api/v1/auth"):
        max_requests = 5
    else:
        max_requests = 60
    
    limiter = SlidingWindowRateLimiter(redis)
    allowed, remaining = await limiter.is_allowed(limit_key, max_requests)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "code": 3001,
                "message": "请求过于频繁，请稍后再试",
                "retry_after": 60
            }
        )
    
    # 添加限流响应头
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(max_requests)
    return response
```

### 4.3 限流监控

```python
# Prometheus 指标
from prometheus_client import Counter, Histogram

# 限流次数统计
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Number of rate limited requests',
    ['api_path', 'user_type']  # user_type: logged_in / anonymous
)

# 限流触发时记录
if not allowed:
    rate_limit_exceeded.labels(
        api_path=request.url.path,
        user_type="logged_in" if user_id else "anonymous"
    ).inc()
```

---

## 5. 内容审核

### 5.1 审核策略（MVP 阶段）

**方案：先发后审**

```
用户上传菜谱 → 直接公开 → 后台异步审核 → 违规则下架
```

**审核流程：**

```
┌─────────────────┐
│ 1. 用户上传菜谱  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 直接发布     │ ← MVP 阶段简化处理
│   audit_status  │
│   = 'approved'  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 后台待审核列表│
│   (运营处理)    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  通过      违规则下架
```

### 5.2 举报机制

```python
# 用户举报功能
@app.post("/api/v1/recipes/{recipe_id}/report")
async def report_recipe(recipe_id: str, reason: str):
    """
    用户举报菜谱
    
    Args:
        recipe_id: 菜谱 ID
        reason: 举报原因（广告/色情/暴力/其他）
    """
    await redis.hincrby("recipe:reports", recipe_id, 1)
    await redis.lpush(f"recipe:reports:{recipe_id}", json.dumps({
        "reporter": current_user.id,
        "reason": reason,
        "timestamp": time.time()
    }))
    
    # 举报数超过阈值，自动下架待审核
    report_count = await redis.hget("recipe:reports", recipe_id)
    if int(report_count) >= 5:
        await db.execute(
            "UPDATE recipes SET audit_status = 'pending' WHERE id = %s",
            (recipe_id,)
        )
    
    return {"message": "举报已提交"}
```

### 5.3 管理后台审核接口

```python
# 管理后台 - 审核菜谱
@app.post("/api/v1/admin/recipes/{recipe_id}/audit")
async def audit_recipe(recipe_id: str, action: str, reason: str = None):
    """
    管理后台审核菜谱
    
    Args:
        action: "approve" 或 "reject"
        reason: 拒绝原因（action=reject 时必填）
    """
    if action == "approve":
        await db.execute(
            "UPDATE recipes SET audit_status = 'approved' WHERE id = %s",
            (recipe_id,)
        )
    elif action == "reject":
        if not reason:
            raise HTTPException(status_code=400, detail="拒绝原因必填")
        await db.execute(
            "UPDATE recipes SET audit_status = 'rejected', rejected_reason = %s WHERE id = %s",
            (reason, recipe_id)
        )
        # 下架已公开的菜谱
        await db.execute(
            "UPDATE recipes SET is_public = false WHERE id = %s",
            (recipe_id,)
        )
    
    return {"message": f"菜谱已{action}"}
```

---

## 6. 错误码体系

### 6.1 错误码定义

```python
# 错误码规范：4 位数字
# 1xxx - 客户端错误
# 2xxx - 服务端错误
# 3xxx - 第三方服务错误
# 4xxx - 业务逻辑错误

ERROR_CODES = {
    # 通用错误
    0: "success",
    
    # 1xxx - 客户端错误
    1001: "参数错误",
    1002: "认证失败",
    1003: "权限不足",
    1004: "资源不存在",
    1005: "重复请求",
    1006: "账号已封禁",
    1007: "Token 已过期",
    1008: "Token 无效",
    1009: "手机号已注册",
    1010: "验证码错误",
    1011: "验证码已过期",
    
    # 2xxx - 服务端错误
    2001: "内部错误",
    2002: "服务不可用",
    2003: "数据库错误",
    2004: "缓存错误",
    2005: "文件上传失败",
    2006: "向量服务错误",
    
    # 3xxx - 第三方服务错误
    3001: "请求过于频繁",  # 限流
    3002: "LLM API 故障",
    3003: "短信服务故障",
    3004: "微信登录失败",
    
    # 4xxx - 业务逻辑错误
    4001: "菜谱审核未通过",
    4002: "收藏已存在",
    4003: "库存不足",
    4004: "菜谱已下架",
    4005: "食材不合法",
}

# HTTP 状态码映射
HTTP_STATUS_MAP = {
    0: 200,
    1001: 400, 1002: 401, 1003: 403, 1004: 404, 1005: 409,
    1006: 403, 1007: 401, 1008: 401, 1009: 409, 1010: 400, 1011: 400,
    2001: 500, 2002: 503, 2003: 500, 2004: 500, 2005: 500, 2006: 500,
    3001: 429, 3002: 503, 3003: 503, 3004: 400,
    4001: 403, 4002: 409, 4003: 400, 4004: 404, 4005: 400,
}
```

### 6.2 统一响应格式

```python
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

class APIResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None
    meta: dict = {
        "request_id": "",
        "timestamp": 0,
        "latency_ms": 0
    }
    
    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "APIResponse":
        return cls(
            code=0,
            message=message,
            data=data,
            meta={
                "request_id": str(uuid.uuid4()),
                "timestamp": int(time.time()),
                "latency_ms": 0  # 由中间件填充
            }
        )
    
    @classmethod
    def error(
        cls,
        code: int,
        message: str = None,
        data: Any = None
    ) -> "APIResponse":
        return cls(
            code=code,
            message=message or ERROR_CODES.get(code, "Unknown error"),
            data=data,
            meta={
                "request_id": str(uuid.uuid4()),
                "timestamp": int(time.time()),
                "latency_ms": 0
            }
        )


# 使用示例
@app.get("/api/v1/recipes/{recipe_id}")
async def get_recipe(recipe_id: str) -> APIResponse:
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        return APIResponse.error(1004, "菜谱不存在")
    return APIResponse.success({"recipe": recipe})
```

### 6.3 全局异常处理

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    
    # 已知业务异常
    if isinstance(exc, BusinessException):
        return JSONResponse(
            status_code=HTTP_STATUS_MAP.get(exc.code, 500),
            content=APIResponse.error(exc.code, exc.message).dict()
        )
    
    # 认证异常
    if isinstance(exc, AuthenticationError):
        return JSONResponse(
            status_code=401,
            content=APIResponse.error(1002, "认证失败").dict()
        )
    
    # 限流异常
    if isinstance(exc, RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content=APIResponse.error(3001, "请求过于频繁").dict()
        )
    
    # 未知异常 - 记录日志并返回 500
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=APIResponse.error(2001, "内部错误").dict()
    )


# 自定义异常基类
class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, code: int, message: str = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "Unknown error")
        super().__init__(self.message)


# 具体业务异常
class RecipeNotFoundError(BusinessException):
    def __init__(self):
        super().__init__(1004, "菜谱不存在")


class RecipeAuditFailedError(BusinessException):
    def __init__(self, reason: str):
        super().__init__(4001, f"菜谱审核未通过：{reason}")
```

---

## 7. 安全加固建议

### 7.1 SQL 注入防护

- 使用 SQLAlchemy ORM，避免原生 SQL
- 必须用原生 SQL 时，使用参数化查询

```python
# ✅ 正确 - 参数化查询
await db.execute("SELECT * FROM users WHERE phone = :phone", {"phone": phone})

# ❌ 错误 - 字符串拼接
await db.execute(f"SELECT * FROM users WHERE phone = '{phone}'")
```

### 7.2 XSS 防护

- 前端对用户输入进行 HTML 转义
- 后端返回的富文本内容使用白名单过滤

```python
from bleach import clean

# 用户输入的菜谱描述（允许有限 HTML）
allowed_tags = ['p', 'br', 'strong', 'em']
safe_description = clean(user_input, tags=allowed_tags)
```

### 7.3 密码与敏感数据

- 密码（如有）使用 bcrypt 加密
- 手机号、邮箱等敏感数据脱敏展示

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 加密
hashed = pwd_context.hash(password)

# 验证
pwd_context.verify(password, hashed)
```

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-04-21 | System | 初始版本，JWT 认证、滑动窗口限流、错误码体系 |

---

**文档结束**

**下一步讨论议题（可选）：**
1. API 接口设计 - RESTful 路由、请求/响应格式详解
2. 跟做模式 (WebSocket) - 实时步骤引导、倒计时
3. 监控与可观测性 - Prometheus 指标、Grafana 仪表盘
