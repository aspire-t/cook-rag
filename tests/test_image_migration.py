"""测试图片 URL 迁移."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestBuildImageURL:
    """Test image URL builder."""

    def test_build_github_pages_url(self):
        from app.services.image_url_builder import build_image_url
        url = build_image_url("meat_dish/红烧肉.jpeg")
        assert url == "https://king-jingxiang.github.io/HowToCook/images/dishes/meat_dish/红烧肉.jpeg"

    def test_build_fallback_url(self):
        from app.services.image_url_builder import build_fallback_image_url
        url = build_fallback_image_url("vegetable_dish/炒青菜.jpeg")
        assert url == "/howtocook-images/dishes/vegetable_dish/炒青菜.jpeg"


class TestImageIndex:
    """Test local image index builder."""

    def test_index_finds_files(self):
        from scripts.migrate_images_to_howtocook import build_image_index
        index = build_image_index()
        assert len(index) > 0
        # Should contain known files
        assert "vegetable_dish/西红柿炒鸡蛋.jpeg" in index
        assert "meat_dish/红烧肉.jpeg" in index
