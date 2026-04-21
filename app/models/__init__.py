"""数据模型模块."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy  declarative base."""

    pass


from .user import User
from .recipe import Recipe
from .ingredient import RecipeIngredient
from .step import RecipeStep
from .favorite import Favorite
from .search_history import SearchHistory
from .report import Report
from .enterprise import Enterprise, EnterpriseUser

__all__ = ["Base", "User", "Recipe", "RecipeIngredient", "RecipeStep", "Favorite", "SearchHistory", "Report", "Enterprise", "EnterpriseUser"]
