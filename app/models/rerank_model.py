"""BGE-Reranker 重排序模型 - 基于 Transformer 的交叉编码器."""

import torch
import torch.nn.functional as F
from typing import List, Tuple, Dict, Any, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path
import asyncio


class RerankModel:
    """
    BGE-Reranker-v2-m3 重排序模型.

    使用交叉编码器 (Cross-Encoder) 对查询 - 文档对进行精细化排序。
    支持 MPS (Apple Silicon) 和 CUDA 加速。
    """

    MODEL_NAME = "BAAI/bge-reranker-v2-m3"

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        max_length: int = 512,
    ):
        """
        初始化 Rerank 模型.

        Args:
            model_name: 模型名称或路径
            device: 设备 (cuda/mps/cpu)
            max_length: 最大序列长度
        """
        self.model_name = model_name or self.MODEL_NAME
        self.max_length = max_length
        self.device = self._detect_device(device)
        self.model = None
        self.tokenizer = None
        self._loaded = False

    def _detect_device(self, device: Optional[str] = None) -> str:
        """
        检测并返回最佳设备.

        优先级：MPS > CUDA > CPU

        Args:
            device: 用户指定的设备

        Returns:
            设备字符串
        """
        if device:
            return device

        # Apple Silicon MPS
        if torch.backends.mps.is_available():
            return "mps"

        # NVIDIA CUDA
        if torch.cuda.is_available():
            return "cuda"

        # CPU fallback
        return "cpu"

    def load_model(self) -> bool:
        """
        加载模型和分词器.

        Returns:
            True 如果加载成功
        """
        if self._loaded:
            return True

        try:
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )

            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
            )

            # 移动到指定设备
            self.model = self.model.to(self.device)
            self.model.eval()

            self._loaded = True
            print(f"Rerank 模型已加载到设备：{self.device}")
            return True

        except Exception as e:
            print(f"加载 Rerank 模型失败：{e}")
            return False

    def ensure_loaded(self) -> bool:
        """确保模型已加载，异步安全."""
        if not self._loaded:
            return self.load_model()
        return True

    async def rerank_batch(
        self,
        query: str,
        documents: List[str],
        batch_size: int = 16,
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """
        批量重排序.

        Args:
            query: 查询文本
            documents: 文档列表
            batch_size: 批处理大小
            top_k: 返回 Top K 结果

        Returns:
            [(doc_index, score), ...] 按分数降序排列
        """
        if not self.ensure_loaded():
            raise RuntimeError("模型未加载")

        if not documents:
            return []

        all_scores = []

        # 批处理
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_scores = await self._score_batch(query, batch_docs)

            for idx, score in enumerate(batch_scores):
                all_scores.append((i + idx, score))

        # 按分数降序排序
        all_scores.sort(key=lambda x: x[1], reverse=True)

        # 返回 Top K
        if top_k:
            all_scores = all_scores[:top_k]

        return all_scores

    async def _score_batch(
        self,
        query: str,
        documents: List[str],
    ) -> List[float]:
        """
        对一批文档进行评分.

        Args:
            query: 查询文本
            documents: 文档批次

        Returns:
            分数列表
        """
        # 构建输入对
        pairs = [[query, doc] for doc in documents]

        # 分词
        inputs = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(self.device)

        # 推理
        with torch.no_grad():
            outputs = self.model(**inputs)

        # 获取分数 (使用 logits 的最后一个 token)
        # BGE-Reranker 返回的是 classification logits
        if hasattr(outputs, "logits"):
            scores = outputs.logits.squeeze(-1)
        else:
            # 对于某些模型架构，可能需要不同的处理方式
            scores = outputs[0].squeeze(-1)

        # 归一化到 [0, 1] (sigmoid)
        scores = torch.sigmoid(scores)

        # 转换为列表
        return scores.cpu().tolist()

    def rerank_sync(
        self,
        query: str,
        documents: List[str],
        batch_size: int = 16,
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """
        同步重排序方法.

        Args:
            query: 查询文本
            documents: 文档列表
            batch_size: 批处理大小
            top_k: 返回 Top K 结果

        Returns:
            [(doc_index, score), ...]
        """
        # 在当前线程中运行异步方法
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.rerank_batch(query, documents, batch_size, top_k)
        )

    def unload(self):
        """卸载模型，释放显存."""
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        self._loaded = False

        # 清理 CUDA/MPS 缓存
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif self.device == "mps":
            torch.mps.empty_cache()


# 全局单例
_rerank_model: Optional[RerankModel] = None


def get_rerank_model() -> RerankModel:
    """获取 Rerank 模型单例."""
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = RerankModel()
    return _rerank_model


async def rerank_documents(
    query: str,
    documents: List[str],
    top_k: Optional[int] = None,
    batch_size: int = 16,
) -> List[Tuple[int, float]]:
    """
    重排序文档.

    Args:
        query: 查询文本
        documents: 文档列表
        top_k: 返回 Top K 结果
        batch_size: 批处理大小

    Returns:
        [(doc_index, score), ...]
    """
    model = get_rerank_model()
    return await model.rerank_batch(query, documents, batch_size, top_k)
