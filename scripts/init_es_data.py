#!/usr/bin/env python3
"""初始化 Elasticsearch 索引并添加测试菜谱数据."""

import asyncio
import httpx


async def init_es_data():
    """初始化 ES 索引和测试数据."""

    es_url = "http://localhost:9200"
    index_name = "recipes"

    # 测试数据
    test_recipes = [
        {
            "id": "1",
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
            "is_public": True,
            "audit_status": "approved",
            "source_type": "traditional",
            "created_at": "2026-04-20T00:00:00Z",
        },
        {
            "id": "2",
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
            "is_public": True,
            "audit_status": "approved",
            "source_type": "traditional",
            "created_at": "2026-04-20T00:00:00Z",
        },
        {
            "id": "3",
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
            "is_public": True,
            "audit_status": "approved",
            "source_type": "traditional",
            "created_at": "2026-04-20T00:00:00Z",
        },
        {
            "id": "4",
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
            "is_public": True,
            "audit_status": "approved",
            "source_type": "traditional",
            "created_at": "2026-04-20T00:00:00Z",
        },
        {
            "id": "5",
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
            "is_public": True,
            "audit_status": "approved",
            "source_type": "traditional",
            "created_at": "2026-04-20T00:00:00Z",
        },
    ]

    async with httpx.AsyncClient() as client:
        # 1. 创建索引
        print("正在创建索引...")
        index_mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "ik_analyzer": {
                            "type": "custom",
                            "tokenizer": "ik_max_word",
                            "filter": ["lowercase"],
                        }
                    }
                },
                "similarity": {
                    "bm25_custom": {
                        "type": "BM25",
                        "k1": 1.2,
                        "b": 0.75,
                    }
                },
            },
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart",
                        "similarity": "bm25_custom",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart",
                        "similarity": "bm25_custom",
                    },
                    "ingredients": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart",
                        "similarity": "bm25_custom",
                    },
                    "steps": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart",
                        "similarity": "bm25_custom",
                    },
                    "cuisine": {"type": "keyword"},
                    "difficulty": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "prep_time": {"type": "integer"},
                    "cook_time": {"type": "integer"},
                    "user_id": {"type": "keyword"},
                    "is_public": {"type": "boolean"},
                    "audit_status": {"type": "keyword"},
                    "source_type": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            },
        }

        try:
            # 删除已存在的索引
            await client.delete(f"{es_url}/{index_name}")
            print("已删除旧索引")
        except:
            pass

        response = await client.put(f"{es_url}/{index_name}", json=index_mapping)
        if response.status_code == 200:
            print("索引创建成功!")
        else:
            print(f"索引创建失败：{response.text}")
            return

        # 2. 插入测试数据
        print("\n正在插入测试菜谱数据...")
        for recipe in test_recipes:
            response = await client.put(f"{es_url}/{index_name}/_doc/{recipe['id']}", json=recipe)
            if response.status_code == 201:
                print(f"  ✓ 已插入：{recipe['name']}")
            else:
                print(f"  ✗ 插入失败 {recipe['name']}: {response.text}")

        # 3. 刷新索引
        await client.post(f"{es_url}/{index_name}/_refresh")
        print("\n索引刷新完成!")

        # 4. 验证数据
        count_response = await client.get(f"{es_url}/{index_name}/_count")
        if count_response.status_code == 200:
            count = count_response.json().get("count", 0)
            print(f"\n索引中共有 {count} 条菜谱记录")

        # 5. 测试搜索
        print("\n测试搜索 '红烧'...")
        search_response = await client.post(
            f"{es_url}/{index_name}/_search",
            json={
                "query": {
                    "multi_match": {
                        "query": "红烧",
                        "fields": ["name", "description", "ingredients", "steps"],
                    }
                }
            }
        )
        if search_response.status_code == 200:
            hits = search_response.json()["hits"]["hits"]
            print(f"找到 {len(hits)} 条结果:")
            for hit in hits:
                print(f"  - {hit['_source']['name']} (得分：{hit['_score']:.2f})")


if __name__ == "__main__":
    asyncio.run(init_es_data())
