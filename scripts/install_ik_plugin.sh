#!/bin/bash
# 安装 Elasticsearch IK 分词器插件

echo "=== 安装 Elasticsearch IK 分词器 ==="

# 1. 创建插件目录
mkdir -p elasticsearch/plugins

# 2. 下载 IK 分词器插件 (对应 ES 8.11.0)
echo "下载 IK 分词器插件..."
IK_VERSION="8.11.0"
PLUGIN_URL="https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v${IK_VERSION}/elasticsearch-analysis-ik-${IK_VERSION}.zip"

cd elasticsearch/plugins

# 检查是否已存在插件
if [ -d "elasticsearch-analysis-ik" ]; then
    echo "IK 分词器插件已存在，跳过下载"
else
    echo "下载 IK 分词器..."
    curl -L -o ik.zip "$PLUGIN_URL"

    if [ -f "ik.zip" ]; then
        echo "解压插件..."
        unzip -q ik.zip
        rm ik.zip
        echo "IK 分词器安装完成"
    else
        echo "下载失败，请检查网络连接"
        exit 1
    fi
fi

cd ../..

# 3. 重启 Elasticsearch
echo "重启 Elasticsearch..."
docker compose restart elasticsearch

# 等待 ES 启动
echo "等待 Elasticsearch 启动..."
sleep 10

# 4. 验证插件安装
echo "验证插件安装..."
curl -s "http://localhost:9200/_nodes/plugins" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    nodes = d['nodes'].values()
    plugins = [p['name'] for n in nodes for p in n.get('plugins', [])]
    if 'analysis-ik' in plugins:
        print('✓ IK 分词器已安装')
    else:
        print('✗ IK 分词器未安装')
        print('已安装插件:', plugins)
except Exception as e:
    print(f'验证失败：{e}')
"

# 5. 测试分词
echo ""
echo "测试 IK 分词器..."
curl -s -X POST "http://localhost:9200/_analyze" -H 'Content-Type: application/json' -d '
{
  "analyzer": "ik_max_word",
  "text": "红烧肉"
}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
tokens = [t['token'] for t in d.get('tokens', [])]
print(f'分词结果：{tokens}')
"

echo ""
echo "=== 安装完成 ==="
echo "下一步：重新初始化索引"
echo "  python3 scripts/init_es_data.py"
