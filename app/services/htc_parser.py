"""HowToCook Markdown 解析器."""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedRecipe:
    """解析后的菜谱数据."""
    name: str
    description: str
    ingredients: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    tags: List[str]
    source_url: Optional[str] = None


class HowToCookParser:
    """HowToCook Markdown 菜谱解析器."""

    def __init__(self):
        """初始化解析器."""
        pass

    def parse_file(self, file_path: Path) -> ParsedRecipe:
        """
        解析 Markdown 文件.

        Args:
            file_path: Markdown 文件路径

        Returns:
            ParsedRecipe 对象
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse(content)

    def parse(self, content: str) -> ParsedRecipe:
        """
        解析 Markdown 内容.

        Args:
            content: Markdown 内容

        Returns:
            ParsedRecipe 对象
        """
        # 提取菜名（第一个标题）
        name = self._extract_name(content)

        # 提取描述
        description = self._extract_description(content)

        # 提取食材
        ingredients = self._extract_ingredients(content)

        # 提取步骤
        steps = self._extract_steps(content)

        # 提取标签
        tags = self._extract_tags(content)

        return ParsedRecipe(
            name=name,
            description=description,
            ingredients=ingredients,
            steps=steps,
            tags=tags,
        )

    def _extract_name(self, content: str) -> str:
        """
        提取菜名.

        Args:
            content: Markdown 内容

        Returns:
            菜名
        """
        # 匹配第一个一级标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # 如果没有标题，返回空字符串
        return ""

    def _extract_description(self, content: str) -> str:
        """
        提取描述.

        Args:
            content: Markdown 内容

        Returns:
            描述文本
        """
        # 查找"菜名"或"简介"部分
        lines = content.split('\n')
        description_lines = []
        in_description = False

        for line in lines:
            if line.startswith('#'):
                # 跳过标题行
                if in_description:
                    break
                continue

            if '简介' in line or '描述' in line:
                in_description = True
                continue

            if in_description:
                if line.strip() and not line.startswith('['):
                    description_lines.append(line.strip())
                elif description_lines:
                    break

        # 如果没有找到描述，使用第一段非空文本
        if not description_lines:
            for line in lines:
                if line.startswith('#'):
                    continue
                if line.strip() and not line.startswith('['):
                    description_lines.append(line.strip())
                    break

        return ' '.join(description_lines)

    def _extract_ingredients(self, content: str) -> List[Dict[str, Any]]:
        """
        提取食材.

        Args:
            content: Markdown 内容

        Returns:
            食材列表 [{name, amount, unit, notes}]
        """
        ingredients = []

        # 匹配食材部分
        in_ingredients = False
        lines = content.split('\n')

        for line in lines:
            # 检测食材部分开始
            if '## 所需食材' in line or '## 食材' in line or '## 材料' in line:
                in_ingredients = True
                continue

            if in_ingredients:
                # 检测下一个部分开始
                if line.startswith('##'):
                    break

                # 匹配列表项
                match = re.match(r'^[-*]\s*(.+)$', line.strip())
                if match:
                    ingredient_text = match.group(1).strip()
                    parsed = self._parse_ingredient_line(ingredient_text)
                    if parsed:
                        ingredients.append(parsed)

        return ingredients

    def _parse_ingredient_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析单行食材.

        Args:
            line: 食材行文本

        Returns:
            食材字典
        """
        # 尝试匹配 "名称 用量 单位" 格式
        # 例如："鸡蛋 2 个", "盐 适量", "猪肉 500g"

        # 移除括号内容作为备注
        notes = None
        if '(' in line:
            line, notes = line.split('(', 1)
            notes = notes.rstrip(')').strip()

        # 匹配用量和单位
        amount_match = re.search(r'(\d+\.?\d*)\s*(g|ml|个|勺|匙|碗|杯|片|块|根)?', line)

        if amount_match:
            amount = float(amount_match.group(1))
            unit = amount_match.group(2) or ""
            name = line[:amount_match.start()].strip()
        else:
            amount = None
            unit = None
            name = line.strip()

        return {
            "name": name,
            "amount": amount,
            "unit": unit,
            "notes": notes,
        }

    def _extract_steps(self, content: str) -> List[Dict[str, Any]]:
        """
        提取步骤.

        Args:
            content: Markdown 内容

        Returns:
            步骤列表 [{step_no, description, tips}]
        """
        steps = []

        # 匹配步骤部分
        in_steps = False
        lines = content.split('\n')
        step_no = 1

        for line in lines:
            # 检测步骤部分开始
            if '## 制作步骤' in line or '## 步骤' in line or '## 做法' in line:
                in_steps = True
                continue

            if in_steps:
                # 检测下一个部分开始
                if line.startswith('##') and '步骤' not in line:
                    break

                # 匹配有序列表
                match = re.match(r'^(\d+)[.、)\s]+(.+)$', line.strip())
                if match:
                    step_no = int(match.group(1))
                    description = match.group(2).strip()
                    steps.append({
                        "step_no": step_no,
                        "description": description,
                        "tips": None,
                    })

        return steps

    def _extract_tags(self, content: str) -> List[str]:
        """
        提取标签.

        Args:
            content: Markdown 内容

        Returns:
            标签列表
        """
        tags = []

        # 匹配标签部分
        lines = content.split('\n')

        for line in lines:
            # 匹配 "标签：xxx, xxx" 格式
            if '标签' in line:
                match = re.search(r'标签 [：:]\s*(.+)$', line)
                if match:
                    tag_text = match.group(1)
                    tags = [t.strip() for t in re.split(r'[,，\s]+', tag_text) if t.strip()]
                    break

        return tags


# 全局解析器实例
_parser: Optional[HowToCookParser] = None


def get_howtocook_parser() -> HowToCookParser:
    """获取解析器实例."""
    global _parser
    if _parser is None:
        _parser = HowToCookParser()
    return _parser
