"""导入进度追踪服务."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class ImportProgress:
    """导入进度追踪器."""

    def __init__(self, checkpoint_file: str = "data/.import_checkpoint.json"):
        """
        初始化进度追踪器.

        Args:
            checkpoint_file: 断点文件路径
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """加载状态."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "imported_files": [],
            "failed_files": [],
            "total_count": 0,
            "success_count": 0,
            "fail_count": 0,
            "last_updated": None,
            "started_at": None,
            "completed_at": None,
        }

    def _save_state(self):
        """保存状态."""
        self.state["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def start_import(self, total_count: int):
        """
        开始导入.

        Args:
            total_count: 总文件数
        """
        self.state["total_count"] = total_count
        self.state["started_at"] = datetime.now().isoformat()
        self._save_state()

    def record_success(self, file_path: str, recipe_id: str):
        """
        记录成功导入.

        Args:
            file_path: 文件路径
            recipe_id: 菜谱 ID
        """
        self.state["imported_files"].append({
            "file": file_path,
            "recipe_id": recipe_id,
            "imported_at": datetime.now().isoformat(),
        })
        self.state["success_count"] += 1
        self._save_state()

    def record_failure(self, file_path: str, error: str):
        """
        记录导入失败.

        Args:
            file_path: 文件路径
            error: 错误信息
        """
        self.state["failed_files"].append({
            "file": file_path,
            "error": error,
            "failed_at": datetime.now().isoformat(),
        })
        self.state["fail_count"] += 1
        self._save_state()

    def complete_import(self):
        """完成导入."""
        self.state["completed_at"] = datetime.now().isoformat()
        self._save_state()

    def is_file_imported(self, file_path: str) -> bool:
        """
        检查文件是否已导入.

        Args:
            file_path: 文件路径

        Returns:
            True 如果已导入
        """
        for record in self.state["imported_files"]:
            if record["file"] == file_path:
                return True
        return False

    def get_imported_files(self) -> List[str]:
        """获取已导入文件列表."""
        return [r["file"] for r in self.state["imported_files"]]

    def get_progress(self) -> Dict[str, Any]:
        """
        获取当前进度.

        Returns:
            进度信息
        """
        total = self.state["total_count"]
        success = self.state["success_count"]
        fail = self.state["fail_count"]
        processed = success + fail

        return {
            "total": total,
            "processed": processed,
            "success": success,
            "failed": fail,
            "progress_percent": (processed / total * 100) if total > 0 else 0,
            "started_at": self.state["started_at"],
            "last_updated": self.state["last_updated"],
        }

    def reset(self):
        """重置进度."""
        self.state = {
            "imported_files": [],
            "failed_files": [],
            "total_count": 0,
            "success_count": 0,
            "fail_count": 0,
            "last_updated": None,
            "started_at": None,
            "completed_at": None,
        }
        self._save_state()


# 全局实例
_progress: Optional[ImportProgress] = None


def get_import_progress(checkpoint_file: Optional[str] = None) -> ImportProgress:
    """获取进度追踪器实例."""
    global _progress
    if _progress is None or checkpoint_file:
        _progress = ImportProgress(checkpoint_file)
    return _progress
