"""Qdrant Collection Schema 定义."""

from qdrant_client.http.models import (
    VectorParams,
    Distance,
    BinaryQuantization,
    BinaryQuantizationConfig,
)


# 向量维度（使用 BGE 模型的输出维度）
VECTOR_SIZE = 1024  # BGE-Large-v1.5 的维度


def get_collection_config() -> dict:
    """
    获取 Collection 配置.

    Returns:
        配置字典
    """
    return {
        "vectors": {
            # 四路向量配置
            "name_vec": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            "desc_vec": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            "step_vec": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            "tag_vec": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        },
        # 二进制量化，减少内存占用
        "quantization_config": BinaryQuantization(
            binary=BinaryQuantizationConfig(always_ram=True)
        ),
        # MVP 阶段单分片
        "shard_number": 1,
        "replication_factor": 1,
    }


# Payload Schema 定义（文档说明）
PAYLOAD_SCHEMA = {
    # 菜系过滤
    "cuisine": {"type": "keyword", "description": "菜系（川菜/粤菜等）"},
    # 难度过滤
    "difficulty": {"type": "keyword", "description": "难度（easy/medium/hard）"},
    # 口味标签
    "taste": {"type": "keyword", "description": "口味标签数组"},
    # 时间范围过滤
    "prep_time": {"type": "integer", "description": "准备时间（分钟）"},
    "cook_time": {"type": "integer", "description": "烹饪时间（分钟）"},
    # 多租户隔离
    "user_id": {"type": "keyword", "description": "用户 ID"},
    "enterprise_id": {"type": "keyword", "description": "企业 ID"},
    # 公开状态
    "is_public": {"type": "boolean", "description": "是否公开"},
    # 审核状态
    "audit_status": {"type": "keyword", "description": "审核状态"},
    # 菜谱 ID（用于关联 PostgreSQL）
    "recipe_id": {"type": "keyword", "description": "菜谱 ID"},
    # 菜名（用于返回）
    "name": {"type": "keyword", "description": "菜名"},
}
