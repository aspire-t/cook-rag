#!/usr/bin/env python3
"""
将数据库中的菜谱同步到 Elasticsearch.
"""

import asyncio
import asyncpg
import httpx
from datetime import datetime

DATABASE_URL = "postgresql://cookrag:password@localhost:5432/cookrag"
ES_URL = "http://localhost:9200"
ES_INDEX = "recipes"


async def sync_to_es():
    """同步所有菜谱到 ES"""
    print("=== 同步菜谱到 Elasticsearch ===\n")

    # 连接数据库
    conn = await asyncpg.connect(DATABASE_URL)

    # 查询所有公开菜谱
    recipes = await conn.fetch("""
        SELECT r.*,
               (SELECT json_agg(json_build_object('name', i.name, 'amount', i.amount, 'unit', i.unit))
                FROM recipe_ingredients i WHERE i.recipe_id = r.id) as ingredients_data,
               (SELECT json_agg(json_build_object('step_no', s.step_no, 'description', s.description, 'duration', s.duration_seconds))
                FROM recipe_steps s WHERE s.recipe_id = r.id) as steps_data
        FROM recipes r
        WHERE r.is_public = true AND r.audit_status = 'approved'
        ORDER BY r.created_at DESC
    """)

    print(f"找到 {len(recipes)} 条菜谱\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        success = 0
        failed = 0

        for recipe in recipes:
            recipe_id = str(recipe["id"])
            name = recipe["name"]

            # 构建 ingredients 字符串
            ingredients_data = recipe["ingredients_data"] or []
            if ingredients_data and isinstance(ingredients_data[0], dict):
                ingredients = ", ".join([
                    f"{ing['name']}{str(ing['amount'] or '')}{ing['unit'] or ''}"
                    for ing in ingredients_data[:10]
                ])
            else:
                ingredients = ""

            # 构建 steps 字符串
            steps_data = recipe["steps_data"] or []
            if steps_data and isinstance(steps_data[0], dict):
                steps = ". ".join([
                    f"{step['step_no']}. {step['description']}"
                    for step in steps_data[:10]
                ])
            else:
                steps = ""

            # 构建 description
            description = recipe["description"] or ""
            if not description and ingredients_data:
                description = f"{name}，主要食材：{ingredients[:100]}"

            # ES 文档
            doc = {
                "id": recipe_id,
                "name": name,
                "description": description[:500],
                "ingredients": ingredients[:1000],
                "steps": steps[:2000],
                "cuisine": recipe["cuisine"],
                "difficulty": recipe["difficulty"],
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

            try:
                # 索引到 ES
                response = await client.put(
                    f"{ES_URL}/{ES_INDEX}/_doc/{recipe_id}",
                    json=doc
                )
                if response.status_code in [200, 201]:
                    success += 1
                    print(f"✓ {name}")
                else:
                    failed += 1
                    print(f"✗ {name}: {response.text[:100]}")
            except Exception as e:
                failed += 1
                print(f"✗ {name}: {e}")

        # 刷新索引
        await client.post(f"{ES_URL}/{ES_INDEX}/_refresh")

    print(f"\n=== 同步完成 ===")
    print(f"成功：{success} 条")
    print(f"失败：{failed} 条")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(sync_to_es())
