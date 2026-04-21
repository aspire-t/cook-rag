"""Embedding 向量化服务 - 使用 BGE 模型生成多路向量."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np

from sentence_transformers import SentenceTransformer


@dataclass
class RecipeVectors:
    """菜谱多路向量."""
    name_vec: List[float]
    desc_vec: List[float]
    step_vec: List[float]
    tag_vec: List[float]


class EmbeddingService:
    """Embedding 向量化服务."""

    # BGE 模型名称
    MODEL_NAME = "BAAI/bge-large-zh-v1.5"

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        初始化 Embedding 服务.

        Args:
            model_name: 模型名称
            device: 运行设备 (cpu/cuda/mps)
        """
        self.model_name = model_name or self.MODEL_NAME
        self.device = self._detect_device(device)
        self.model: Optional[SentenceTransformer] = None

    def _detect_device(self, device: Optional[str]) -> str:
        """检测设备可用性."""
        if device:
            return device

        # 检测 MPS (Apple Silicon)
        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass

        # 检测 CUDA
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass

        return "cpu"

    def load_model(self):
        """加载模型."""
        if self.model is None:
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )

    def encode(self, text: str, normalize: bool = True) -> List[float]:
        """
        生成单文本向量.

        Args:
            text: 输入文本
            normalize: 是否归一化

        Returns:
            向量列表
        """
        if self.model is None:
            self.load_model()

        embedding = self.model.encode(
            [text],
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )[0]

        return embedding.tolist()

    def encode_batch(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
        """
        批量生成向量.

        Args:
            texts: 文本列表
            normalize: 是否归一化
            batch_size: 批次大小

        Returns:
            向量列表
        """
        if self.model is None:
            self.load_model()

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=True,
            batch_size=batch_size,
        )

        return embeddings.tolist()

    def generate_recipe_vectors(
        self,
        name: str,
        description: str,
        ingredients: List[str],
        steps: List[str],
        tags: List[str],
    ) -> RecipeVectors:
        """
        生成菜谱多路向量.

        Args:
            name: 菜名
            description: 描述
            ingredients: 食材列表
            steps: 步骤列表
            tags: 标签列表

        Returns:
            RecipeVectors 对象
        """
        if self.model is None:
            self.load_model()

        # 菜名向量
        name_vec = self.encode(name)

        # 描述 + 食材向量
        desc_text = f"{description} {' '.join(ingredients)}"
        desc_vec = self.encode(desc_text)

        # 步骤向量（合并所有步骤）
        step_text = " ".join(steps)
        step_vec = self.encode(step_text)

        # 标签向量
        tag_text = " ".join(tags)
        tag_vec = self.encode(tag_text) if tags else [0.0] * 1024

        return RecipeVectors(
            name_vec=name_vec,
            desc_vec=desc_vec,
            step_vec=step_vec,
            tag_vec=tag_vec,
        )


# 全局服务实例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取 Embedding 服务实例."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
