#!/bin/bash
# 初始化 Elasticsearch 索引并添加测试数据

ES_URL="http://127.0.0.1:9200"
INDEX="recipes"

echo "=== 初始化 Elasticsearch 索引 ==="

# 1. 删除已存在的索引
echo "删除旧索引..."
curl -s -X DELETE "$ES_URL/$INDEX" 2>/dev/null
echo ""

# 2. 创建索引
echo "创建索引..."
curl -s -X PUT "$ES_URL/$INDEX" -H 'Content-Type: application/json' -d '
{
  "settings": {
    "analysis": {
      "analyzer": {
        "ik_max_word": {
          "type": "custom",
          "tokenizer": "ik_max_word"
        }
      }
    },
    "similarity": {
      "bm25_custom": {
        "type": "BM25",
        "k1": 1.2,
        "b": 0.75
      }
    }
  },
  "mappings": {
    "properties": {
      "name": {
        "type": "text",
        "analyzer": "ik_max_word",
        "similarity": "bm25_custom",
        "fields": {"keyword": {"type": "keyword"}}
      },
      "description": {
        "type": "text",
        "analyzer": "ik_max_word",
        "similarity": "bm25_custom"
      },
      "ingredients": {
        "type": "text",
        "analyzer": "ik_max_word",
        "similarity": "bm25_custom"
      },
      "steps": {
        "type": "text",
        "analyzer": "ik_max_word",
        "similarity": "bm25_custom"
      },
      "cuisine": {"type": "keyword"},
      "difficulty": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "prep_time": {"type": "integer"},
      "cook_time": {"type": "integer"},
      "user_id": {"type": "keyword"},
      "is_public": {"type": "boolean"},
      "created_at": {"type": "date"}
    }
  }
}'
echo ""
echo ""

# 3. 添加测试数据
echo "添加测试菜谱..."

# 红烧肉
curl -s -X PUT "$ES_URL/$INDEX/_doc/1" -H 'Content-Type: application/json' -d '
{
  "name": "红烧肉",
  "description": "经典本帮菜，色泽红亮，肥而不腻，入口即化",
  "ingredients": "五花肉 500g, 冰糖 30g, 生抽 2 勺，老抽 1 勺，料酒 2 勺，姜片 5 片，葱段 2 根，八角 2 个，香叶 2 片",
  "steps": "1. 五花肉切块焯水 2. 炒糖色 3. 加入肉块翻炒 4. 加入调料和水 5. 小火炖煮 1 小时 6. 大火收汁",
  "cuisine": "本帮菜",
  "difficulty": "中等",
  "tags": ["肉类", "经典", "家常菜"],
  "prep_time": 20,
  "cook_time": 60,
  "user_id": "system",
  "is_public": true,
  "created_at": "2026-04-20"
}'
echo " - 红烧肉"

# 麻婆豆腐
curl -s -X PUT "$ES_URL/$INDEX/_doc/2" -H 'Content-Type: application/json' -d '
{
  "name": "麻婆豆腐",
  "description": "四川传统名菜，麻辣鲜香，豆腐嫩滑",
  "ingredients": "嫩豆腐 400g, 牛肉末 100g, 豆瓣酱 2 勺，花椒粉 1 勺，辣椒粉 1 勺，姜末 1 勺，蒜末 1 勺，葱花适量",
  "steps": "1. 豆腐切块焯水 2. 炒香牛肉末 3. 加入豆瓣酱炒出红油 4. 加入豆腐和调料 5. 小火焖煮 5 分钟 6. 撒上花椒粉和葱花",
  "cuisine": "川菜",
  "difficulty": "简单",
  "tags": ["豆制品", "麻辣", "下饭菜"],
  "prep_time": 10,
  "cook_time": 15,
  "user_id": "system",
  "is_public": true,
  "created_at": "2026-04-20"
}'
echo " - 麻婆豆腐"

# 番茄炒蛋
curl -s -X PUT "$ES_URL/$INDEX/_doc/3" -H 'Content-Type: application/json' -d '
{
  "name": "番茄炒蛋",
  "description": "经典家常菜，酸甜可口，营养丰富",
  "ingredients": "鸡蛋 4 个，番茄 3 个，白糖 1 勺，盐适量，葱花适量",
  "steps": "1. 鸡蛋打散炒熟 2. 番茄切块 3. 炒番茄出汁 4. 加入鸡蛋翻炒 5. 调味撒葱花",
  "cuisine": "家常菜",
  "difficulty": "简单",
  "tags": ["快手菜", "素食", "营养"],
  "prep_time": 5,
  "cook_time": 10,
  "user_id": "system",
  "is_public": true,
  "created_at": "2026-04-20"
}'
echo " - 番茄炒蛋"

# 宫保鸡丁
curl -s -X PUT "$ES_URL/$INDEX/_doc/4" -H 'Content-Type: application/json' -d '
{
  "name": "宫保鸡丁",
  "description": "经典川菜，鸡肉鲜嫩，花生酥脆，麻辣酸甜",
  "ingredients": "鸡胸肉 300g, 花生米 50g, 干辣椒 10 个，花椒 1 勺，葱段 2 根，姜蒜末适量，糖 1 勺，醋 1 勺，生抽 1 勺",
  "steps": "1. 鸡肉切丁腌制 2. 炸花生米 3. 炒香辣椒花椒 4. 加入鸡丁翻炒 5. 加入调料和花生米 6. 翻炒均匀出锅",
  "cuisine": "川菜",
  "difficulty": "中等",
  "tags": ["肉类", "麻辣", "下饭菜"],
  "prep_time": 15,
  "cook_time": 10,
  "user_id": "system",
  "is_public": true,
  "created_at": "2026-04-20"
}'
echo " - 宫保鸡丁"

# 清蒸鲈鱼
curl -s -X PUT "$ES_URL/$INDEX/_doc/5" -H 'Content-Type: application/json' -d '
{
  "name": "清蒸鲈鱼",
  "description": "粤菜经典，鱼肉鲜嫩，原汁原味",
  "ingredients": "鲈鱼 1 条（约 500g), 姜片 5 片，葱段 3 根，蒸鱼豉油 2 勺，料酒 1 勺",
  "steps": "1. 鲈鱼处理干净 2. 鱼身划刀放姜葱 3. 水开上汽蒸 8 分钟 4. 倒掉蒸鱼水 5. 淋上蒸鱼豉油 6. 烧热油浇在鱼身上",
  "cuisine": "粤菜",
  "difficulty": "简单",
  "tags": ["海鲜", "清淡", "健康"],
  "prep_time": 10,
  "cook_time": 8,
  "user_id": "system",
  "is_public": true,
  "created_at": "2026-04-20"
}'
echo " - 清蒸鲈鱼"

# 4. 刷新索引
echo ""
echo "刷新索引..."
curl -s -X POST "$ES_URL/$INDEX/_refresh"
echo ""

# 5. 统计数量
echo ""
echo "统计菜谱数量:"
curl -s "$ES_URL/$INDEX/_count"
echo ""

# 6. 测试搜索
echo ""
echo "测试搜索 '红烧':"
curl -s -X POST "$ES_URL/$INDEX/_search" -H 'Content-Type: application/json' -d '
{
  "query": {
    "multi_match": {
      "query": "红烧",
      "fields": ["name", "description", "ingredients"]
    }
  }
}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'找到 {d[\"hits\"][\"total\"][\"value\"]} 条结果'); [print(f\" - {h['_source']['name']}\") for h in d['hits']['hits']]"

echo ""
echo "=== 初始化完成 ==="
