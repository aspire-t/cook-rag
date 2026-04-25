#!/usr/bin/env python3
"""插入测试数据的脚本 (SQLite 模式)."""

import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.user import User
from app.models.recipe import Recipe
from app.models.ingredient import RecipeIngredient
from app.models.step import RecipeStep


async def seed_data():
    engine = create_async_engine(
        "sqlite+aiosqlite:///./cookrag.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 检查是否已有数据
        result = await session.execute(select(Recipe))
        if result.scalars().first():
            print("测试数据已存在，跳过插入")
            return

        print("插入测试数据...")

        # 创建测试用户
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$placeholder_placeholder_placeholder_placeholder",
        )
        session.add(user)
        await session.commit()

        # 创建测试菜谱 1: 红烧肉
        recipe1 = Recipe(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="红烧肉",
            description="经典家常菜，肥而不腻，瘦而不柴",
            cuisine="川菜",
            difficulty="medium",
            prep_time=20,
            cook_time=60,
            servings=4,
            tags=["家常菜", "猪肉", "下饭菜"],
            is_public=True,
            user_id=user.id,
        )
        session.add(recipe1)
        await session.flush()

        ingredients1 = [
            RecipeIngredient(recipe_id=recipe1.id, name="五花肉", amount=500, unit="克", sequence=1),
            RecipeIngredient(recipe_id=recipe1.id, name="冰糖", amount=30, unit="克", sequence=2),
            RecipeIngredient(recipe_id=recipe1.id, name="料酒", amount=2, unit="勺", sequence=3),
            RecipeIngredient(recipe_id=recipe1.id, name="生抽", amount=2, unit="勺", sequence=4),
            RecipeIngredient(recipe_id=recipe1.id, name="老抽", amount=1, unit="勺", sequence=5),
            RecipeIngredient(recipe_id=recipe1.id, name="姜片", amount=5, unit="片", sequence=6),
            RecipeIngredient(recipe_id=recipe1.id, name="葱段", amount=2, unit="根", sequence=7),
            RecipeIngredient(recipe_id=recipe1.id, name="八角", amount=2, unit="个", sequence=8),
            RecipeIngredient(recipe_id=recipe1.id, name="桂皮", amount=1, unit="小块", sequence=9),
        ]
        for ing in ingredients1:
            session.add(ing)

        steps1 = [
            RecipeStep(recipe_id=recipe1.id, step_no=1, description="五花肉洗净，切成 3 厘米见方的块", duration_seconds=None),
            RecipeStep(recipe_id=recipe1.id, step_no=2, description="冷水下锅，加入料酒、姜片，焯水去腥", duration_seconds=180),
            RecipeStep(recipe_id=recipe1.id, step_no=3, description="锅中放少许油，加入冰糖小火炒至焦糖色", duration_seconds=120),
            RecipeStep(recipe_id=recipe1.id, step_no=4, description="放入焯好的五花肉翻炒上色", duration_seconds=60),
            RecipeStep(recipe_id=recipe1.id, step_no=5, description="加入生抽、老抽、八角、桂皮、葱段、姜片", duration_seconds=30),
            RecipeStep(recipe_id=recipe1.id, step_no=6, description="加入开水没过肉块，大火烧开转小火炖 40 分钟", duration_seconds=2400),
            RecipeStep(recipe_id=recipe1.id, step_no=7, description="大火收汁，出锅装盘", duration_seconds=120),
        ]
        for step in steps1:
            session.add(step)

        # 创建测试菜谱 2: 麻婆豆腐
        recipe2 = Recipe(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            name="麻婆豆腐",
            description="四川传统名菜，麻辣烫嫩",
            cuisine="川菜",
            difficulty="easy",
            prep_time=10,
            cook_time=15,
            servings=2,
            tags=["家常菜", "豆腐", "快手菜", "下饭菜"],
            is_public=True,
            user_id=user.id,
        )
        session.add(recipe2)
        await session.flush()

        ingredients2 = [
            RecipeIngredient(recipe_id=recipe2.id, name="嫩豆腐", amount=400, unit="克", sequence=1),
            RecipeIngredient(recipe_id=recipe2.id, name="猪肉末", amount=100, unit="克", sequence=2),
            RecipeIngredient(recipe_id=recipe2.id, name="豆瓣酱", amount=2, unit="勺", sequence=3),
            RecipeIngredient(recipe_id=recipe2.id, name="花椒粉", amount=1, unit="勺", sequence=4),
            RecipeIngredient(recipe_id=recipe2.id, name="辣椒粉", amount=1, unit="勺", sequence=5),
            RecipeIngredient(recipe_id=recipe2.id, name="蒜末", amount=1, unit="勺", sequence=6),
            RecipeIngredient(recipe_id=recipe2.id, name="姜末", amount=1, unit="勺", sequence=7),
            RecipeIngredient(recipe_id=recipe2.id, name="葱花", amount=2, unit="勺", sequence=8),
        ]
        for ing in ingredients2:
            session.add(ing)

        steps2 = [
            RecipeStep(recipe_id=recipe2.id, step_no=1, description="豆腐切成小块，开水焯烫去豆腥味", duration_seconds=60),
            RecipeStep(recipe_id=recipe2.id, step_no=2, description="热锅凉油，放入肉末炒散至变色", duration_seconds=120),
            RecipeStep(recipe_id=recipe2.id, step_no=3, description="加入豆瓣酱炒出红油", duration_seconds=60),
            RecipeStep(recipe_id=recipe2.id, step_no=4, description="加入姜蒜末炒香", duration_seconds=30),
            RecipeStep(recipe_id=recipe2.id, step_no=5, description="加入适量清水烧开", duration_seconds=60),
            RecipeStep(recipe_id=recipe2.id, step_no=6, description="放入豆腐块，轻轻推动，煮 3 分钟", duration_seconds=180),
            RecipeStep(recipe_id=recipe2.id, step_no=7, description="加入辣椒粉、花椒粉，轻轻推动", duration_seconds=30),
            RecipeStep(recipe_id=recipe2.id, step_no=8, description="撒上葱花，出锅", duration_seconds=10),
        ]
        for step in steps2:
            session.add(step)

        # 创建测试菜谱 3: 番茄炒蛋
        recipe3 = Recipe(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            name="番茄炒蛋",
            description="国民家常菜，酸甜可口",
            cuisine="家常菜",
            difficulty="easy",
            prep_time=5,
            cook_time=10,
            servings=2,
            tags=["家常菜", "快手菜", "鸡蛋", "素食"],
            is_public=True,
            user_id=user.id,
        )
        session.add(recipe3)
        await session.flush()

        ingredients3 = [
            RecipeIngredient(recipe_id=recipe3.id, name="鸡蛋", amount=4, unit="个", sequence=1),
            RecipeIngredient(recipe_id=recipe3.id, name="番茄", amount=3, unit="个", sequence=2),
            RecipeIngredient(recipe_id=recipe3.id, name="白糖", amount=1, unit="勺", sequence=3),
            RecipeIngredient(recipe_id=recipe3.id, name="盐", amount=0.5, unit="勺", sequence=4),
            RecipeIngredient(recipe_id=recipe3.id, name="葱花", amount=1, unit="勺", sequence=5),
        ]
        for ing in ingredients3:
            session.add(ing)

        steps3 = [
            RecipeStep(recipe_id=recipe3.id, step_no=1, description="番茄洗净切块，鸡蛋打散加少许盐", duration_seconds=120),
            RecipeStep(recipe_id=recipe3.id, step_no=2, description="热锅多油，倒入蛋液炒至金黄蓬松盛出", duration_seconds=60),
            RecipeStep(recipe_id=recipe3.id, step_no=3, description="锅中留底油，放入番茄块翻炒", duration_seconds=60),
            RecipeStep(recipe_id=recipe3.id, step_no=4, description="加入白糖、盐调味，炒出番茄汁", duration_seconds=120),
            RecipeStep(recipe_id=recipe3.id, step_no=5, description="倒入炒好的鸡蛋，快速翻炒均匀", duration_seconds=30),
            RecipeStep(recipe_id=recipe3.id, step_no=6, description="撒上葱花，出锅", duration_seconds=10),
        ]
        for step in steps3:
            session.add(step)

        await session.commit()
        print("测试数据插入完成!")
        print(f"  - 用户：{user.username}")
        print(f"  - 菜谱 1: {recipe1.name}")
        print(f"  - 菜谱 2: {recipe2.name}")
        print(f"  - 菜谱 3: {recipe3.name}")


if __name__ == "__main__":
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./cookrag.db"
    asyncio.run(seed_data())
