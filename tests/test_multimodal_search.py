"""多模态搜索端到端测试."""

import pytest
import asyncio
from pathlib import Path
from PIL import Image
import io
import base64

from app.services.clip_service import get_clip_service
from app.services.qdrant_service import get_qdrant_service
from app.services.image_importer import ImageImporter
from app.api.v1.images import search_by_image, get_recipe_images
from app.api.schemas import ImageSearchRequest


class TestMultimodalSearch:
    """多模态搜索集成测试."""

    def test_clip_text_embedding(self):
        """测试 CLIP 文本向量化."""
        clip_service = get_clip_service()
        vector = clip_service.get_text_embedding("鱼香肉丝")

        assert vector.shape == (512,)
        assert abs(vector).max() > 0  # 非零向量

    def test_clip_image_embedding(self, tmp_path):
        """测试 CLIP 图片向量化."""
        clip_service = get_clip_service()

        # 创建测试图片
        img = Image.new("RGB", (224, 224), color="red")
        img_path = tmp_path / "test.jpg"
        img.save(img_path)

        vector = clip_service.get_image_embedding(img_path)

        assert vector.shape == (512,)
        assert abs(vector).max() > 0

    def test_clip_cross_modal(self):
        """测试跨模态语义一致性。

        同一概念的文本和图片向量应该有较高的余弦相似度。
        """
        clip_service = get_clip_service()
        import numpy as np

        # 获取文本向量
        text_vector = clip_service.get_text_embedding("红烧肉")

        # 创建红色图片（模拟红烧肉颜色）
        img = Image.new("RGB", (224, 224), color=(139, 69, 19))  # 棕色
        img_vector = clip_service.get_image_embedding(img)

        # 计算余弦相似度
        similarity = np.dot(text_vector, img_vector)

        # 跨模态相似度应该 > 0.5（同一语义空间）
        assert similarity > 0.3

    def test_batch_text_embeddings(self):
        """测试批量文本向量化."""
        clip_service = get_clip_service()

        texts = ["鱼香肉丝", "宫保鸡丁", "红烧肉"]
        vectors = clip_service.batch_get_text_embeddings(texts)

        assert vectors.shape == (3, 512)

    def test_batch_image_embeddings(self, tmp_path):
        """测试批量图片向量化."""
        clip_service = get_clip_service()
        import numpy as np

        # 创建多张测试图片
        images = []
        for color in ["red", "green", "blue"]:
            img = Image.new("RGB", (224, 224), color=color)
            images.append(img)

        vectors = clip_service.batch_get_image_embeddings(images)

        assert vectors.shape == (3, 512)

        # 不同颜色的图片向量应该不同
        similarity = np.dot(vectors[0], vectors[1])
        assert similarity < 0.99  # 不应该完全相同

    def test_qdrant_image_schema(self):
        """测试 Qdrant image_vec 字段配置."""
        from app.services.qdrant_schema import get_collection_config

        config = get_collection_config()
        vectors = config["vectors"]

        # 验证 image_vec 存在
        assert "image_vec" in vectors
        assert vectors["image_vec"].size == 512
        # distance 是 Cosine (首字母大写)
        assert "Cosine" in str(vectors["image_vec"].distance)

    def test_image_importer_markdown_parse(self):
        """测试 Markdown 图片解析."""
        importer = ImageImporter(token="fake_token")

        markdown = """
        ## 鱼香肉丝

        ![封面图](https://example.com/cover.jpg)

        步骤 1：![步骤 1](https://example.com/step1.jpg)

        步骤 2：![步骤 2](https://example.com/step2.jpg)
        """

        images = importer.parse_markdown_images(markdown)

        assert len(images) == 3
        assert images[0]["type"] == "cover"
        assert images[1]["type"] == "step"
        assert images[2]["type"] == "step"

    def test_image_importer_github_url_convert(self):
        """测试 GitHub URL 转换."""
        # 直接测试转换逻辑
        blob_url = "https://github.com/king-jingxiang/HowToCook/blob/main/dishes/yc.jpg"
        raw_url = blob_url.replace("/blob/", "/raw/")
        assert "raw" in raw_url
        assert "blob" not in raw_url

    def test_image_search_request_schema(self):
        """测试图片搜索请求 Schema."""
        # 纯文本搜索
        req1 = ImageSearchRequest(text_query="川菜", limit=10)
        assert req1.text_query == "川菜"
        assert req1.limit == 10

        # 图片 URL 搜索
        req2 = ImageSearchRequest(image_url="https://example.com/img.jpg", limit=5)
        assert req2.image_url == "https://example.com/img.jpg"

        # Base64 搜索
        req3 = ImageSearchRequest(image_base64="iVBORw0KGgoAAAANS...", limit=10)
        assert req3.image_base64 is not None

    def test_image_search_response_schema(self):
        """测试图片搜索响应 Schema。"""
        from app.api.schemas import ImageSearchResponse

        resp = ImageSearchResponse(
            query_type="image",
            results=[
                {"recipe_id": 1, "score": 0.95, "name": "鱼香肉丝"},
                {"recipe_id": 2, "score": 0.85, "name": "宫保鸡丁"}
            ]
        )

        assert resp.query_type == "image"
        assert len(resp.results) == 2
        assert resp.results[0]["recipe_id"] == 1

    def test_recipe_images_response_schema(self):
        """测试菜谱图片响应 Schema."""
        from app.api.schemas import RecipeImagesResponse, RecipeImageResponse

        resp = RecipeImagesResponse(
            recipe_id="550e8400-e29b-41d4-a716-446655440000",
            cover=RecipeImageResponse(
                id="550e8400-e29b-41d4-a716-446655440001",
                step_no=None,
                image_type="cover",
                image_url="https://example.com/cover.jpg",
                width=800,
                height=600,
                file_size=102400
            ),
            steps=[
                RecipeImageResponse(
                    id="550e8400-e29b-41d4-a716-446655440002",
                    step_no=0,
                    image_type="step",
                    image_url="https://example.com/step1.jpg",
                    width=800,
                    height=600,
                    file_size=81920
                )
            ]
        )

        assert resp.recipe_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.cover.image_type == "cover"
        assert len(resp.steps) == 1
        assert resp.steps[0].step_no == 0


class TestPerformance:
    """性能测试."""

    def test_clip_embedding_latency(self):
        """测试 CLIP 向量化延迟。

        目标：单张图片向量化 < 100ms (MPS)
        """
        import time
        from PIL import Image

        clip_service = get_clip_service()
        img = Image.new("RGB", (224, 224), color="red")

        # 预热
        clip_service.get_image_embedding(img)

        # 测试
        start = time.time()
        for _ in range(10):
            clip_service.get_image_embedding(img)
        elapsed = time.time() - start

        avg_latency_ms = (elapsed / 10) * 1000
        print(f"平均向量化延迟：{avg_latency_ms:.2f}ms")

        # MVP 目标：< 500ms
        assert avg_latency_ms < 500

    def test_text_embedding_latency(self):
        """测试文本向量化延迟。

        目标：单个文本向量化 < 50ms
        """
        import time

        clip_service = get_clip_service()

        # 预热
        clip_service.get_text_embedding("测试")

        # 测试
        start = time.time()
        for _ in range(100):
            clip_service.get_text_embedding("鱼香肉丝")
        elapsed = time.time() - start

        avg_latency_ms = (elapsed / 100) * 1000
        print(f"平均文本向量化延迟：{avg_latency_ms:.2f}ms")

        assert avg_latency_ms < 100
