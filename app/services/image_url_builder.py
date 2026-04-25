"""图片 URL 构建 — 优先 HowToCook GitHub Pages CDN，回退本地静态文件."""

from app.core.config import settings


def build_image_url(source_path: str) -> str:
    """根据 source_path 构建图片 URL.

    Args:
        source_path: 如 "meat_dish/红烧肉.jpeg"

    Returns:
        GitHub Pages CDN URL
    """
    return f"{settings.HOWTOCOOK_IMAGE_BASE_URL}{source_path}"


def build_fallback_image_url(source_path: str) -> str:
    """构建本地回退 URL（当 CDN 不可用时）."""
    return settings.IMAGE_FALLBACK_BASE + source_path
