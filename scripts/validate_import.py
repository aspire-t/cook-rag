#!/usr/bin/env python3
"""数据导入和验证脚本 - 本地测试。

使用方法:
    python scripts/validate_import.py --all
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.qdrant_schema import get_collection_config


async def check_database():
    """检查数据库连接。"""
    print("\n1. 检查 PostgreSQL 连接...")
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        print("   ✅ PostgreSQL 连接成功")
        return True
    except Exception as e:
        print(f"   ❌ PostgreSQL 连接失败：{e}")
        return False


async def check_redis():
    """检查 Redis 连接。"""
    print("\n2. 检查 Redis 连接...")
    try:
        import redis.asyncio as redis

        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        print("   ✅ Redis 连接成功")
        return True
    except Exception as e:
        print(f"   ❌ Redis 连接失败：{e}")
        return False


async def check_es():
    """检查 Elasticsearch 连接。"""
    print("\n3. 检查 Elasticsearch 连接...")
    try:
        from elasticsearch import AsyncElasticsearch

        es = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
        info = await es.info()
        await es.close()
        print(f"   ✅ ES 连接成功 - 版本：{info['version']['number']}")
        return True
    except Exception as e:
        print(f"   ❌ ES 连接失败：{e}")
        return False


async def check_qdrant():
    """检查 Qdrant 连接。"""
    print("\n4. 检查 Qdrant 连接...")
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.QDRANT_URL)

        # 检查集群状态
        from qdrant_client.http.models import ClusterStatus
        try:
            cluster_info = client.cluster_info()
            print(f"   ✅ Qdrant 连接成功")
        except Exception:
            pass

        # 检查 Collection 是否存在
        try:
            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]
            exists = settings.QDRANT_COLLECTION in collection_names
            print(f"   Collection '{settings.QDRANT_COLLECTION}': {'存在' if exists else '不存在'}")

            if exists:
                info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
                print(f"   向量配置:")
                for name, config in info.config.params.vectors.items():
                    print(f"     - {name}: {config.size}维")
        except Exception as e:
            print(f"   获取 Collection 信息失败：{e}")

        return True
    except Exception as e:
        print(f"   ❌ Qdrant 连接失败：{e}")
        return False


def check_config():
    """检查配置文件。"""
    print("\n5. 检查配置文件...")

    # 检查 .env 文件
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"   ✅ .env 文件存在")
    else:
        print(f"   ⚠️  .env 文件不存在，使用默认配置")

    # 检查关键配置
    print(f"\n   当前配置:")
    print(f"   - DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    print(f"   - REDIS_URL: {settings.REDIS_URL}")
    print(f"   - QDRANT_URL: {settings.QDRANT_URL}")
    print(f"   - ELASTICSEARCH_URL: {settings.ELASTICSEARCH_URL}")
    print(f"   - CLIP_DEVICE: {settings.CLIP_DEVICE if hasattr(settings, 'CLIP_DEVICE') else 'N/A'}")

    return True


def check_image_config():
    """检查图片存储配置。"""
    print("\n6. 检查图片存储配置...")

    if hasattr(settings, 'IMAGE_REPO_OWNER'):
        print(f"   ✅ IMAGE_REPO_OWNER: {settings.IMAGE_REPO_OWNER}")
    else:
        print(f"   ⚠️  IMAGE_REPO_OWNER 未配置")

    if hasattr(settings, 'IMAGE_REPO_NAME'):
        print(f"   ✅ IMAGE_REPO_NAME: {settings.IMAGE_REPO_NAME}")
    else:
        print(f"   ⚠️  IMAGE_REPO_NAME 未配置")

    if hasattr(settings, 'IMAGE_BASE_CDN_URL'):
        print(f"   ✅ IMAGE_BASE_CDN_URL: {settings.IMAGE_BASE_CDN_URL}")
    else:
        print(f"   ⚠️  IMAGE_BASE_CDN_URL 未配置")

    return True


async def run_all_checks():
    """运行所有检查。"""
    print("=" * 60)
    print("CookRAG 数据导入验证")
    print("=" * 60)

    results = {
        "config": check_config(),
        "image_config": check_image_config(),
        "database": await check_database(),
        "redis": await check_redis(),
        "es": await check_es(),
        "qdrant": await check_qdrant()
    }

    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")

    if all_passed:
        print("\n🎉 所有检查通过！可以执行数据导入")
        print("\n下一步:")
        print("1. python scripts/qdrant_collection.py --create")
        print("2. python scripts/import_data.py --source data/howtocook")
        print("3. python scripts/import_images.py --token YOUR_TOKEN")
    else:
        print("\n⚠️  部分检查失败，请先解决")

    return all_passed


async def main():
    parser = argparse.ArgumentParser(description="数据导入验证")
    parser.add_argument("--all", action="store_true", help="运行所有检查")
    parser.add_argument("--db", action="store_true", help="仅检查数据库")
    parser.add_argument("--redis", action="store_true", help="仅检查 Redis")
    parser.add_argument("--es", action="store_true", help="仅检查 ES")
    parser.add_argument("--qdrant", action="store_true", help="仅检查 Qdrant")
    args = parser.parse_args()

    if args.all:
        await run_all_checks()
    elif args.db:
        await check_database()
    elif args.redis:
        await check_redis()
    elif args.es:
        await check_es()
    elif args.qdrant:
        await check_qdrant()
    else:
        await run_all_checks()


if __name__ == "__main__":
    asyncio.run(main())
