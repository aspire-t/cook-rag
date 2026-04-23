#!/usr/bin/env python3
"""Qdrant Collection 管理脚本。

使用方法:
    # 重建 Collection（删除旧数据）
    python scripts/qdrant_collection.py --recreate

    # 检查 Collection 状态
    python scripts/qdrant_collection.py --check

    # 创建 Collection（如果不存在）
    python scripts/qdrant_collection.py --create
"""

import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.qdrant_schema import get_collection_config, PAYLOAD_SCHEMA
from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType


def check_collection(client: QdrantClient, collection_name: str):
    """检查 Collection 状态。"""
    print(f"\n检查 Collection: {collection_name}")
    print("=" * 50)

    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        exists = collection_name in collection_names
    except Exception:
        exists = False

    print(f"存在状态：{'✅ 存在' if exists else '❌ 不存在'}")

    if exists:
        info = client.get_collection(collection_name=collection_name)
        print(f"向量数量：{info.points_count}")
        print(f"向量配置：")
        for name, config in info.config.params.vectors.items():
            print(f"  - {name}: {config.size} 维，{config.distance}")

        print(f"\nPayload 索引：")
        for field, idx_info in info.payload_schema.items():
            print(f"  - {field}: {idx_info.data_type}")

    return exists


def create_collection(client: QdrantClient, collection_name: str):
    """创建 Collection。"""
    print(f"\n创建 Collection: {collection_name}")
    print("=" * 50)

    # 检查是否已存在
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        exists = collection_name in collection_names
    except Exception:
        exists = False

    if exists:
        print("Collection 已存在，跳过创建")
        return True

    config = get_collection_config()

    try:
        client.create_collection(
            collection_name=collection_name,
            **config
        )
        print("✅ Collection 创建成功")

        # 创建 Payload 索引
        print("\n创建 Payload 索引...")
        indexes = [
            ("cuisine", PayloadSchemaType.KEYWORD),
            ("difficulty", PayloadSchemaType.KEYWORD),
            ("user_id", PayloadSchemaType.KEYWORD),
            ("prep_time", PayloadSchemaType.INTEGER),
            ("cook_time", PayloadSchemaType.INTEGER),
            ("is_public", PayloadSchemaType.BOOL),
            ("audit_status", PayloadSchemaType.KEYWORD),
            ("recipe_id", PayloadSchemaType.KEYWORD),
        ]

        for field, schema_type in indexes:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=schema_type
            )
            print(f"  ✅ {field}")

        print("\n✅ Payload 索引创建完成")
        return True

    except Exception as e:
        print(f"❌ Collection 创建失败：{e}")
        return False


def recreate_collection(client: QdrantClient, collection_name: str):
    """重建 Collection（删除旧数据）。"""
    print(f"\n⚠️  警告：即将删除并重建 Collection: {collection_name}")
    print("=" * 50)

    confirm = input("确认删除？(yes/no): ")
    if confirm.lower() != "yes":
        print("操作已取消")
        return False

    # 删除旧 Collection
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        exists = collection_name in collection_names
    except Exception:
        exists = False

    if exists:
        print("删除旧 Collection...")
        client.delete_collection(collection_name=collection_name)
        print("✅ 删除成功")

    # 创建新 Collection
    return create_collection(client, collection_name)


def main():
    parser = argparse.ArgumentParser(description="Qdrant Collection 管理")
    parser.add_argument("--recreate", action="store_true", help="重建 Collection")
    parser.add_argument("--create", action="store_true", help="创建 Collection")
    parser.add_argument("--check", action="store_true", help="检查 Collection 状态")
    args = parser.parse_args()

    client = QdrantClient(url=settings.QDRANT_URL)
    collection_name = settings.QDRANT_COLLECTION

    print(f"Qdrant URL: {settings.QDRANT_URL}")
    print(f"Collection: {collection_name}")

    if args.recreate:
        recreate_collection(client, collection_name)
    elif args.create:
        create_collection(client, collection_name)
    elif args.check:
        check_collection(client, collection_name)
    else:
        parser.print_help()

    print("\n" + "=" * 50)
    print("操作完成!")


if __name__ == "__main__":
    main()
