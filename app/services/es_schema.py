"""Elasticsearch 索引 Schema 定义 - recipes 菜谱索引."""

# 菜谱索引 Mapping (recipes index)
RECIPE_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "ik_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_max_word",  # 最细粒度分词
                    "filter": ["lowercase"],
                }
            }
        },
        # BM25 参数配置
        "similarity": {
            "bm25_custom": {
                "type": "BM25",
                "k1": 1.2,  # 词频饱和度参数，默认 1.2
                "b": 0.75,  # 长度归一化参数，默认 0.75
            }
        },
    },
    "mappings": {
        "properties": {
            # 菜名 - 使用 IK 分词
            "name": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",  # 搜索时用粗粒度
                "similarity": "bm25_custom",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                    }
                },
            },
            # 描述 - 使用 IK 分词
            "description": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "similarity": "bm25_custom",
            },
            # 食材 - 使用 IK 分词
            "ingredients": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "similarity": "bm25_custom",
            },
            # 步骤 - 使用 IK 分词
            "steps": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "similarity": "bm25_custom",
            },
            # 菜系 - keyword 类型（精确匹配）
            "cuisine": {
                "type": "keyword",
            },
            # 难度 - keyword 类型
            "difficulty": {
                "type": "keyword",
            },
            # 标签 - keyword 数组
            "tags": {
                "type": "keyword",
            },
            # 时间 - integer
            "prep_time": {
                "type": "integer",
            },
            "cook_time": {
                "type": "integer",
            },
            # 用户 ID - keyword（用于过滤）
            "user_id": {
                "type": "keyword",
            },
            # 公开状态
            "is_public": {
                "type": "boolean",
            },
            # 审核状态
            "audit_status": {
                "type": "keyword",
            },
            # 来源类型
            "source_type": {
                "type": "keyword",
            },
            # 向量 ID（用于关联 Qdrant）
            "vector_id": {
                "type": "keyword",
            },
            # 创建时间
            "created_at": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis",
            },
        }
    },
}
