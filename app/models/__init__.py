"""数据模型模块."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy  declarative base."""

    pass


# 按依赖顺序导入：基础模型 -> 依赖模型 -> 关联模型
# 第一层：基础模型（无外键依赖）
from .user import User
from .enterprise import Enterprise, EnterpriseUser

# 第二层：菜谱主表（依赖 User）
from .recipe import Recipe

# 第三层：菜谱子项（依赖 Recipe）
from .ingredient import RecipeIngredient
from .step import RecipeStep

# 第四层：关联模型（依赖 Recipe + User）
from .favorite import Favorite
from .search_history import SearchHistory
from .report import Report

# 第五层：B 端模型（依赖 Recipe + Enterprise）
from .standard_recipe import StandardRecipe

# 第六层：企业资源管理（依赖 Enterprise）
from .inventory import Inventory, InventoryTransaction
from .supplier import Supplier
from .purchase_order import PurchaseOrder

__all__ = [
    "Base",
    "User",
    "Enterprise",
    "EnterpriseUser",
    "Recipe",
    "RecipeIngredient",
    "RecipeStep",
    "Favorite",
    "SearchHistory",
    "Report",
    "StandardRecipe",
    "Inventory",
    "InventoryTransaction",
    "Supplier",
    "PurchaseOrder",
]
