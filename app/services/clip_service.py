"""CLIP 向量化服务 - Chinese-CLIP."""

import torch
from PIL import Image
from transformers import ChineseCLIPProcessor, ChineseCLIPModel
from typing import List, Union, Optional
from pathlib import Path
import numpy as np

from app.core.config import settings


class ClipService:
    """Chinese-CLIP 向量化服务。

    支持：
    - 图片向量化
    - 文本向量化
    - 批量处理
    """

    def __init__(self):
        self.model_name = settings.CLIP_MODEL_NAME
        self.device = self._get_device()
        self.model = None
        self.processor = None

    def _get_device(self) -> str:
        """获取可用设备."""
        if settings.CLIP_DEVICE == "cuda" and torch.cuda.is_available():
            return "cuda"
        elif settings.CLIP_DEVICE == "mps" and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self):
        """懒加载模型."""
        if self.model is None:
            self.model = ChineseCLIPModel.from_pretrained(self.model_name).to(self.device)
            self.processor = ChineseCLIPProcessor.from_pretrained(self.model_name)

    def get_image_embedding(
        self,
        image: Union[str, Path, Image.Image],
        normalize: bool = True
    ) -> np.ndarray:
        """获取图片向量。

        Args:
            image: 图片路径或 PIL Image
            normalize: 是否归一化

        Returns:
            512 维向量
        """
        self._load_model()

        if isinstance(image, str) or isinstance(image, Path):
            image = Image.open(image).convert("RGB")

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)

        embedding = outputs.cpu().numpy().flatten()

        if normalize:
            embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def get_text_embedding(
        self,
        text: str,
        normalize: bool = True
    ) -> np.ndarray:
        """获取文本向量。

        Args:
            text: 输入文本
            normalize: 是否归一化

        Returns:
            512 维向量
        """
        self._load_model()

        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)

        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)

        embedding = outputs.cpu().numpy().flatten()

        if normalize:
            embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def batch_get_image_embeddings(
        self,
        images: List[Union[str, Path, Image.Image]],
        batch_size: int = 16,
        normalize: bool = True
    ) -> np.ndarray:
        """批量获取图片向量。

        Args:
            images: 图片列表
            batch_size: 批处理大小
            normalize: 是否归一化

        Returns:
            (n, 512) 向量数组
        """
        self._load_model()

        # 加载所有图片
        loaded_images = []
        for img in images:
            if isinstance(img, str) or isinstance(img, Path):
                loaded_images.append(Image.open(img).convert("RGB"))
            else:
                loaded_images.append(img)

        all_embeddings = []

        for i in range(0, len(loaded_images), batch_size):
            batch_images = loaded_images[i:i + batch_size]

            inputs = self.processor(
                images=batch_images,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs)

            batch_embeddings = outputs.cpu().numpy()

            if normalize:
                batch_embeddings = batch_embeddings / np.linalg.norm(
                    batch_embeddings, axis=1, keepdims=True
                )

            all_embeddings.append(batch_embeddings)

        return np.vstack(all_embeddings)

    def batch_get_text_embeddings(
        self,
        texts: List[str],
        batch_size: int = 16,
        normalize: bool = True
    ) -> np.ndarray:
        """批量获取文本向量。

        Args:
            texts: 文本列表
            batch_size: 批处理大小
            normalize: 是否归一化

        Returns:
            (n, 512) 向量数组
        """
        self._load_model()

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            inputs = self.processor(
                text=batch_texts,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.get_text_features(**inputs)

            batch_embeddings = outputs.cpu().numpy()

            if normalize:
                batch_embeddings = batch_embeddings / np.linalg.norm(
                    batch_embeddings, axis=1, keepdims=True
                )

            all_embeddings.append(batch_embeddings)

        return np.vstack(all_embeddings)


# 单例实例
_clip_service: Optional[ClipService] = None


def get_clip_service() -> ClipService:
    """获取 CLIP 服务单例."""
    global _clip_service
    if _clip_service is None:
        _clip_service = ClipService()
    return _clip_service
