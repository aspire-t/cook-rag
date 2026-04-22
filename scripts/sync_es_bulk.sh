#!/bin/bash
# 批量同步菜谱到 Elasticsearch

DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="cookrag"
DB_USER="cookrag"
DB_PASS="password"
ES_URL="http://localhost:9200"
ES_INDEX="recipes"

echo "=== 批量同步菜谱到 Elasticsearch ==="

# 删除旧索引并重新创建
echo "删除旧索引..."
curl -s -X DELETE "$ES_URL/$ES_INDEX" > /dev/null 2>&1

echo "创建新索引..."
curl -s -X PUT "$ES_URL/$ES_INDEX" -H 'Content-Type: application/json' -d '
{
  "settings": {
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
      "id": {"type": "keyword"},
      "name": {"type": "text", "similarity": "bm25_custom", "fields": {"keyword": {"type": "keyword"}}},
      "description": {"type": "text", "similarity": "bm25_custom"},
      "ingredients": {"type": "text", "similarity": "bm25_custom"},
      "steps": {"type": "text", "similarity": "bm25_custom"},
      "cuisine": {"type": "keyword"},
      "difficulty": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "prep_time": {"type": "integer"},
      "cook_time": {"type": "integer"},
      "user_id": {"type": "keyword"},
      "is_public": {"type": "boolean"},
      "audit_status": {"type": "keyword"},
      "source_type": {"type": "keyword"},
      "source_url": {"type": "text"},
      "created_at": {"type": "date"}
    }
  }
}'

echo ""
echo "同步数据..."

# 使用 psql 导出数据并同步到 ES
psql -h $DB_HOST -p $DB_PORT -U $DB_PASS -d $DB_NAME -t -A -F'|' -c "
SELECT
    r.id,
    r.name,
    COALESCE(r.description, ''),
    COALESCE(r.cuisine, ''),
    COALESCE(r.difficulty, ''),
    r.prep_time,
    r.cook_time,
    COALESCE(r.tags, '[]'::jsonb),
    COALESCE(r.user_id, '00000000-0000-0000-0000-000000000000'),
    r.is_public,
    r.audit_status,
    r.source_type,
    COALESCE(r.source_url, ''),
    r.created_at,
    (SELECT COALESCE(string_agg(i.name || ' ' || COALESCE(i.amount::text, '') || COALESCE(i.unit, ''), ', '), '')
     FROM recipe_ingredients i WHERE i.recipe_id = r.id) as ingredients,
    (SELECT COALESCE(string_agg(s.step_no || '. ' || s.description, '. '), '')
     FROM recipe_steps s WHERE s.recipe_id = r.id) as steps
FROM recipes r
WHERE r.is_public = true AND r.audit_status = 'approved'
ORDER BY r.created_at DESC
LIMIT 500
" | while IFS='|' read -r id name description cuisine difficulty prep_time cook_time tags user_id is_public audit_status source_type source_url created_at ingredients steps; do
    # 清理字段
    name=$(echo "$name" | sed 's/"/\\"/g' | tr -d '\n\r')
    description=$(echo "$description" | sed 's/"/\\"/g' | tr -d '\n\r' | head -c 500)
    ingredients=$(echo "$ingredients" | sed 's/"/\\"/g' | tr -d '\n\r' | head -c 1000)
    steps=$(echo "$steps" | sed 's/"/\\"/g' | tr -d '\n\r' | head -c 2000)

    # 构建 JSON 并发送到 ES
    curl -s -X POST "$ES_URL/$ES_INDEX/_doc/$id" -H 'Content-Type: application/json' -d "
{
  \"id\": \"$id\",
  \"name\": \"$name\",
  \"description\": \"$description\",
  \"ingredients\": \"$ingredients\",
  \"steps\": \"$steps\",
  \"cuisine\": \"$cuisine\",
  \"difficulty\": \"$difficulty\",
  \"tags\": $tags,
  \"prep_time\": $prep_time,
  \"cook_time\": $cook_time,
  \"user_id\": \"$user_id\",
  \"is_public\": $is_public,
  \"audit_status\": \"$audit_status\",
  \"source_type\": \"$source_type\",
  \"source_url\": \"$source_url\",
  \"created_at\": \"$created_at\"
}" > /dev/null

    echo "✓ $name"
done

# 刷新索引
echo ""
curl -s -X POST "$ES_URL/$ES_INDEX/_refresh" > /dev/null

# 统计数量
COUNT=$(curl -s "$ES_URL/$ES_INDEX/_count" | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])")

echo ""
echo "=== 同步完成 ==="
echo "ES 中共有 $COUNT 条菜谱"
