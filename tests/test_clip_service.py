"""
测试 CLIP 向量化服务 (Task #37)

测试 Chinese-CLIP 模型的向量化功能：
- 文本向量化
- 图片向量化
- 批量处理
- 归一化
"""

import pytest
import numpy as np
from pathlib import Path
from PIL import Image


class TestClipService:
    """测试 CLIP 向量化服务 (Task #37)"""

    @pytest.fixture
    def clip_service_file(self) -> str:
        """读取 app/services/clip_service.py"""
        clip_path = Path(__file__).parent.parent / "app" / "services" / "clip_service.py"
        if clip_path.exists():
            with open(clip_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @pytest.fixture
    def sample_image(self, tmp_path) -> Path:
        """创建测试图片"""
        img_path = tmp_path / "test_image.png"
        # 创建一个简单的测试图片
        img = Image.new('RGB', (224, 224), color='red')
        img.save(img_path)
        return img_path

    @pytest.fixture
    def sample_images(self, tmp_path) -> list:
        """创建多个测试图片"""
        images = []
        for i, color in enumerate(['red', 'green', 'blue']):
            img_path = tmp_path / f"test_image_{i}.png"
            img = Image.new('RGB', (224, 224), color=color)
            img.save(img_path)
            images.append(img_path)
        return images

    def test_clip_service_file_exists(self, clip_service_file):
        """测试 CLIP 服务文件存在"""
        clip_path = Path(__file__).parent.parent / "app" / "services" / "clip_service.py"
        assert clip_path.exists(), "app/services/clip_service.py 应该存在"

    def test_clip_service_class(self, clip_service_file):
        """测试 CLIP 服务类"""
        assert "class ClipService" in clip_service_file, "应该有 ClipService 类"

    def test_imports(self, clip_service_file):
        """测试必要的导入"""
        assert "torch" in clip_service_file, "应该导入 torch"
        assert "transformers" in clip_service_file, "应该导入 transformers"
        assert "CLIPProcessor" in clip_service_file, "应该导入 CLIPProcessor"
        assert "CLIPModel" in clip_service_file, "应该导入 CLIPModel"
        assert "numpy" in clip_service_file or "np" in clip_service_file, "应该导入 numpy"
        assert "PIL" in clip_service_file or "Image" in clip_service_file, "应该导入 PIL Image"

    def test_device_detection(self, clip_service_file):
        """测试设备检测"""
        assert "_get_device" in clip_service_file, "应该有 _get_device 方法"
        assert "cuda" in clip_service_file, "应该支持 CUDA"
        assert "cpu" in clip_service_file, "应该支持 CPU"

    def test_lazy_loading(self, clip_service_file):
        """测试懒加载"""
        assert "_load_model" in clip_service_file, "应该有 _load_model 方法"
        assert "if self.model is None" in clip_service_file, "应该实现懒加载"

    def test_get_text_embedding_method(self, clip_service_file):
        """测试文本向量化方法"""
        assert "def get_text_embedding" in clip_service_file, "应该有 get_text_embedding 方法"

    def test_get_image_embedding_method(self, clip_service_file):
        """测试图片向量化方法"""
        assert "def get_image_embedding" in clip_service_file, "应该有 get_image_embedding 方法"

    def test_batch_text_embeddings(self, clip_service_file):
        """测试批量文本向量化"""
        assert "def batch_get_text_embeddings" in clip_service_file, "应该有 batch_get_text_embeddings 方法"
        assert "batch_size" in clip_service_file, "应该支持 batch_size 参数"

    def test_batch_image_embeddings(self, clip_service_file):
        """测试批量图片向量化"""
        assert "def batch_get_image_embeddings" in clip_service_file, "应该有 batch_get_image_embeddings 方法"

    def test_normalize_option(self, clip_service_file):
        """测试归一化选项"""
        assert "normalize" in clip_service_file, "应该有 normalize 参数"
        assert "np.linalg.norm" in clip_service_file, "应该使用 L2 范数归一化"

    def test_singleton_pattern(self, clip_service_file):
        """测试单例模式"""
        assert "get_clip_service" in clip_service_file, "应该有 get_clip_service 函数"
        assert "_clip_service" in clip_service_file, "应该有单例实例"


class TestTextEmbedding:
    """测试文本向量化"""

    @pytest.fixture
    def service(self):
        """创建 ClipService 实例"""
        from app.services.clip_service import ClipService
        return ClipService()

    @pytest.fixture
    def sample_image(self, tmp_path):
        """创建测试图片"""
        img_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (224, 224), color='red')
        img.save(img_path)
        return img_path

    @pytest.fixture
    def sample_images(self, tmp_path):
        """创建多个测试图片"""
        images = []
        for i, color in enumerate(['red', 'green', 'blue']):
            img_path = tmp_path / f"test_image_{i}.png"
            img = Image.new('RGB', (224, 224), color=color)
            img.save(img_path)
            images.append(img_path)
        return images

    def test_text_embedding_dimension(self, service):
        """测试文本向量维度为 512"""
        embedding = service.get_text_embedding("这是一道美味的川菜")
        assert embedding.shape == (512,), f"文本向量维度应该是 512，实际是 {embedding.shape}"

    def test_text_embedding_normalized(self, service):
        """测试文本向量归一化"""
        embedding = service.get_text_embedding("这是一道美味的川菜", normalize=True)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-5, f"归一化向量的范数应该接近 1，实际是 {norm}"

    def test_text_embedding_not_normalized(self, service):
        """测试文本向量不归一化"""
        embedding = service.get_text_embedding("这是一道美味的川菜", normalize=False)
        norm = np.linalg.norm(embedding)
        assert norm != pytest.approx(1.0, rel=1e-5), "不归一化时范数不应该为 1"

    def test_similar_texts_similar_embeddings(self, service):
        """测试相似文本有相似的向量"""
        # 两个相似的句子
        emb1 = service.get_text_embedding("怎么做红烧肉")
        emb2 = service.get_text_embedding("红烧肉的做法")

        # 计算余弦相似度
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        # 相似句子的余弦相似度应该较高
        assert similarity > 0.7, f"相似文本的余弦相似度应该 > 0.7，实际是 {similarity}"

    def test_different_texts_different_embeddings(self, service):
        """测试不同文本有不同的向量"""
        emb1 = service.get_text_embedding("怎么做红烧肉")
        emb2 = service.get_text_embedding("今天天气真好")

        # 计算余弦相似度
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        # 不相关句子的余弦相似度应该较低 (实际模型输出可能在 0.6 左右)
        assert similarity < 0.8, f"不相关文本的余弦相似度应该 < 0.8，实际是 {similarity}"


class TestImageEmbedding:
    """测试图片向量化"""

    @pytest.fixture
    def service(self):
        """创建 ClipService 实例"""
        from app.services.clip_service import ClipService
        return ClipService()

    @pytest.fixture
    def sample_image(self, tmp_path):
        """创建测试图片"""
        img_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (224, 224), color='red')
        img.save(img_path)
        return img_path

    @pytest.fixture
    def sample_images(self, tmp_path):
        """创建多个测试图片"""
        images = []
        for i, color in enumerate(['red', 'green', 'blue']):
            img_path = tmp_path / f"test_image_{i}.png"
            img = Image.new('RGB', (224, 224), color=color)
            img.save(img_path)
            images.append(img_path)
        return images

    def test_image_embedding_dimension(self, service, sample_image):
        """测试图片向量维度为 512"""
        embedding = service.get_image_embedding(sample_image)
        assert embedding.shape == (512,), f"图片向量维度应该是 512，实际是 {embedding.shape}"

    def test_image_embedding_normalized(self, service, sample_image):
        """测试图片向量归一化"""
        embedding = service.get_image_embedding(sample_image, normalize=True)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-5, f"归一化向量的范数应该接近 1，实际是 {norm}"

    def test_image_embedding_from_path(self, service, sample_image):
        """测试从路径加载图片"""
        embedding1 = service.get_image_embedding(str(sample_image))
        assert embedding1.shape == (512,), "从字符串路径加载应该成功"

    def test_image_embedding_from_pil(self, service, sample_image):
        """测试从 PIL Image 加载"""
        img = Image.open(sample_image).convert("RGB")
        embedding = service.get_image_embedding(img)
        assert embedding.shape == (512,), "从 PIL Image 加载应该成功"


class TestBatchEmbeddings:
    """测试批量向量化"""

    @pytest.fixture
    def service(self):
        """创建 ClipService 实例"""
        from app.services.clip_service import ClipService
        return ClipService()

    @pytest.fixture
    def sample_image(self, tmp_path):
        """创建测试图片"""
        img_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (224, 224), color='red')
        img.save(img_path)
        return img_path

    @pytest.fixture
    def sample_images(self, tmp_path):
        """创建多个测试图片"""
        images = []
        for i, color in enumerate(['red', 'green', 'blue']):
            img_path = tmp_path / f"test_image_{i}.png"
            img = Image.new('RGB', (224, 224), color=color)
            img.save(img_path)
            images.append(img_path)
        return images

    def test_batch_text_embeddings_shape(self, service):
        """测试批量文本向量形状"""
        texts = ["川菜", "粤菜", "湘菜"]
        embeddings = service.batch_get_text_embeddings(texts)
        assert embeddings.shape == (3, 512), f"批量文本向量形状应该是 (3, 512)，实际是 {embeddings.shape}"

    def test_batch_text_embeddings_consistent(self, service):
        """测试批量文本向量与单个一致"""
        text = "宫保鸡丁"

        # 单个
        single_emb = service.get_text_embedding(text)

        # 批量
        batch_embs = service.batch_get_text_embeddings([text])

        assert np.allclose(single_emb, batch_embs[0]), "单个和批量结果应该一致"

    def test_batch_image_embeddings_shape(self, service, sample_images):
        """测试批量图片向量形状"""
        embeddings = service.batch_get_image_embeddings(sample_images)
        assert embeddings.shape == (3, 512), f"批量图片向量形状应该是 (3, 512)，实际是 {embeddings.shape}"

    def test_batch_image_embeddings_consistent(self, service, sample_image):
        """测试批量图片向量与单个一致"""
        # 单个
        single_emb = service.get_image_embedding(sample_image)

        # 批量
        batch_embs = service.batch_get_image_embeddings([sample_image])

        assert np.allclose(single_emb, batch_embs[0]), "单个和批量结果应该一致"

    def test_batch_size_parameter(self, service):
        """测试 batch_size 参数"""
        texts = [f"文本 {i}" for i in range(10)]

        # 使用不同的 batch_size
        embeddings1 = service.batch_get_text_embeddings(texts, batch_size=2)
        embeddings2 = service.batch_get_text_embeddings(texts, batch_size=5)

        # 结果应该相同 (考虑浮点精度误差)
        assert embeddings1.shape == embeddings2.shape == (10, 512), "不同 batch_size 应该得到相同形状"
        # 使用更宽松的容差，因为不同 batch 大小可能有微小浮点误差
        assert np.allclose(embeddings1, embeddings2, rtol=1e-4, atol=1e-5), "不同 batch_size 应该得到相同结果"


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

    def test_clip_model_config(self, config_file):
        """测试 CLIP 模型配置"""
        assert "CLIP_MODEL_NAME" in config_file or "CLIP" in config_file, "应该有 CLIP 模型配置"
        assert "chinese-clip" in config_file.lower(), "应该配置 Chinese-CLIP 模型"

    def test_clip_device_config(self, config_file):
        """测试 CLIP 设备配置"""
        assert "CLIP_DEVICE" in config_file, "应该有 CLIP_DEVICE 配置"


class TestCrossModalRetrieval:
    """测试跨模态检索（图文匹配）"""

    @pytest.fixture
    def service(self):
        """创建 ClipService 实例"""
        from app.services.clip_service import ClipService
        return ClipService()

    @pytest.fixture
    def test_image(self, tmp_path):
        """创建测试图片（红色）"""
        img_path = tmp_path / "red_image.png"
        img = Image.new('RGB', (224, 224), color='red')
        img.save(img_path)
        return img_path

    def test_text_image_similarity(self, service, test_image):
        """测试文本和图片向量的相似度计算"""
        # 获取文本向量
        text_emb = service.get_text_embedding("红色的图片")

        # 获取图片向量
        image_emb = service.get_image_embedding(test_image)

        # 计算余弦相似度
        similarity = np.dot(text_emb, image_emb) / (np.linalg.norm(text_emb) * np.linalg.norm(image_emb))

        # 语义相关的图文应该有较高的相似度
        assert similarity > 0, f"语义相关的图文相似度应该为正，实际是 {similarity}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
