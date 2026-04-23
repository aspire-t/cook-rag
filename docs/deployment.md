# CookRAG 生产环境部署指南

## 目录

- [系统要求](#系统要求)
- [架构概述](#架构概述)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [数据导入](#数据导入)
- [服务启动](#服务启动)
- [监控与运维](#监控与运维)

---

## 系统要求

### 硬件要求
- **CPU**: 4 核以上（推荐 8 核）
- **内存**: 16GB 以上（推荐 32GB，用于 Rerank 模型和 CLIP 模型）
- **磁盘**: 50GB 以上（向量数据和图片缓存）
- **GPU**: 可选（CUDA 11+，用于加速向量化）

### 软件要求
- **操作系统**: Linux (Ubuntu 20.04+) / macOS
- **Python**: 3.11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

---

## 架构概述

```
┌─────────────────────────────────────────────────────────────┐
│                         CookRAG                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ FastAPI  │  │   LLM    │  │  Rerank  │  │   CLIP   │    │
│  │   API    │  │  Qwen    │  │  BGE-M3  │  │ Chinese  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                            │                                │
│  ┌─────────────────────────┼─────────────────────────┐      │
│  │                         │                         │      │
│  │  ┌──────────┐    ┌─────▼─────┐  ┌──────────┐     │      │
│  │  │PostgreSQL│    │   Redis   │  │   ES     │     │      │
│  │  │  数据库  │    │   缓存    │  │  BM25    │     │      │
│  │  └──────────┘    └───────────┘  └──────────┘     │      │
│  │                         │                         │      │
│  │  ┌──────────┐           │                         │      │
│  │  │  Qdrant  │◀──────────┘                         │      │
│  │  │  向量库  │                                     │      │
│  │  └──────────┘                                     │      │
│  └────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 用途 | 端口 |
|------|------|------|
| FastAPI | API 服务 | 8000 |
| PostgreSQL | 关系型数据库 | 5432 |
| Redis | 缓存/会话/限流 | 6379 |
| Elasticsearch | BM25 关键词检索 | 9200 |
| Qdrant | 向量检索（5 路向量） | 6333 |

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/aspire-t/cook-rag.git
cd cook-rag
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

### 3. 启动基础设施

```bash
docker-compose up -d postgres redis elasticsearch qdrant
```

### 4. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 5. 初始化数据库

```bash
alembic upgrade head
```

### 6. 创建 Qdrant Collection

```bash
python scripts/qdrant_collection.py --create
```

### 7. 导入数据

```bash
python scripts/import_data.py --source data/howtocook
```

### 8. 启动 API 服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 配置说明

### 环境变量 (.env)

```bash
# ==================== 数据库配置 ====================
DATABASE_URL=postgresql+asyncpg://cookrag:password@localhost:5432/cookrag

# ==================== Redis 配置 ====================
REDIS_URL=redis://localhost:6379/0

# ==================== Qdrant 配置 ====================
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=recipes

# ==================== Elasticsearch 配置 ====================
ELASTICSEARCH_URL=http://localhost:9200
ES_INDEX_NAME=recipes

# ==================== LLM 配置 ====================
QWEN_API_KEY=your_api_key_here
QWEN_MODEL=qwen-plus

# ==================== 图片存储配置 ====================
IMAGE_REPO_OWNER=aspire-t
IMAGE_REPO_NAME=cook-rag-images
IMAGE_BASE_CDN_URL=https://cdn.jsdelivr.net/gh/aspire-t/cook-rag-images@main/
GITHUB_TOKEN=your_github_token

# ==================== CLIP 模型配置 ====================
CLIP_MODEL_NAME=OFA-Sys/chinese-clip-vit-base-patch16
CLIP_DEVICE=mps  # mps/cuda/cpu

# ==================== JWT 配置 ====================
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ==================== 微信小程序配置 ====================
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret

# ==================== 服务配置 ====================
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

### 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | PostgreSQL 连接 URL | - |
| REDIS_URL | Redis 连接 URL | - |
| QDRANT_URL | Qdrant 服务地址 | http://localhost:6333 |
| QDRANT_COLLECTION | Qdrant Collection 名称 | recipes |
| ELASTICSEARCH_URL | ES 服务地址 | http://localhost:9200 |
| QWEN_API_KEY | 阿里云百炼 API Key | - |
| CLIP_DEVICE | CLIP 模型运行设备 | mps (Mac) / cuda (NVIDIA) / cpu |
| JWT_SECRET_KEY | JWT 密钥（生产环境请修改） | - |

---

## 数据导入

### 导入 HowToCook 数据

```bash
# 1. 下载 HowToCook 数据
git clone https://github.com/king-jingxiang/HowToCook.git data/howtocook

# 2. 执行导入
python scripts/import_data.py \
  --source data/howtocook \
  --batch-size 100 \
  --resume  # 支持断点续传
```

### 导入图片（可选）

```bash
python scripts/import_images.py \
  --token YOUR_GITHUB_TOKEN \
  --batch-size 50
```

### 导入进度查看

```bash
# 进度信息会实时输出到控制台
# 导入完成后会显示统计信息：
# - 处理菜谱数
# - 上传图片数
# - 数据库记录数
# - 向量化数量
```

---

## 服务启动

### 开发环境

```bash
# 启动所有服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境

```bash
# 使用 gunicorn + uvicorn workers
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/cookrag/access.log \
  --error-logfile /var/log/cookrag/error.log
```

### Docker 部署

```bash
# 构建镜像
docker build -t cookrag:latest .

# 启动容器
docker run -d \
  --name cookrag \
  -p 8000:8000 \
  --env-file .env \
  --network cookrag-network \
  cookrag:latest
```

---

## 监控与运维

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/api/v1/health

# 数据库连接检查
curl http://localhost:8000/api/v1/health/db

# Redis 连接检查
curl http://localhost:8000/api/v1/health/redis
```

### 监控指标

访问 `http://localhost:8000/metrics` 获取 Prometheus 格式指标：

- HTTP 请求总数
- 请求延迟分布（P50, P99）
- 缓存命中率
- RAG 搜索延迟
- LLM Token 消耗

### Grafana 仪表盘

导入 `monitoring/grafana-dashboard.json` 到 Grafana：

1. 登录 Grafana
2. Dashboards → Import
3. 上传 JSON 文件
4. 选择 Prometheus 数据源

### 日志管理

```bash
# 查看实时日志
tail -f /var/log/cookrag/app.log

# 搜索错误日志
grep "ERROR" /var/log/cookrag/app.log

# 日志轮转（logrotate 配置）
/var/log/cookrag/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

---

## 常见问题

### Q: CLIP 模型加载失败？
A: 检查设备配置：
- Mac: `CLIP_DEVICE=mps`
- NVIDIA: `CLIP_DEVICE=cuda`
- 无 GPU: `CLIP_DEVICE=cpu`

### Q: Qdrant Collection 创建失败？
A: 先删除旧 Collection：
```bash
python scripts/qdrant_collection.py --recreate
```

### Q: 图片导入失败？
A: 检查 GitHub Token 权限：
- 需要 `repo` 权限
- 确认图片仓库已创建

### Q: 内存不足？
A: 调整批处理大小：
```bash
python scripts/import_data.py --batch-size 50
```

---

## 附录

### API 文档
启动服务后访问：http://localhost:8000/docs

### Docker Compose 配置
参考 `docker-compose.yml`

### 性能基准
- 搜索 P50: < 200ms
- 搜索 P99: < 1s
- Rerank 延迟：< 500ms (20 items)
- CLIP 向量化：~100ms/张 (MPS)

---

最后更新：2026-04-23
