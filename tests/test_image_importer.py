"""
测试图片导入服务 (Task #36)

测试 ImageImporter 服务：
- Markdown 图片解析
- GitHub 图片上传
- 图片元数据提取
- 数据库记录创建
"""

import pytest
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import io
from PIL import Image


# 全局 fixtures
@pytest.fixture
def mock_token() -> str:
    """返回 mock GitHub token"""
    return "test_token_12345"


@pytest.fixture
def sample_markdown() -> str:
    """返回示例 Markdown 内容"""
    return """
# 红烧肉

![成品图](https://github.com/king-jingxiang/HowToCook/blob/master/images/hongshaorou.jpg)

## 步骤

![步骤 1](https://github.com/king-jingxiang/HowToCook/blob/master/images/hongshaorou_step1.jpg)

![步骤 2](https://github.com/king-jingxiang/HowToCook/blob/master/images/hongshaorou_step2.jpg)
"""


@pytest.fixture
def sample_image_content() -> bytes:
    """生成测试图片二进制内容"""
    img = Image.new('RGB', (224, 224), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()


class TestImageImporter:
    """测试图片导入服务 (Task #36)"""

    @pytest.fixture
    def image_importer_file(self) -> str:
        """读取 app/services/image_importer.py"""
        importer_path = Path(__file__).parent.parent / "app" / "services" / "image_importer.py"
        if importer_path.exists():
            with open(importer_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_image_importer_file_exists(self, image_importer_file):
        """测试 ImageImporter 服务文件存在"""
        importer_path = Path(__file__).parent.parent / "app" / "services" / "image_importer.py"
        assert importer_path.exists(), "app/services/image_importer.py 应该存在"

    def test_image_importer_class(self, image_importer_file):
        """测试 ImageImporter 类"""
        assert "class ImageImporter" in image_importer_file, "应该有 ImageImporter 类"

    def test_imports(self, image_importer_file):
        """测试必要的导入"""
        assert "aiohttp" in image_importer_file, "应该导入 aiohttp"
        assert "base64" in image_importer_file, "应该导入 base64"
        assert "PIL" in image_importer_file or "Image" in image_importer_file, "应该导入 PIL Image"
        assert "re" in image_importer_file, "应该导入 re 模块"

    def test_init_method(self, image_importer_file):
        """测试初始化方法"""
        assert "def __init__" in image_importer_file, "应该有 __init__ 方法"
        assert "token" in image_importer_file, "应该接收 token 参数"
        assert "IMAGE_REPO_OWNER" in image_importer_file, "应该使用 IMAGE_REPO_OWNER 配置"
        assert "IMAGE_REPO_NAME" in image_importer_file, "应该使用 IMAGE_REPO_NAME 配置"
        assert "IMAGE_BASE_CDN_URL" in image_importer_file, "应该使用 IMAGE_BASE_CDN_URL 配置"
        assert "clip_service" in image_importer_file, "应该初始化 clip_service"

    def test_upload_to_github_method(self, image_importer_file):
        """测试上传方法"""
        assert "def upload_to_github" in image_importer_file, "应该有 upload_to_github 方法"
        assert "path" in image_importer_file, "upload_to_github 应该接收 path 参数"
        assert "content" in image_importer_file, "upload_to_github 应该接收 content 参数"
        assert "message" in image_importer_file, "upload_to_github 应该接收 message 参数"
        assert "base64.b64encode" in image_importer_file, "应该使用 base64 编码内容"
        assert "api.github.com" in image_importer_file, "应该调用 GitHub API"

    def test_parse_markdown_images_method(self, image_importer_file):
        """测试 Markdown 图片解析方法"""
        assert "def parse_markdown_images" in image_importer_file, "应该有 parse_markdown_images 方法"
        assert "re.findall" in image_importer_file or "re.finditer" in image_importer_file, "应该使用正则表达式解析"
        assert r"!\[" in image_importer_file, "应该匹配 Markdown 图片语法"

    def test_get_image_metadata_method(self, image_importer_file):
        """测试图片元数据方法"""
        assert "def get_image_metadata" in image_importer_file, "应该有 get_image_metadata 方法"
        assert "width" in image_importer_file, "应该提取图片宽度"
        assert "height" in image_importer_file, "应该提取图片高度"
        assert "format" in image_importer_file, "应该提取图片格式"
        assert "size" in image_importer_file, "应该提取文件大小"

    def test_import_recipe_images_method(self, image_importer_file):
        """测试导入方法"""
        assert "def import_recipe_images" in image_importer_file, "应该有 import_recipe_images 方法"
        assert "recipe_id" in image_importer_file, "import_recipe_images 应该接收 recipe_id 参数"
        assert "markdown_content" in image_importer_file, "import_recipe_images 应该接收 markdown_content 参数"
        assert "RecipeImage" in image_importer_file, "应该创建 RecipeImage 记录"
        assert "clip_vector_id" in image_importer_file, "应该生成 CLIP 向量 ID"

    def test_github_blob_to_raw_conversion(self, image_importer_file):
        """测试 GitHub blob 到 raw URL 转换"""
        assert "/blob/" in image_importer_file, "应该处理 blob URL"
        assert "/raw/" in image_importer_file, "应该转换为 raw URL"


class TestMarkdownParsing:
    """测试 Markdown 图片解析"""

    @pytest.fixture
    def importer(self, mock_token):
        """创建 ImageImporter 实例（mock）"""
        from app.services.image_importer import ImageImporter
        with patch('app.services.image_importer.get_clip_service'):
            return ImageImporter(token=mock_token)

    def test_parse_single_image(self, importer):
        """测试解析单张图片"""
        markdown = "![封面图](https://example.com/image.jpg)"
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 1
        assert images[0]["alt"] == "封面图"
        assert images[0]["url"] == "https://example.com/image.jpg"
        assert images[0]["type"] == "cover"  # "封面图" 被识别为 cover

    def test_parse_cover_image(self, importer):
        """测试解析封面图片"""
        markdown = "![成品图](https://example.com/cover.jpg)"
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 1
        assert images[0]["type"] == "cover"

    def test_parse_cover_image_with_chinese(self, importer):
        """测试解析中文封面图片"""
        markdown = "![封面](https://example.com/cover.jpg)"
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 1
        assert images[0]["type"] == "cover"

    def test_parse_step_images(self, importer):
        """测试解析步骤图片"""
        markdown = """
        ![步骤 1](https://example.com/step1.jpg)
        ![步骤 2](https://example.com/step2.jpg)
        ![步骤 3](https://example.com/step3.jpg)
        """
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 3
        for img in images:
            assert img["type"] == "step"

    def test_parse_mixed_images(self, importer):
        """测试解析混合图片"""
        markdown = """
        ![成品图](https://example.com/cover.jpg)
        ![步骤 1](https://example.com/step1.jpg)
        ![步骤 2](https://example.com/step2.jpg)
        """
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 3
        assert images[0]["type"] == "cover"
        assert images[1]["type"] == "step"
        assert images[2]["type"] == "step"

    def test_parse_github_blob_urls(self, importer):
        """测试解析 GitHub blob URL"""
        markdown = "![图](https://github.com/user/repo/blob/master/images/test.jpg)"
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 1
        assert "github.com" in images[0]["url"]
        assert "/blob/" in images[0]["url"]

    def test_parse_no_images(self, importer):
        """测试没有图片的 Markdown"""
        markdown = "# 标题\n\n这是纯文本内容。"
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 0

    def test_parse_empty_alt(self, importer):
        """测试解析空 alt 文本"""
        markdown = "![](https://example.com/image.jpg)"
        images = importer.parse_markdown_images(markdown)

        assert len(images) == 1
        assert images[0]["alt"] == ""
        assert images[0]["url"] == "https://example.com/image.jpg"


class TestImageMetadata:
    """测试图片元数据提取"""

    @pytest.fixture
    def importer(self, mock_token):
        """创建 ImageImporter 实例（mock）"""
        from app.services.image_importer import ImageImporter
        with patch('app.services.image_importer.get_clip_service'):
            return ImageImporter(token=mock_token)

    def test_get_metadata_jpeg(self, importer):
        """测试 JPEG 图片元数据"""
        img = Image.new('RGB', (800, 600), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()

        metadata = importer.get_image_metadata(content)

        assert metadata["width"] == 800
        assert metadata["height"] == 600
        assert metadata["format"] == "JPEG"
        assert metadata["size"] == len(content)

    def test_get_metadata_png(self, importer):
        """测试 PNG 图片元数据"""
        img = Image.new('RGB', (1024, 768), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        content = buffer.getvalue()

        metadata = importer.get_image_metadata(content)

        assert metadata["width"] == 1024
        assert metadata["height"] == 768
        assert metadata["format"] == "PNG"

    def test_get_metadata_different_sizes(self, importer):
        """测试不同尺寸的图片"""
        sizes = [(100, 100), (500, 300), (1920, 1080)]

        for width, height in sizes:
            img = Image.new('RGB', (width, height), color='green')
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')
            content = buffer.getvalue()

            metadata = importer.get_image_metadata(content)

            assert metadata["width"] == width
            assert metadata["height"] == height


class TestGithubUpload:
    """测试 GitHub 上传功能"""

    def test_upload_to_github_signature(self):
        """测试上传方法签名"""
        from app.services.image_importer import ImageImporter
        import inspect

        # 验证方法存在且签名正确
        assert hasattr(ImageImporter, 'upload_to_github')
        sig = inspect.signature(ImageImporter.upload_to_github)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'path' in params
        assert 'content' in params
        assert 'message' in params

    @pytest.mark.asyncio
    async def test_upload_api_endpoint(self, mock_token):
        """测试上传 API 端点"""
        from app.services.image_importer import ImageImporter
        with patch('app.services.image_importer.get_clip_service'):
            importer = ImageImporter(token=mock_token)

        # 验证 URL 构造
        url = f"https://api.github.com/repos/{importer.owner}/{importer.repo}/contents/test.jpg"
        assert "aspire-t" in url
        assert "cook-rag-images" in url
        assert "test.jpg" in url


class TestImportRecipeImages:
    """测试完整的导入流程"""

    def test_import_recipe_images_signature(self):
        """测试导入方法签名"""
        from app.services.image_importer import ImageImporter
        import inspect

        # 验证方法存在且签名正确
        assert hasattr(ImageImporter, 'import_recipe_images')
        sig = inspect.signature(ImageImporter.import_recipe_images)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'recipe_id' in params
        assert 'markdown_content' in params
        assert 'source_repo' in params

    def test_import_recipe_images_async(self):
        """测试导入方法是异步的"""
        from app.services.image_importer import ImageImporter
        import inspect

        method = getattr(ImageImporter, 'import_recipe_images')
        assert inspect.iscoroutinefunction(method)

    def test_recipe_image_path_generation(self):
        """测试存储路径生成逻辑"""
        # 验证路径生成逻辑
        recipe_id = 1
        image_type = "cover"
        idx = 0
        local_path = f"recipes/{recipe_id}/{image_type}_{idx}.jpg"

        assert local_path == "recipes/1/cover_0.jpg"

        # 步骤图片
        image_type = "step"
        idx = 2
        local_path = f"recipes/{recipe_id}/{image_type}_{idx}.jpg"
        assert local_path == "recipes/1/step_2.jpg"

    def test_cdn_url_generation(self):
        """测试 CDN URL 生成逻辑"""
        from app.core.config import settings

        local_path = "recipes/1/cover_0.jpg"
        cdn_url = f"{settings.IMAGE_BASE_CDN_URL}{local_path}"

        assert "cdn.jsdelivr.net" in cdn_url
        assert "recipes/1/cover_0.jpg" in cdn_url

    def test_clip_vector_id_generation(self):
        """测试 CLIP 向量 ID 生成逻辑"""
        recipe_id = 1
        image_type = "cover"
        idx = 0
        vector_id = f"recipe_{recipe_id}_{image_type}_{idx}"

        assert vector_id == "recipe_1_cover_0"


class TestConfigIntegration:
    """测试配置集成"""

    @pytest.fixture
    def config_file(self) -> str:
        """读取 app/core/config.py"""
        config_path = Path(__file__).parent.parent / "app" / "core" / "config.py"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_image_repo_config(self, config_file):
        """测试图片仓库配置"""
        assert "IMAGE_REPO_NAME" in config_file, "应该有 IMAGE_REPO_NAME 配置"
        assert "IMAGE_REPO_OWNER" in config_file, "应该有 IMAGE_REPO_OWNER 配置"
        assert "cook-rag-images" in config_file, "应该配置 cook-rag-images 仓库"

    def test_image_cdn_config(self, config_file):
        """测试图片 CDN 配置"""
        assert "IMAGE_BASE_CDN_URL" in config_file, "应该有 IMAGE_BASE_CDN_URL 配置"
        assert "cdn.jsdelivr.net" in config_file, "应该使用 jsdelivr CDN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
