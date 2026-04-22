# 修复搜索准确性问题

## 问题原因

搜索"红烧"返回"清蒸鲈鱼"的原因是：
1. Elasticsearch 没有安装 IK 中文分词器插件
2. 使用默认标准分词器，中文被拆成单字
3. Docker 容器中运行的是旧代码

## 已修复内容

1. **修改 `app/services/es_search.py`**:
   - 使用 `multi_match` 的 `phrase` 类型（精确短语匹配）
   - 设置 `slop: 5` 允许 5 个字的间隔
   - 提高 `name` 字段权重到 ^20

2. **添加测试用例**:
   - `test_search_accuracy` 验证搜索"红烧"只返回"红烧肉"

## 重新构建 Docker 容器

**必须重新构建 Docker 镜像才能生效！**

```bash
# 1. 停止现有容器
docker compose down

# 2. 重新构建 app 镜像（使用最新代码）
docker compose build --no-cache app

# 3. 启动所有服务
docker compose up -d

# 4. 查看日志确认启动成功
docker compose logs -f app
```

## 验证修复

```bash
# 测试搜索"红烧" - 应该只返回"红烧肉"
curl -X POST "http://localhost:8000/api/v1/search/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "红烧", "top_k": 10, "use_hybrid": false}'

# 期望输出:
# {
#   "query": "红烧",
#   "results": [
#     {"name": "红烧肉", ...}
#   ],
#   "total": 1,
#   "source": "es"
# }
```

## 测试用例

```bash
# 运行测试验证修复
python3 -m pytest tests/test_search.py::TestSearchAPIIntegration::test_search_accuracy -v
```

## 长期解决方案：安装 IK 分词器

为了获得更好的中文搜索效果，建议安装 IK 分词器：

```bash
# 1. 创建插件目录
mkdir -p elasticsearch/plugins

# 2. 下载 IK 分词器（对应 ES 8.11.0）
cd elasticsearch/plugins
curl -L -o ik.zip "https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.11.0/elasticsearch-analysis-ik-8.11.0.zip"
unzip ik.zip
rm ik.zip

# 3. 重启 Elasticsearch
docker compose restart elasticsearch

# 4. 验证插件安装
curl "http://localhost:9200/_nodes/plugins" | python3 -m json.tool

# 5. 重新初始化索引（使用 IK 分词器）
python3 scripts/init_es_data.py
```
