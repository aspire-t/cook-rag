"""B 端标准化配方生成服务."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.standard_recipe import StandardRecipe
from app.models.recipe import Recipe
from app.models.enterprise import EnterpriseUser
from app.services.llm_service import LLMService

# 标准化配方生成 Prompt
B_STANDARDIZE_PROMPT = """
# Role
你是一位餐饮行业标准化专家，拥有 10 年以上中央厨房和连锁餐饮管理经验。
你的任务是将家庭菜谱转化为可工业化生产的标准化配方。

# Input
菜谱名称：{recipe_name}
菜系：{cuisine}
难度：{difficulty}
准备时间：{prep_time}分钟
烹饪时间：{cook_time}分钟
 servings: {servings}人份

## 食材
{ingredients}

## 步骤
{steps}

# Output Requirements
请严格按照以下 JSON 格式输出：

```json
{{
    "sop": {{
        "ingredients_table": [
            {{"ingredient": "鸡胸肉", "spec": "去骨去皮", "amount_g": 500.0, "tolerance_g": 5, "note": "新鲜/冷冻均可"}}
        ],
        "procedures": [
            {{
                "step_num": 1,
                "title": "食材预处理",
                "duration_min": 5,
                "operation": "鸡胸肉切成 2cm 见方的丁",
                "critical_control_point": "大小均匀，确保熟度一致",
                "quality_check": "随机抽取 10 块，重量差异<10%"
            }}
        ]
    }},
    "cost_calculation": {{
        "ingredients": [
            {{"ingredient": "鸡胸肉", "unit_price_kg": 18.0, "amount_g": 500, "cost": 9.0}}
        ],
        "total_cost": 15.5,
        "suggested_price": 45.0,
        "gross_margin": 65.5
    }},
    "nutrition_info": {{
        "per_100g": {{
            "energy_kcal": 180,
            "protein_g": 22.5,
            "fat_g": 8.2,
            "carbohydrate_g": 5.6,
            "sodium_mg": 450
        }}
    }},
    "allergen_info": {{
        "contains": ["花生"],
        "may_contain": ["大豆"]
    }},
    "shelf_life": {{
        "days": 1,
        "storage_temp": "0-4°C 冷藏",
        "frozen_days": 30,
        "frozen_temp": "-18°C"
    }}
}}
```
"""


class StandardizeService:
    """标准化配方生成服务."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()

    async def generate_standard_recipe(
        self,
        recipe_id: str,
        enterprise_id: str,
        created_by: str,
    ) -> StandardRecipe:
        """
        生成标准化配方.

        Args:
            recipe_id: 菜谱 ID
            enterprise_id: 企业 ID
            created_by: 创建人 ID

        Returns:
            StandardRecipe: 标准化配方对象
        """
        # 获取菜谱详情
        result = await self.db.execute(
            select(Recipe)
            .where(Recipe.id == recipe_id)
        )
        recipe = result.scalar_one_or_none()
        if not recipe:
            raise ValueError(f"菜谱不存在：{recipe_id}")

        # 获取食材列表
        ingredients_result = await self.db.execute(
            select(RecipeIngredient)
            .where(RecipeIngredient.recipe_id == recipe_id)
            .order_by(RecipeIngredient.order_index)
        )
        ingredients = ingredients_result.scalars().all()

        # 获取步骤列表
        steps_result = await self.db.execute(
            select(RecipeStep)
            .where(RecipeStep.recipe_id == recipe_id)
            .order_by(RecipeStep.step_number)
        )
        steps = steps_result.scalars().all()

        # 构建 Prompt 输入
        ingredients_text = "\n".join(
            f"- {ing.ingredient_name}: {ing.amount} {ing.unit}"
            for ing in ingredients
        )
        steps_text = "\n".join(
            f"{step.step_number}. {step.description}"
            for step in steps
        )

        prompt = B_STANDARDIZE_PROMPT.format(
            recipe_name=recipe.name,
            cuisine=recipe.cuisine or "未分类",
            difficulty=recipe.difficulty or "medium",
            prep_time=recipe.prep_time or 0,
            cook_time=recipe.cook_time or 0,
            servings=recipe.servings or 1,
            ingredients=ingredients_text,
            steps=steps_text,
        )

        # 调用 LLM 生成标准化配方
        response = await self.llm_service.generate(prompt, temperature=0.3)

        # 解析 LLM 响应
        standard_data = self._parse_llm_response(response)

        # 旧版本设为非最新
        await self._deprecate_old_versions(recipe_id, enterprise_id)

        # 创建标准化配方记录
        standard_recipe = StandardRecipe(
            id=str(uuid.uuid4()),
            recipe_id=recipe_id,
            enterprise_id=enterprise_id,
            sop_content=json.dumps(standard_data.get("sop", {}), ensure_ascii=False),
            cost_calculation=json.dumps(standard_data.get("cost_calculation", {}), ensure_ascii=False),
            total_cost=standard_data.get("cost_calculation", {}).get("total_cost"),
            suggested_price=standard_data.get("cost_calculation", {}).get("suggested_price"),
            gross_margin=standard_data.get("cost_calculation", {}).get("gross_margin"),
            nutrition_info=json.dumps(standard_data.get("nutrition_info", {}), ensure_ascii=False),
            allergen_info=json.dumps(standard_data.get("allergen_info", {}), ensure_ascii=False),
            shelf_life_days=standard_data.get("shelf_life", {}).get("days"),
            storage_temperature=standard_data.get("shelf_life", {}).get("storage_temp"),
            version=1,
            is_latest=True,
            created_by=created_by,
        )

        self.db.add(standard_recipe)
        await self.db.flush()

        return standard_recipe

    def _parse_llm_response(self, response: str) -> dict:
        """解析 LLM 响应."""
        try:
            # 尝试提取 JSON 代码块
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except Exception as e:
            # 返回默认结构
            return {
                "sop": {"ingredients_table": [], "procedures": []},
                "cost_calculation": {"total_cost": 0, "suggested_price": 0, "gross_margin": 0},
                "nutrition_info": {"per_100g": {}},
                "allergen_info": {"contains": [], "may_contain": []},
                "shelf_life": {"days": 1, "storage_temp": "0-4°C"},
            }

    async def _deprecate_old_versions(self, recipe_id: str, enterprise_id: str):
        """将旧版本设为非最新."""
        result = await self.db.execute(
            select(StandardRecipe).where(
                StandardRecipe.recipe_id == recipe_id,
                StandardRecipe.enterprise_id == enterprise_id,
                StandardRecipe.is_latest,
            )
        )
        old_versions = result.scalars().all()
        for old_version in old_versions:
            old_version.is_latest = False

    async def get_latest_standard_recipe(
        self,
        recipe_id: str,
        enterprise_id: str,
    ) -> Optional[StandardRecipe]:
        """获取最新版本的标准化配方."""
        result = await self.db.execute(
            select(StandardRecipe).where(
                StandardRecipe.recipe_id == recipe_id,
                StandardRecipe.enterprise_id == enterprise_id,
                StandardRecipe.is_latest,
            )
        )
        return result.scalar_one_or_none()

    async def check_enterprise_permission(
        self,
        enterprise_id: str,
        user_id: str,
    ) -> bool:
        """检查用户是否属于该企业."""
        result = await self.db.execute(
            select(EnterpriseUser).where(
                EnterpriseUser.enterprise_id == enterprise_id,
                EnterpriseUser.user_id == user_id,
                EnterpriseUser.is_active,
            )
        )
        return result.scalar_one_or_none() is not None
