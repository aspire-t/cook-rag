#!/usr/bin/env python3
"""使用批量 API 同步菜谱到 Elasticsearch"""

import asyncio
import asyncpg
import httpx
import json
from datetime import datetime

DATABASE_URL = "postgresql://cookrag:password@localhost:5432/cookrag"
ES_URL = "http://localhost:9200"
ES_INDEX = "recipes"
BATCH_SIZE = 50


async def main():
    print("=== 批量同步菜谱到 Elasticsearch ===\n")

    conn = await asyncpg.connect(DATABASE_URL)
    print("数据库连接成功")

    recipes = await conn.fetch("""
        SELECT r.id, r.name, r.description, r.cuisine, r.difficulty,
               r.prep_time, r.cook_time, r.tags, r.user_id,
               r.is_public, r.audit_status, r.source_type,
               r.source_url, r.created_at
        FROM recipes r
        WHERE r.is_public = true AND r.audit_status = 'approved'
        ORDER BY r.created_at DESC
    """)

    print(f"找到 {len(recipes)} 条菜谱\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 检查索引是否存在
        resp = await client.get(f"{ES_URL}/{ES_INDEX}")
        if resp.status_code == 200:
            print("索引已存在，删除旧索引...")
            await client.delete(f"{ES_URL}/{ES_INDEX}")

        index_config = {
            "settings": {
                "number_of_replicas": 0,
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
                    "name": {"type": "text", "similarity": "bm25_custom"},
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
        }

        print("创建索引...")
        resp = await client.put(f"{ES_URL}/{ES_INDEX}", json=index_config)
        print(f"创建索引：{resp.status_code} - {resp.text[:100]}")

        success = 0
        failed = 0

        # 批量处理
        for batch_start in range(0, len(recipes), BATCH_SIZE):
            batch = recipes[batch_start:batch_start + BATCH_SIZE]
            bulk_lines = []

            for recipe in batch:
                recipe_id = str(recipe["id"])
                name = recipe["name"]

                # 获取食材和步骤
                ing_result = await conn.fetch("""
                    SELECT name, amount, unit FROM recipe_ingredients
                    WHERE recipe_id = $1 ORDER BY sequence
                """, recipe["id"])

                ingredients = ", ".join([
                    f"{r['name']}{str(r['amount'] or '')}{r['unit'] or ''}"
                    for r in ing_result
                ]) if ing_result else ""

                step_result = await conn.fetch("""
                    SELECT step_no, description FROM recipe_steps
                    WHERE recipe_id = $1 ORDER BY step_no
                """, recipe["id"])

                steps = ". ".join([
                    f"{r['step_no']}. {r['description']}"
                    for r in step_result
                ]) if step_result else ""

                doc = {
                    "id": recipe_id,
                    "name": name,
                    "description": recipe["description"] or "",
                    "ingredients": ingredients[:1000],
                    "steps": steps[:2000],
                    "cuisine": recipe["cuisine"] or "",
                    "difficulty": recipe["difficulty"] or "",
                    "tags": recipe["tags"] or [],
                    "prep_time": recipe["prep_time"],
                    "cook_time": recipe["cook_time"],
                    "user_id": str(recipe["user_id"]) if recipe["user_id"] else "system",
                    "is_public": recipe["is_public"],
                    "audit_status": recipe["audit_status"],
                    "source_type": recipe["source_type"],
                    "source_url": recipe["source_url"],
                    "created_at": recipe["created_at"].isoformat() if recipe["created_at"] else datetime.now().isoformat(),
                }

                bulk_lines.append(json.dumps({"index": {"_id": recipe_id}}))
                bulk_lines.append(json.dumps(doc, ensure_ascii=False))

            # 发送批量请求
            bulk_data = "\n".join(bulk_lines) + "\n"
            try:
                resp = await client.post(
                    f"{ES_URL}/{ES_INDEX}/_bulk",
                    content=bulk_data,
                    headers={"Content-Type": "application/x-ndjson"}
                )
                if resp.status_code in [200, 201]:
                    result = resp.json()
                    items = result.get("items", [])
                    batch_success = sum(1 for i in items if "error" not in i.get("index", {}))
                    batch_failed = len(items) - batch_success
                    success += batch_success
                    failed += batch_failed
                    print(f"批次 {batch_start // BATCH_SIZE + 1}: 成功 {batch_success}/{len(items)}")
                    if batch_failed > 0:
                        for i, item in enumerate(items):
                            if "error" in item.get("index", {}):
                                print(f"  失败：{batch[i].get('name', 'unknown')} - {item['index'].get('error', {}).get('reason', 'unknown')}")
                else:
                    print(f"批次失败：HTTP {resp.status_code} - {resp.text[:200]}")
                    failed += len(batch)
            except Exception as e:
                print(f"批次异常：{e}")
                failed += len(batch)

        # 刷新索引
        await client.post(f"{ES_URL}/{ES_INDEX}/_refresh")

        # 统计
        count_resp = await client.get(f"{ES_URL}/{ES_INDEX}/_count")
        count = count_resp.json()["count"]

        print(f"\n=== 同步完成 ===")
        print(f"成功：{success} 条")
        print(f"失败：{failed} 条")
        print(f"ES 中总共有 {count} 条菜谱")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
