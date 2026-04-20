"""
Evaluator Agent - 自动化测试和验收

职责：
1. 使用 Playwright 测试 running app
2. 根据 Sprint Contract 验收标准打分
3. 生成 Bug 报告
4. 决定是否需要迭代修复
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class EvaluationResult:
    """评估结果"""
    passed: bool
    score: float
    bugs: List[str]
    details: Dict[str, Any]
    timestamp: datetime


class EvaluatorAgent:
    """
    Evaluator Agent

    使用 Playwright 自动化测试 running app，
    根据 Sprint Contract 验收标准进行评分。
    """

    SYSTEM_PROMPT = """
你是一位资深 QA 工程师。你的任务是测试应用功能并生成详细的 Bug 报告。

## 测试原则
1. 像真实用户一样使用应用
2. 测试所有验收标准
3. 记录详细的复现步骤
4. 截图保存问题现场

## 评分标准
- 5 分：完全符合验收标准
- 4 分：基本符合，有小问题
- 3 分：部分符合，需要改进
- 2 分：大部分不符合
- 1 分：完全不符合
"""

    def __init__(self, context, contract):
        self.ctx = context
        self.contract = contract
        self.app_url = "http://localhost:3000"  # 默认前端地址
        self.api_url = "http://localhost:8000"  # 默认后端地址

    async def run(self) -> EvaluationResult:
        """
        运行 Evaluator

        1. 启动 Playwright
        2. 执行验收测试
        3. 生成 Bug 报告
        4. 计算总分
        """
        logger.info(f"Evaluator: Testing Sprint {self.contract.sprint_number} - {self.contract.feature_name}")

        # Step 1: 启动 Playwright 并导航到应用
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Step 2: 执行测试
            results = await self._run_acceptance_tests(page)

            await browser.close()

        # Step 3: 计算总分
        score = self._calculate_score(results)
        passed = score >= 4.0

        # Step 4: 生成 Bug 报告
        bugs = self._extract_bugs(results)

        result = EvaluationResult(
            passed=passed,
            score=score,
            bugs=bugs,
            details=results,
            timestamp=datetime.now(),
        )

        # Step 5: 保存报告
        await self._save_report(result)

        return result

    async def _run_acceptance_tests(self, page) -> Dict[str, Any]:
        """
        执行验收测试

        对每个验收标准：
        1. 执行测试操作
        2. 验证结果
        3. 记录通过/失败
        """
        results = {}

        for i, criterion in enumerate(self.contract.acceptance_criteria):
            logger.info(f"Testing criterion {i+1}: {criterion[:80]}...")

            try:
                # 使用 LLM 生成测试脚本
                test_script = await self._generate_test_script(criterion)

                # 执行测试
                test_result = await self._execute_test(page, test_script)

                results[criterion] = {
                    "passed": test_result["passed"],
                    "error": test_result.get("error"),
                    "screenshot": test_result.get("screenshot"),
                }

            except Exception as e:
                logger.error(f"Test failed for criterion: {criterion}")
                results[criterion] = {
                    "passed": False,
                    "error": str(e),
                }

        return results

    async def _generate_test_script(self, criterion: str) -> str:
        """
        根据验收标准生成 Playwright 测试脚本

        调用 LLM 将自然语言的验收标准转换为可执行的 Playwright 代码
        """
        from harness.llm_client import call_llm

        prompt = f"""
根据以下验收标准生成 Playwright 测试脚本：

验收标准：{criterion}
应用 URL: {self.app_url}

请生成 Python async Playwright 代码来测试这个标准。
只返回代码，不要解释。

示例格式：
async def test(page):
    await page.goto("{self.app_url}")
    # ... 测试逻辑
    return {"{ passed: boolean, error: string | None }"}
"""

        return await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=2048,
        )

    async def _execute_test(self, page, script: str) -> Dict[str, Any]:
        """执行测试脚本"""
        try:
            # 执行测试脚本
            exec(script, {"page": page})

            # 运行 test 函数
            result = await test(page)

            return {
                "passed": result.get("passed", False),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
            }

    def _calculate_score(self, results: Dict[str, Any]) -> float:
        """计算总分"""
        if not results:
            return 0.0

        passed_count = sum(1 for r in results.values() if r.get("passed", False))
        return (passed_count / len(results)) * 5.0

    def _extract_bugs(self, results: Dict[str, Any]) -> List[str]:
        """从测试结果中提取 Bug 列表"""
        bugs = []

        for criterion, result in results.items():
            if not result.get("passed", False):
                error = result.get("error", "Unknown error")
                bugs.append(f"[{criterion[:50]}...] {error[:200]}")

        return bugs

    async def _save_report(self, result: EvaluationResult):
        """保存评估报告"""
        report_path = self.ctx.artifact_path(f"sprint_{self.contract.sprint_number}_qa_report.md")

        report = f"""# Sprint {self.contract.sprint_number} QA Report

**Date**: {result.timestamp}
**Feature**: {self.contract.feature_name}
**Score**: {result.score:.1f}/5.0
**Status**: {"PASSED" if result.passed else "FAILED"}

## Test Results

"""
        for criterion, details in result.details.items():
            status = "✅" if details.get("passed") else "❌"
            report += f"### {status} {criterion}\n"
            if details.get("error"):
                report += f"Error: {details['error']}\n\n"

        if result.bugs:
            report += "\n## Bugs Found\n\n"
            for i, bug in enumerate(result.bugs, 1):
                report += f"{i}. {bug}\n"

        report_path.write_text(report)
        logger.info(f"QA report saved to {report_path}")
