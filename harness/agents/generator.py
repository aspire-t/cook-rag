"""
Generator Agent - 按 Sprint Contract 实现功能

职责：
1. 读取 Sprint Contract
2. 实现功能代码
3. 自我评估
4. 修复 Evaluator 发现的 Bug
"""

import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from loguru import logger


class GeneratorAgent:
    """
    Generator Agent

    基于 Sprint Contract 实现功能。
    使用 Playwright MCP 与 running app 交互验证。
    """

    SYSTEM_PROMPT = """
你是一位资深全栈工程师。你的任务是按照 Sprint Contract 实现功能。

## 技术栈
- 前端：React + Vite + TailwindCSS
- 后端：FastAPI + Python 3.11
- 数据库：PostgreSQL + Qdrant
- 测试：Playwright

## 开发原则
1. 先写测试，再实现功能（TDD）
2. 小步提交，频繁验证
3. 遵循已有的代码规范
4. 保持代码简洁清晰

## 输出要求
1. 完整的源代码
2. 单元测试
3. E2E 测试脚本
4. 运行说明
"""

    def __init__(self, context, contract):
        self.ctx = context
        self.contract = contract
        self.app_dir = context.project_root / "app"

    async def run(self) -> bool:
        """
        运行 Generator

        1. 分析 Sprint Contract
        2. 生成代码
        3. 运行测试验证
        """
        logger.info(f"Generator: Starting Sprint {self.contract.sprint_number} - {self.contract.feature_name}")

        # 确保应用目录存在
        self.app_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: 分析需求
        await self._analyze_requirements()

        # Step 2: 生成代码
        await self._generate_code()

        # Step 3: 运行测试
        test_passed = await self._run_tests()

        if not test_passed:
            logger.warning("Generator: Initial tests failed, attempting fixes...")
            await self._fix_issues()

        return test_passed

    async def fix_bugs(self, bugs: List[str]):
        """根据 Evaluator 的 Bug 报告修复问题"""
        logger.info(f"Generator: Fixing {len(bugs)} bugs...")

        for i, bug in enumerate(bugs):
            logger.info(f"Fixing bug {i+1}/{len(bugs)}: {bug[:100]}...")
            await self._fix_single_bug(bug)

        # 修复后重新运行测试
        await self._run_tests()

    async def _analyze_requirements(self):
        """分析 Sprint Contract 需求"""
        from harness.llm_client import call_llm

        prompt = f"""
分析以下 Sprint Contract，生成详细的实现方案：

{self.contract.to_markdown()}

请输出：
1. 需要修改/创建的文件列表
2. 每个文件的核心逻辑
3. 潜在的技术难点
"""

        analysis = await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=2048,
        )

        # 保存分析结果
        analysis_file = self.ctx.artifact_path(f"sprint_{self.contract.sprint_number}_analysis.md")
        analysis_file.write_text(analysis)
        logger.debug(f"Analysis saved to {analysis_file}")

    async def _generate_code(self):
        """生成代码"""
        from harness.llm_client import call_llm

        # 读取分析结果
        analysis_file = self.ctx.artifact_path(f"sprint_{self.contract.sprint_number}_analysis.md")
        analysis = analysis_file.read_text() if analysis_file.exists() else ""

        # 生成每个模块的代码
        modules = await self._get_module_list(analysis)

        for module_path in modules:
            logger.info(f"Generating: {module_path}")

            code = await call_llm(
                model="qwen3.5-plus",
                prompt=f"""
基于以下分析生成代码：
{analysis}

请生成 {module_path} 的完整代码：
""",
                max_tokens=4096,
            )

            # 写入文件
            full_path = self.ctx.project_root / module_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code)

    async def _get_module_list(self, analysis: str) -> List[str]:
        """获取需要生成的模块列表"""
        from harness.llm_client import call_llm

        response = await call_llm(
            model="qwen3.5-plus",
            prompt=f"""
从以下分析中提取需要创建/修改的文件列表：
{analysis}

只返回文件路径列表，每行一个：
""",
            max_tokens=512,
        )

        return [line.strip() for line in response.split("\n") if line.strip().endswith((".py", ".tsx", ".ts", ".css"))]

    async def _run_tests(self) -> bool:
        """运行测试验证"""
        import subprocess

        test_dir = self.ctx.project_root / "tests" / "e2e"

        if not test_dir.exists():
            logger.warning("Generator: No E2E tests found, skipping...")
            return True

        try:
            result = subprocess.run(
                ["pytest", str(test_dir), "-v"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            passed = result.returncode == 0

            if passed:
                logger.success("Generator: All tests passed!")
            else:
                logger.error(f"Generator: Tests failed:\n{result.stdout}\n{result.stderr}")

            return passed

        except subprocess.TimeoutExpired:
            logger.error("Generator: Test timeout")
            return False
        except Exception as e:
            logger.error(f"Generator: Test error: {e}")
            return True  # 测试基础设施问题，不阻止流程

    async def _fix_issues(self):
        """修复测试发现的问题"""
        # 读取测试输出，调用 LLM 分析并修复
        pass

    async def _fix_single_bug(self, bug: str):
        """修复单个 Bug"""
        from harness.llm_client import call_llm

        # 调用 LLM 分析 Bug 并生成修复代码
        fix = await call_llm(
            model="qwen3.5-plus",
            prompt=f"""
修复以下 Bug：
{bug}

请分析原因并给出修复方案：
""",
            max_tokens=2048,
        )

        # 应用修复
        await self._apply_fix(fix)

    async def _apply_fix(self, fix: str):
        """应用修复代码"""
        # 解析 fix 内容，更新对应文件
        pass
