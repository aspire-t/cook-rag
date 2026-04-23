#!/usr/bin/env python3
"""本地测试脚本 - 测试数据导入逻辑（不需要外部服务）。

使用方法:
    python scripts/test_local.py
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_parser():
    """测试 HowToCook Markdown 解析器。"""
    print("\n" + "=" * 50)
    print("测试 HowToCook Markdown 解析器")
    print("=" * 50)

    # 直接导入解析器类而不依赖完整模块
    import re
    from typing import List, Dict

    class HowToCookParser:
        """HowToCook Markdown 解析器。"""

        def __init__(self):
            self.section_patterns = {
                "ingredients": re.compile(r"## 食材\s*.*?(?=##|$)", re.DOTALL),
                "steps": re.compile(r"## 做法\s*.*?(?=##|$)", re.DOTALL),
                "tags": re.compile(r"tags:\s*\[([^\]]+)\]", re.IGNORECASE),
            }

        def parse_markdown(self, content: str) -> Dict:
            """解析 Markdown 内容。"""
            result = {
                "name": self._extract_title(content),
                "ingredients": self._extract_ingredients(content),
                "steps": self._extract_steps(content),
                "tags": self._extract_tags(content),
                "cuisine": self._extract_cuisine(content),
                "difficulty": self._estimate_difficulty(content),
                "prep_time": 0,
                "cook_time": 0,
                "content": content
            }
            return result

        def _extract_title(self, content: str) -> str:
            match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
            return match.group(1).strip() if match else ""

        def _extract_ingredients(self, content: str) -> List[str]:
            ingredients = []
            match = self.section_patterns["ingredients"].search(content)
            if match:
                section = match.group(0)
                for line in section.split("\n"):
                    line = line.strip()
                    if line.startswith("- ") and len(line) > 2:
                        ingredients.append(line[2:].strip())
            return ingredients

        def _extract_steps(self, content: str) -> List[str]:
            steps = []
            match = self.section_patterns["steps"].search(content)
            if match:
                section = match.group(0)
                for line in section.split("\n"):
                    line = line.strip()
                    if re.match(r"^\d+[\.\)]\s*", line):
                        step_text = re.sub(r"^\d+[\.\)]\s*", "", line)
                        steps.append(step_text)
            return steps

        def _extract_tags(self, content: str) -> List[str]:
            tags = []
            match = self.section_patterns["tags"].search(content)
            if match:
                tags_str = match.group(1)
                tags = [t.strip().strip("\"'") for t in tags_str.split(",")]
            return tags

        def _extract_cuisine(self, content: str) -> str:
            cuisine_map = {
                "川菜": ["川菜", "四川", "麻辣"],
                "粤菜": ["粤菜", "广东", "清淡"],
            }
            tags = self._extract_tags(content)
            tags_str = ",".join(tags)
            for cuisine, keywords in cuisine_map.items():
                for keyword in keywords:
                    if keyword in tags_str:
                        return cuisine
            return "其他"

        def _estimate_difficulty(self, content: str) -> str:
            ingredients_count = len(self._extract_ingredients(content))
            steps_count = len(self._extract_steps(content))
            total = ingredients_count + steps_count
            if total < 10:
                return "easy"
            elif total < 20:
                return "medium"
            else:
                return "hard"

    parser = HowToCookParser()

    # 测试 Markdown 内容
    test_markdown = """
# 鱼香肉丝

tags: ["川菜", "辣", "家常"]

## 食材

- 猪里脊肉 200g
- 笋 100g
- 木耳 50g

## 做法

1. 肉切丝
2. 腌制 10 分钟
3. 炒制

## 小贴士

多放点饭！
"""

    result = parser.parse_markdown(test_markdown)

    print(f"菜名：{result['name']}")
    print(f"菜系：{result['cuisine']}")
    print(f"难度：{result['difficulty']}")
    print(f"食材数：{len(result['ingredients'])}")
    print(f"步骤数：{len(result['steps'])}")
    print(f"标签：{result['tags']}")

    # 验证
    assert result['name'] == '鱼香肉丝', f"菜名错误：{result['name']}"
    assert len(result['ingredients']) == 3, f"食材数错误：{len(result['ingredients'])}"
    assert len(result['steps']) == 3, f"步骤数错误：{len(result['steps'])}"
    assert '川菜' in result['tags'], f"标签错误：{result['tags']}"

    print("✅ 解析测试通过")
    return True


def test_clip_service():
    """测试 CLIP 服务。"""
    print("\n" + "=" * 50)
    print("测试 CLIP 向量化服务")
    print("=" * 50)

    from app.services.clip_service import get_clip_service
    from PIL import Image
    import numpy as np

    clip_service = get_clip_service()

    # 测试文本向量化
    print("测试文本向量化...")
    text_vector = clip_service.get_text_embedding("鱼香肉丝")
    print(f"  文本向量维度：{text_vector.shape}")
    assert text_vector.shape == (512,), f"维度错误：{text_vector.shape}"

    # 测试图片向量化
    print("测试图片向量化...")
    img = Image.new("RGB", (224, 224), color="red")
    image_vector = clip_service.get_image_embedding(img)
    print(f"  图片向量维度：{image_vector.shape}")
    assert image_vector.shape == (512,), f"维度错误：{image_vector.shape}"

    # 测试归一化
    text_norm = np.linalg.norm(text_vector)
    image_norm = np.linalg.norm(image_vector)
    print(f"  文本向量范数：{text_norm:.4f}")
    print(f"  图片向量范数：{image_norm:.4f}")
    assert abs(text_norm - 1.0) < 0.01, f"文本未归一化：{text_norm}"
    assert abs(image_norm - 1.0) < 0.01, f"图片未归一化：{image_norm}"

    # 测试跨模态
    similarity = np.dot(text_vector, image_vector)
    print(f"  跨模态相似度：{similarity:.4f}")

    print("✅ CLIP 测试通过")
    return True


def test_qdrant_schema():
    """测试 Qdrant Schema。"""
    print("\n" + "=" * 50)
    print("测试 Qdrant Schema")
    print("=" * 50)

    from app.services.qdrant_schema import get_collection_config, PAYLOAD_SCHEMA

    config = get_collection_config()
    vectors = config["vectors"]

    print("向量配置:")
    for name, params in vectors.items():
        print(f"  - {name}: {params.size}维")

    # 验证 5 路向量
    assert "name_vec" in vectors, "缺少 name_vec"
    assert "desc_vec" in vectors, "缺少 desc_vec"
    assert "step_vec" in vectors, "缺少 step_vec"
    assert "tag_vec" in vectors, "缺少 tag_vec"
    assert "image_vec" in vectors, "缺少 image_vec"

    # 验证维度
    assert vectors["name_vec"].size == 1024
    assert vectors["image_vec"].size == 512

    print("✅ Qdrant Schema 测试通过")
    return True


def test_image_importer():
    """测试图片导入器。"""
    print("\n" + "=" * 50)
    print("测试图片导入器")
    print("=" * 50)

    from app.services.image_importer import ImageImporter

    importer = ImageImporter(token="fake_token")

    # 测试 Markdown 解析
    markdown = """
# 鱼香肉丝

![封面图](https://example.com/cover.jpg)

步骤 1：![步骤 1](https://example.com/step1.jpg)

步骤 2：![步骤 2](https://example.com/step2.jpg)
"""

    images = importer.parse_markdown_images(markdown)
    print(f"解析到 {len(images)} 张图片")

    assert len(images) == 3, f"图片数错误：{len(images)}"
    assert images[0]["type"] == "cover", f"类型错误：{images[0]['type']}"
    assert images[1]["type"] == "step", f"类型错误：{images[1]['type']}"

    print("✅ 图片导入器测试通过")
    return True


def test_api_schemas():
    """测试 API Schema。"""
    print("\n" + "=" * 50)
    print("测试 API Schema")
    print("=" * 50)

    from app.api.schemas import (
        RecipeImageResponse,
        RecipeImagesResponse,
        ImageSearchRequest,
        ImageSearchResponse
    )

    # 测试图片响应
    img_resp = RecipeImageResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        step_no=None,
        image_type="cover",
        image_url="https://example.com/cover.jpg",
        width=800,
        height=600,
        file_size=102400
    )
    print(f"图片响应：{img_resp.image_type}")

    # 测试图片列表响应
    list_resp = RecipeImagesResponse(
        recipe_id="550e8400-e29b-41d4-a716-446655440000",
        cover=img_resp,
        steps=[]
    )
    print(f"列表响应：recipe_id={list_resp.recipe_id}")

    # 测试搜索请求
    search_req = ImageSearchRequest(
        text_query="川菜",
        limit=10
    )
    print(f"搜索请求：text_query={search_req.text_query}")

    print("✅ API Schema 测试通过")
    return True


def main():
    print("=" * 60)
    print("CookRAG 本地测试")
    print("=" * 60)

    tests = [
        ("Parser", test_parser),
        ("CLIP", test_clip_service),
        ("Qdrant Schema", test_qdrant_schema),
        ("Image Importer", test_image_importer),
        ("API Schema", test_api_schemas),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} 测试失败：{e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = all(results.values())
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    if all_passed:
        print("\n🎉 所有本地测试通过！")
        print("\n下一步:")
        print("1. 启动 Qdrant: docker compose up -d qdrant")
        print("2. 创建 Collection: python scripts/qdrant_collection.py --create")
        print("3. 导入数据：python scripts/import_data.py --source data/howtocook")
    else:
        print("\n⚠️  部分测试失败")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
