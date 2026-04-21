"""数据导入器 - 导入菜谱到 PostgreSQL、Elasticsearch、Qdrant."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.recipe import Recipe
from app.models.ingredient import RecipeIngredient
from app.models.step import RecipeStep
from app.services.es_search import ESSearchService
from app.services.qdrant_service import QdrantService
from app.services.embedding_service import EmbeddingService
from qdrant_client.http.models import PointStruct


class DataImporter:
    """数据导入器."""

    def __init__(
        self,
        db_session: AsyncSession,
        es_service: Optional[ESSearchService] = None,
        qdrant_service: Optional[QdrantService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        初始化导入器.

        Args:
            db_session: 数据库会话
            es_service: ES 服务
            qdrant_service: Qdrant 服务
            embedding_service: Embedding 服务
        """
        self.db_session = db_session
        self.es_service = es_service or ESSearchService()
        self.qdrant_service = qdrant_service or QdrantService()
        self.embedding_service = embedding_service or EmbeddingService()

    async def import_recipe(self, parsed_recipe: Any, source_url: Optional[str] = None) -> str:
        """
        导入单个菜谱.

        Args:
            parsed_recipe: 解析后的菜谱数据
            source_url: 来源 URL

        Returns:
            菜谱 ID
        """
        # 生成菜谱 ID
        recipe_id = str(uuid.uuid4())

        # 1. 导入 PostgreSQL
        await self._import_to_postgres(recipe_id, parsed_recipe, source_url)

        # 2. 导入 Elasticsearch
        await self._import_to_es(recipe_id, parsed_recipe)

        # 3. 生成向量并导入 Qdrant
        await self._import_to_qdrant(recipe_id, parsed_recipe)

        return recipe_id

    async def _import_to_postgres(
        self,
        recipe_id: str,
        parsed_recipe: Any,
        source_url: Optional[str],
    ):
        """导入到 PostgreSQL."""
        # 创建菜谱
        recipe = Recipe(
            id=uuid.UUID(recipe_id),
            name=parsed_recipe.name,
            description=parsed_recipe.description[:2000] if parsed_recipe.description else "",
            cuisine=self._detect_cuisine(parsed_recipe.tags),
            difficulty="medium",  # 默认难度
            prep_time=30,  # 默认准备时间
            cook_time=30,  # 默认烹饪时间
            tags=parsed_recipe.tags or [],
            source_url=source_url,
            source_type="howtocook",
            is_public=True,
            audit_status="approved",
            vector_id=recipe_id,  # 与 Qdrant ID 一致
        )

        self.db_session.add(recipe)
        await self.db_session.flush()

        # 创建食材
        for idx, ing in enumerate(parsed_recipe.ingredients):
            ingredient = RecipeIngredient(
                recipe_id=uuid.UUID(recipe_id),
                name=ing.get("name", ""),
                amount=ing.get("amount"),
                unit=ing.get("unit"),
                sequence=idx,
                notes=ing.get("notes"),
            )
            self.db_session.add(ingredient)

        # 创建步骤
        for step in parsed_recipe.steps:
            recipe_step = RecipeStep(
                recipe_id=uuid.UUID(recipe_id),
                step_no=step.get("step_no", 0),
                description=step.get("description", ""),
                duration_seconds=None,
                tips=step.get("tips"),
            )
            self.db_session.add(recipe_step)

        await self.db_session.commit()

    async def _import_to_es(self, recipe_id: str, parsed_recipe: Any):
        """导入到 Elasticsearch."""
        # 构建 ES 文档
        doc = {
            "recipe_id": recipe_id,
            "name": parsed_recipe.name,
            "description": parsed_recipe.description or "",
            "ingredients": " ".join([ing.get("name", "") for ing in parsed_recipe.ingredients]),
            "steps": " ".join([step.get("description", "") for step in parsed_recipe.steps]),
            "cuisine": self._detect_cuisine(parsed_recipe.tags),
            "difficulty": "medium",
            "tags": parsed_recipe.tags or [],
            "prep_time": 30,
            "cook_time": 30,
            "is_public": True,
            "audit_status": "approved",
            "source_type": "howtocook",
            "vector_id": recipe_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.es_service.index_recipe(recipe_id, doc)

    async def _import_to_qdrant(self, recipe_id: str, parsed_recipe: Any):
        """导入到 Qdrant."""
        # 生成多路向量
        vectors = self.embedding_service.generate_recipe_vectors(
            name=parsed_recipe.name,
            description=parsed_recipe.description or "",
            ingredients=[ing.get("name", "") for ing in parsed_recipe.ingredients],
            steps=[step.get("description", "") for step in parsed_recipe.steps],
            tags=parsed_recipe.tags or [],
        )

        # 构建 payload
        payload = {
            "recipe_id": recipe_id,
            "name": parsed_recipe.name,
            "cuisine": self._detect_cuisine(parsed_recipe.tags),
            "difficulty": "medium",
            "prep_time": 30,
            "cook_time": 30,
            "taste": parsed_recipe.tags or [],
            "is_public": True,
            "audit_status": "approved",
        }

        # 构建向量点
        point = PointStruct(
            id=recipe_id,
            vector={
                "name_vec": vectors.name_vec,
                "desc_vec": vectors.desc_vec,
                "step_vec": vectors.step_vec,
                "tag_vec": vectors.tag_vec,
            },
            payload=payload,
        )

        self.qdrant_service.upsert([point])

    def _detect_cuisine(self, tags: List[str]) -> Optional[str]:
        """从标签中检测菜系."""
        cuisine_keywords = {
            "川菜": ["川菜", "四川", "麻辣"],
            "粤菜": ["粤菜", "广东", "清淡"],
            "鲁菜": ["鲁菜", "山东"],
            "苏菜": ["苏菜", "江苏", "淮扬"],
            "浙菜": ["浙菜", "浙江", "杭州"],
            "闽菜": ["闽菜", "福建"],
            "湘菜": ["湘菜", "湖南"],
            "徽菜": ["徽菜", "安徽"],
        }

        for cuisine, keywords in cuisine_keywords.items():
            for tag in tags:
                if any(kw in tag for kw in keywords):
                    return cuisine

        return None


async def import_recipe_batch(
    parsed_recipes: List[Any],
    db_session: AsyncSession,
) -> Dict[str, Any]:
    """
    批量导入菜谱.

    Args:
        parsed_recipes: 解析后的菜谱列表
        db_session: 数据库会话

    Returns:
        导入结果统计
    """
    importer = DataImporter(db_session)
    results = {
        "total": len(parsed_recipes),
        "success": 0,
        "failed": 0,
        "recipe_ids": [],
        "errors": [],
    }

    for idx, parsed in enumerate(parsed_recipes):
        try:
            recipe_id = await importer.import_recipe(parsed)
            results["success"] += 1
            results["recipe_ids"].append(recipe_id)
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"index": idx, "error": str(e)})

    return results
