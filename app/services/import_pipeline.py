"""HowToCook 数据导入流水线."""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.services.htc_parser import HowToCookParser, get_howtocook_parser
from app.services.embedding_service import EmbeddingService
from app.services.es_search import ESSearchService
from app.services.qdrant_service import QdrantService
from app.services.data_importer import DataImporter
from app.services.import_progress import ImportProgress, get_import_progress


class ImportPipeline:
    """HowToCook 数据导入流水线."""

    def __init__(
        self,
        data_dir: str = "data/howtocook",
        checkpoint_file: str = "data/.import_checkpoint.json",
        batch_size: int = 100,
    ):
        """
        初始化导入流水线.

        Args:
            data_dir: HowToCook 数据目录
            checkpoint_file: 断点文件
            batch_size: 批次大小
        """
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        self.parser = get_howtocook_parser()
        self.progress = get_import_progress(checkpoint_file)

        # 服务实例（懒加载）
        self._db_session: Optional[AsyncSession] = None
        self._es_service: Optional[ESSearchService] = None
        self._qdrant_service: Optional[QdrantService] = None
        self._embedding_service: Optional[EmbeddingService] = None

    @property
    def db_session(self) -> AsyncSession:
        """获取数据库会话."""
        if self._db_session is None:
            engine = create_async_engine(settings.DATABASE_URL)
            async_session = async_sessionmaker(engine, class_=AsyncSession)
            self._db_session = async_session()
        return self._db_session

    @property
    def es_service(self) -> ESSearchService:
        """获取 ES 服务."""
        if self._es_service is None:
            self._es_service = ESSearchService()
        return self._es_service

    @property
    def qdrant_service(self) -> QdrantService:
        """获取 Qdrant 服务."""
        if self._qdrant_service is None:
            self._qdrant_service = QdrantService()
        return self._qdrant_service

    @property
    def embedding_service(self) -> EmbeddingService:
        """获取 Embedding 服务."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _list_markdown_files(self) -> List[Path]:
        """列出所有 Markdown 文件."""
        files = list(self.data_dir.glob("**/*.md"))
        return sorted(files)

    def _filter_pending_files(self, files: List[Path]) -> List[Path]:
        """
        过滤出待导入的文件.

        Args:
            files: 所有文件列表

        Returns:
            待导入文件列表
        """
        imported = set(self.progress.get_imported_files())
        return [f for f in files if str(f) not in imported]

    async def run(self, full_import: bool = False) -> Dict[str, Any]:
        """
        运行导入流水线.

        Args:
            full_import: 是否全量导入（忽略断点）

        Returns:
            导入结果统计
        """
        # 列出所有文件
        all_files = self._list_markdown_files()
        total_count = len(all_files)

        if total_count == 0:
            return {
                "status": "no_data",
                "message": "数据目录为空",
            }

        # 过滤待导入文件
        if full_import:
            self.progress.reset()
            pending_files = all_files
        else:
            pending_files = self._filter_pending_files(all_files)

        if len(pending_files) == 0:
            return {
                "status": "completed",
                "message": "所有文件已导入",
                "total": total_count,
            }

        # 开始导入
        self.progress.start_import(total_count)

        results = {
            "total": total_count,
            "pending": len(pending_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        # 批量处理
        batches = [
            pending_files[i : i + self.batch_size]
            for i in range(0, len(pending_files), self.batch_size)
        ]

        for batch_idx, batch in enumerate(batches):
            batch_result = await self._process_batch(batch)
            results["success"] += batch_result["success"]
            results["failed"] += batch_result["failed"]
            if batch_result["errors"]:
                results["errors"].extend(batch_result["errors"])

            print(f"批次 {batch_idx + 1}/{len(batches)} 完成：成功 {batch_result['success']}, 失败 {batch_result['failed']}")

        # 完成导入
        self.progress.complete_import()

        return {
            "status": "completed",
            **results,
        }

    async def _process_batch(self, files: List[Path]) -> Dict[str, Any]:
        """
        处理单个批次.

        Args:
            files: 文件列表

        Returns:
            处理结果
        """
        result = {
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for file_path in files:
            try:
                # 1. Markdown 解析
                parsed_recipe = self.parser.parse_file(file_path)

                # 数据清洗
                parsed_recipe = self._clean_recipe(parsed_recipe)

                # 数据校验
                if not self._validate_recipe(parsed_recipe):
                    raise ValueError("数据校验失败")

                # 2. 向量化
                vectors = self.embedding_service.generate_recipe_vectors(
                    name=parsed_recipe.name,
                    description=parsed_recipe.description or "",
                    ingredients=[ing.get("name", "") for ing in parsed_recipe.ingredients],
                    steps=[step.get("description", "") for step in parsed_recipe.steps],
                    tags=parsed_recipe.tags or [],
                )

                # 3. 导入 PostgreSQL
                recipe_id = await self._save_to_postgres(parsed_recipe, file_path)

                # 4. 导入 Elasticsearch
                await self._save_to_es(recipe_id, parsed_recipe)

                # 5. 导入 Qdrant
                await self._save_to_qdrant(recipe_id, parsed_recipe, vectors)

                # 记录成功
                self.progress.record_success(str(file_path), recipe_id)
                result["success"] += 1

            except Exception as e:
                error_msg = f"{file_path}: {str(e)}"
                result["errors"].append({"file": str(file_path), "error": str(e)})
                self.progress.record_failure(str(file_path), str(e))
                result["failed"] += 1
                print(f"导入失败 {file_path}: {e}")

        return result

    def _clean_recipe(self, parsed_recipe: Any) -> Any:
        """
        数据清洗.

        Args:
            parsed_recipe: 解析后的菜谱

        Returns:
            清洗后的菜谱
        """
        # 清理菜名
        if parsed_recipe.name:
            parsed_recipe.name = parsed_recipe.name.strip()

        # 清理描述
        if parsed_recipe.description:
            parsed_recipe.description = parsed_recipe.description.strip()[:2000]

        # 清理食材
        for ing in parsed_recipe.ingredients:
            if ing.get("name"):
                ing["name"] = ing["name"].strip()

        # 清理步骤
        for step in parsed_recipe.steps:
            if step.get("description"):
                step["description"] = step["description"].strip()

        return parsed_recipe

    def _validate_recipe(self, parsed_recipe: Any) -> bool:
        """
        数据校验.

        Args:
            parsed_recipe: 解析后的菜谱

        Returns:
            True 如果校验通过
        """
        # 必须有菜名
        if not parsed_recipe.name:
            return False

        # 必须有食材
        if not parsed_recipe.ingredients:
            return False

        # 必须有步骤
        if not parsed_recipe.steps:
            return False

        return True

    async def _save_to_postgres(self, parsed_recipe: Any, source_file: Path) -> str:
        """保存到 PostgreSQL."""
        from uuid import uuid4
        from datetime import datetime, timezone
        from app.models.recipe import Recipe
        from app.models.ingredient import RecipeIngredient
        from app.models.step import RecipeStep

        recipe_id = str(uuid4())

        recipe = Recipe(
            id=uuid4(),
            name=parsed_recipe.name,
            description=parsed_recipe.description or "",
            cuisine=self._detect_cuisine(parsed_recipe.tags),
            difficulty="medium",
            prep_time=30,
            cook_time=30,
            tags=parsed_recipe.tags or [],
            source_url=str(source_file),
            source_type="howtocook",
            is_public=True,
            audit_status="approved",
            vector_id=recipe_id,
        )

        self.db_session.add(recipe)
        await self.db_session.flush()

        for idx, ing in enumerate(parsed_recipe.ingredients):
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                name=ing.get("name", ""),
                amount=ing.get("amount"),
                unit=ing.get("unit"),
                sequence=idx,
                notes=ing.get("notes"),
            )
            self.db_session.add(ingredient)

        for step in parsed_recipe.steps:
            recipe_step = RecipeStep(
                recipe_id=recipe.id,
                step_no=step.get("step_no", 0),
                description=step.get("description", ""),
                duration_seconds=None,
                tips=step.get("tips"),
            )
            self.db_session.add(recipe_step)

        await self.db_session.commit()

        return recipe_id

    async def _save_to_es(self, recipe_id: str, parsed_recipe: Any):
        """保存到 Elasticsearch."""
        from datetime import datetime, timezone

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

    async def _save_to_qdrant(self, recipe_id: str, parsed_recipe: Any, vectors: Any):
        """保存到 Qdrant."""
        from qdrant_client.http.models import PointStruct

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

    def _detect_cuisine(self, tags: list) -> Optional[str]:
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

    async def close(self):
        """关闭资源."""
        if self._db_session:
            await self._db_session.close()
        if self._es_service:
            await self._es_service.close()
        if self._qdrant_service:
            self._qdrant_service.close()
        if self._embedding_service:
            pass  # Embedding 服务无需关闭


async def run_import_pipeline(
    data_dir: str = "data/howtocook",
    full_import: bool = False,
) -> Dict[str, Any]:
    """
    运行导入流水线.

    Args:
        data_dir: 数据目录
        full_import: 是否全量导入

    Returns:
        导入结果
    """
    pipeline = ImportPipeline(data_dir=data_dir)
    try:
        result = await pipeline.run(full_import=full_import)
        return result
    finally:
        await pipeline.close()
