"""
Contract Negotiator - Sprint Contract 协商器

职责：
1. Generator 提出实现方案
2. Evaluator 审查并添加测试条件
3. 双方协商达成一致
"""

import asyncio
from typing import List, Optional
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class SprintContract:
    """Sprint Contract 定义"""
    sprint_number: int
    feature_name: str
    description: str
    implementation_plan: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    verification_tests: list[str] = field(default_factory=list)
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    qa_score: Optional[float] = None
    bugs_found: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        criteria = "\n".join(f"- [ ] {c}" for c in self.acceptance_criteria)
        tests = "\n".join(f"- {t}" for t in self.verification_tests)
        bugs = "\n".join(f"- {b}" for b in self.bugs_found) if self.bugs_found else "无"

        return f"""# Sprint {self.sprint_number} Contract

## Feature: {self.feature_name}

### Description
{self.description}

## Implementation Plan
{self.implementation_plan}

## Acceptance Criteria
{criteria}

## Verification Tests
{tests}

## Status
- **State**: {self.status}
- **Started**: {self.started_at or 'Not started'}
- **Completed**: {self.completed_at or 'In progress'}
- **QA Score**: {self.qa_score or 'N/A'}

## Bugs Found
{bugs}
"""


class ContractNegotiator:
    """
    Contract Negotiator

    核心设计：Sprint Contract 机制
    - 在开发前明确"完成"的定义
    - Generator 和 Evaluator 共同协商验收标准
    - 确保双方对"Done"有一致的理解
    """

    def __init__(self, context):
        self.ctx = context

    async def negotiate(self, sprint_plan) -> SprintContract:
        """
        协商 Sprint Contract

        流程：
        1. Generator 提出实现方案
        2. Evaluator 提出验收标准
        3. 双方迭代直到达成一致
        """
        logger.info(f"Negotiating Sprint Contract for: {sprint_plan.feature_name}")

        # Step 1: 创建初始 Contract
        contract = SprintContract(
            sprint_number=sprint_plan.sprint_number,
            feature_name=sprint_plan.feature_name,
            description=sprint_plan.description,
        )

        # Step 2: Generator 提出实现方案
        contract = await self._generator_proposes(contract)

        # Step 3: Evaluator 添加验收标准
        contract = await self._evaluator_adds_criteria(contract)

        # Step 4: 协商测试条件
        contract = await self._negotiate_tests(contract)

        # 保存 Contract
        self._save_contract(contract)

        logger.success(f"Contract negotiated for Sprint {contract.sprint_number}")
        return contract

    async def _generator_proposes(self, contract: SprintContract) -> SprintContract:
        """Generator 提出实现方案"""
        from harness.llm_client import call_llm

        prompt = f"""
作为 Generator，为以下 Sprint 提出实现方案：

Feature: {contract.feature_name}
Description: {contract.description}

请输出：
1. 实现思路（2-3 句话）
2. 需要创建/修改的文件列表
3. 关键技术点

保持方案简洁务实。
"""

        response = await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=1024,
        )

        contract.implementation_plan = response
        return contract

    async def _evaluator_adds_criteria(self, contract: SprintContract) -> SprintContract:
        """Evaluator 添加验收标准"""
        from harness.llm_client import call_llm

        prompt = f"""
作为 Evaluator，基于以下实现方案制定验收标准：

Feature: {contract.feature_name}
Implementation Plan: {contract.implementation_plan}

请输出 5-8 个具体的验收标准，每个标准：
- 具体可测试
- 有明确的通过/失败条件
- 涵盖功能、用户体验、边界情况

格式示例：
1. 用户可以成功登录
2. 登录失败时显示错误提示
3. 记住密码功能正常工作
...
"""

        response = await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=1024,
        )

        # 解析验收标准
        criteria = []
        for line in response.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                # 移除序号，保留内容
                content = line.split(".", 1)[-1].strip()
                criteria.append(content)

        contract.acceptance_criteria = criteria
        return contract

    async def _negotiate_tests(self, contract: SprintContract) -> SprintContract:
        """Generator 和 Evaluator 协商测试条件"""
        from harness.llm_client import call_llm

        prompt = f"""
为以下验收标准制定具体的测试方法：

验收标准：
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(contract.acceptance_criteria))}

请为每个标准制定 1-2 个具体的测试场景。
格式：
- [验收标准序号] 测试场景描述
"""

        response = await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=1024,
        )

        # 解析测试
        tests = []
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                tests.append(line)

        contract.verification_tests = tests
        return contract

    def _save_contract(self, contract: SprintContract):
        """保存 Contract 到文件系统"""
        contract_file = self.ctx.contract_path(contract.sprint_number)
        contract_file.parent.mkdir(parents=True, exist_ok=True)
        contract_file.write_text(contract.to_markdown())
        logger.debug(f"Contract saved to {contract_file}")