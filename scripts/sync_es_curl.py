#!/usr/bin/env python3
"""同步菜谱到 Elasticsearch - 使用 curl 避免 httpx 兼容性问题"""

import asyncio
import asyncpg
import subprocess
import json
from datetime import datetime

DATABASE_URL = "postgresql://cookrag:password@localhost:5432/cookrag"
ES_URL = "http://localhost:9200"
ES_INDEX = "recipes"
BATCH_SIZE = 50


def bulk_index(docs_batch, index_name):
    """使用 curl 批量索引文档"""
    bulk_lines = []
    for doc in docs_batch:
        bulk_lines.append(json.dumps({"index": {"_id": doc["id"]}}))
        bulk_lines.append(json.dumps(doc, ensure_ascii=False))

    bulk_data = "\n".join(bulk_lines) + "\n"

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{ES_URL}/{index_name}/_bulk",
         "-H", "Content-Type: application/x-ndjson",
         "-d", bulk_data],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        resp = json.loads(result.stdout)
        items = resp.get("items", [])
        success = sum(1 for i in items if "error" not in i.get("index", {}))
        return success, len(items) - success, items
    else:
        return 0, len(docs_batch), []


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

    # 获取所有菜谱的食材和步骤
    print("获取食材和步骤数据...")
    recipes_data = []
    for i, recipe in enumerate(recipes):
        recipe_id = str(recipe["id"])
        name = recipe["name"]

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
        recipes_data.append(doc)

        if (i + 1) % 100 == 0:
            print(f"  已加载 {i + 1}/{len(recipes)} 条菜谱")

    print(f"完成加载 {len(recipes_data)} 条菜谱数据\n")

    # 批量索引
    total_success = 0
    total_failed = 0

    for batch_start in range(0, len(recipes_data), BATCH_SIZE):
        batch = recipes_data[batch_start:batch_start + BATCH_SIZE]
        success, failed, items = bulk_index(batch, ES_INDEX)

        total_success += success
        total_failed += failed

        # 显示失败的

        if failed > 0:
            for i, item in enumerate(items):
                if "error" in item.get("index", {}):
                    recipe_name = batch[i].get("name", "unknown")
                    error_reason = item["index"].get("error", {}).get("reason", "unknown")
                    print(f"  失败：{recipe_name} - {error_reason}")

    # 刷新索引
    subprocess.run(
        ["curl", "-s", "-X", "POST", f"{ES_URL}/{ES_INDEX}/_refresh"],
        capture_output=True
    )

    # 统计
    result = subprocess.run(
        ["curl", "-s", f"{ES_URL}/{ES_INDEX}/_count"],
        capture_output=True,
        text=True
    )
    count = json.loads(result.stdout)["count"]

    print(f"\n=== 同步完成 ===")
    print(f"成功：{total_success} 条")
    print(f"失败：{total_failed} 条")
    print(f"ES 中总共有 {count} 条菜谱")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
