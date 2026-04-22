"""数据模型模块."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy  declarative base."""

    pass


# 按依赖顺序导入：基础模型 -> 依赖模型 -> 关联模型
# 第一层：基础模型（无外键依赖）
from .user import User

# 第二层：菜谱主表（依赖 User）
from .recipe import Recipe

# 第三层：菜谱子项（依赖 Recipe）
from .ingredient import RecipeIngredient
from .step import RecipeStep

# 第四层：关联模型（依赖 Recipe + User）
from .favorite import Favorite
from .search_history import SearchHistory
from .report import Report
from .recipe_image import RecipeImage

__all__ = [
    "Base",
    "User",
    "Recipe",
    "RecipeIngredient",
    "RecipeStep",
    "Favorite",
    "SearchHistory",
    "Report",
    "RecipeImage",
]
