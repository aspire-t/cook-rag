"""
CookRAG Harness - Long-Running Multi-Agent System

基于 Anthropic Harness 设计模式：
- Planner: 将用户输入扩展为完整的产品规格
- Generator: 按 Sprint 迭代实现功能
- Evaluator: 自动化测试和验收

核心模式：
1. Sprint Contract - Generator 和 Evaluator 协商验收标准
2. 文件通信 - 通过 artifact 文件传递上下文
3. Playwright 验证 - 自动化 UI 测试
4. 迭代循环 - 基于反馈持续改进
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class HarnessState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    ITERATING = "iterating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SprintContract:
    """
    Sprint Contract - Generator 和 Evaluator 协商的验收标准

    这是 Harness 的核心设计模式：
    1. 在开发前明确"完成"的定义
    2. Generator 提出实现方案
    3. Evaluator 审查并添加测试条件
    4. 双方达成一致后开始开发
    """
    sprint_number: int
    feature_name: str
    description: str

    # Generator 提出的实现方案
    implementation_plan: str = ""

    # Evaluator 制定的验收标准
    acceptance_criteria: list[str] = field(default_factory=list)

    # 验证脚本/测试
    verification_tests: list[str] = field(default_factory=list)

    # 状态跟踪
    status: str = "pending"  # pending, in_progress, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 评估结果
    qa_score: Optional[float] = None
    bugs_found: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """导出为 Markdown 格式，用于 Agent 间通信"""
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


@dataclass
class HarnessContext:
    """
    Harness 上下文 - 在所有 Agent 间共享的状态

    设计原则：
    1. 所有状态持久化到文件系统
    2. 每个 Agent 读取前一个 Agent 的输出
    3. 支持从中断点恢复
    """
    project_root: Path
    user_prompt: str

    # 状态
    state: HarnessState = HarnessState.IDLE
    current_sprint: int = 0

    # Artifacts
    spec_path: Optional[Path] = None
    sprint_plans: list[SprintContract] = field(default_factory=list)
    qa_reports: list[dict] = field(default_factory=list)

    # 迭代历史
    iteration_history: list[dict] = field(default_factory=list)

    # 错误跟踪
    errors: list[str] = field(default_factory=list)

    def artifact_path(self, filename: str) -> Path:
        """获取 artifact 文件路径"""
        return self.project_root / "harness" / "artifacts" / filename

    def contract_path(self, sprint_num: int) -> Path:
        """获取 sprint contract 文件路径"""
        return self.project_root / "harness" / "contracts" / f"sprint_{sprint_num}.md"

    def log_path(self) -> Path:
        """获取日志文件路径"""
        return self.project_root / "harness" / "logs" / f"harness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def save_state(self):
        """持久化当前状态到文件系统"""
        state_file = self.artifact_path("state.json")
        import json

        state = {
            "state": self.state.value,
            "user_prompt": self.user_prompt,
            "current_sprint": self.current_sprint,
            "spec_path": str(self.spec_path) if self.spec_path else None,
            "sprint_count": len(self.sprint_plans),
            "iteration_count": len(self.iteration_history),
            "errors": self.errors,
            "timestamp": datetime.now().isoformat(),
        }

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_state(cls, project_root: Path) -> "HarnessContext":
        """从文件系统恢复状态"""
        import json

        state_file = project_root / "harness" / "artifacts" / "state.json"
        if not state_file.exists():
            raise FileNotFoundError("No saved state found")

        with open(state_file, "r") as f:
            saved = json.load(f)

        ctx = cls(
            project_root=project_root,
            user_prompt=saved.get("user_prompt", ""),
        )
        ctx.state = HarnessState(saved.get("state", "idle"))
        ctx.current_sprint = saved.get("current_sprint", 0)
        ctx.errors = saved.get("errors", [])

        # 恢复 spec
        if saved.get("spec_path"):
            ctx.spec_path = Path(saved["spec_path"])

        return ctx


class HarnessOrchestrator:
    """
    Harness 编排器 - 协调 Planner、Generator、Evaluator 的执行

    执行流程：
    1. Planner 读取用户输入，生成产品规格和 Sprint 计划
    2. 对每个 Sprint:
       a. Generator 和 Evaluator 协商 Sprint Contract
       b. Generator 实现功能
       c. Evaluator 运行自动化测试
       d. 如果失败，Generator 根据反馈修复
       e. 如果通过，进入下一个 Sprint
    3. 所有 Sprint 完成后，输出最终产品
    """

    def __init__(self, project_root: Path, user_prompt: str):
        self.ctx = HarnessContext(project_root=project_root, user_prompt=user_prompt)
        self.setup_logging()

        # 确保目录存在
        self.ctx.artifact_path("").parent.mkdir(parents=True, exist_ok=True)
        self.ctx.log_path().parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Harness initialized for prompt: {user_prompt[:100]}...")

    def setup_logging(self):
        """配置日志"""
        logger.remove()
        logger.add(
            self.ctx.project_root / "harness" / "logs" / "harness.log",
            rotation="10 MB",
            retention="7 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        )
        logger.add(
            lambda msg: print(msg, end=""),
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>",
        )

    async def run(self) -> HarnessContext:
        """
        运行完整 Harness 流程

        返回最终上下文状态
        """
        try:
            # Phase 1: Planner 生成规格
            self.ctx.state = HarnessState.PLANNING
            self.ctx.save_state()

            logger.info("Phase 1: Planning...")
            from harness.agents.planner import PlannerAgent

            planner = PlannerAgent(self.ctx)
            await planner.run()

            # Phase 2: 执行 Sprints
            self.ctx.state = HarnessState.GENERATING

            for i, sprint in enumerate(self.ctx.sprint_plans):
                logger.info(f"Sprint {i+1}/{len(self.ctx.sprint_plans)}: {sprint.feature_name}")

                # 2a: 协商 Sprint Contract
                from harness.agents.contract_negotiator import ContractNegotiator

                negotiator = ContractNegotiator(self.ctx)
                contract = await negotiator.negotiate(sprint)

                # 2b: Generator 实现
                from harness.agents.generator import GeneratorAgent

                generator = GeneratorAgent(self.ctx, contract)
                await generator.run()

                # 2c: Evaluator 验证
                self.ctx.state = HarnessState.EVALUATING

                from harness.agents.evaluator import EvaluatorAgent

                evaluator = EvaluatorAgent(self.ctx, contract)
                result = await evaluator.run()

                if result.passed:
                    logger.success(f"Sprint {i+1} passed with score {result.score}")
                    contract.status = "completed"
                    contract.qa_score = result.score
                else:
                    logger.warning(f"Sprint {i+1} failed: {result.bugs}")
                    contract.bugs_found = result.bugs

                    # 2d: 迭代修复（最多 3 次）
                    for retry in range(3):
                        logger.info(f"Retry {retry+1}/3: Fixing bugs...")
                        self.ctx.state = HarnessState.ITERATING

                        await generator.fix_bugs(result.bugs)
                        result = await evaluator.run()

                        if result.passed:
                            contract.status = "completed"
                            contract.qa_score = result.score
                            break
                        contract.bugs_found = result.bugs
                    else:
                        contract.status = "failed"
                        logger.error(f"Sprint {i+1} failed after 3 retries")

                # 保存 contract
                self._save_contract(contract)
                self.ctx.save_state()

            self.ctx.state = HarnessState.COMPLETED
            logger.success("Harness completed successfully!")

        except Exception as e:
            self.ctx.state = HarnessState.FAILED
            self.ctx.errors.append(str(e))
            logger.exception(f"Harness failed: {e}")
            raise

        finally:
            self.ctx.save_state()

        return self.ctx

    def _save_contract(self, contract: SprintContract):
        """保存 Sprint Contract 到文件系统"""
        contract_file = self.ctx.contract_path(contract.sprint_number)
        with open(contract_file, "w") as f:
            f.write(contract.to_markdown())


# 便捷函数
async def run_harness(user_prompt: str, project_root: Optional[Path] = None) -> HarnessContext:
    """
    运行 Harness 的便捷函数

    Args:
        user_prompt: 用户的产品描述（1-2 句话）
        project_root: 项目根目录，默认为当前目录

    Returns:
        最终的 HarnessContext
    """
    if project_root is None:
        project_root = Path.cwd()

    orchestrator = HarnessOrchestrator(project_root, user_prompt)
    return await orchestrator.run()


if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "创建一个菜谱搜索应用"

    asyncio.run(run_harness(prompt))
