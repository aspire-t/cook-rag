"""
Planner Agent - 将用户简短输入扩展为完整产品规格

职责：
1. 理解用户意图（1-2 句话）
2. 扩展为详细的产品规格文档
3. 分解为可执行的 Sprint 计划
4. 识别 AI 功能集成点
"""

import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from loguru import logger


class PlannerAgent:
    """
    Planner Agent

    输入：用户简短描述（如"创建一个菜谱搜索应用"）
    输出：
    - spec.md: 完整产品规格
    - sprint_plan.md: Sprint 分解计划
    """

    SYSTEM_PROMPT = """
你是一位资深产品经理和技术架构师。你的任务是将用户的简短产品想法扩展为可执行的产品规格和开发计划。

## 你的输出要求

### 1. 产品概述
- 目标用户和核心场景
- 核心价值主张
- 竞品分析要点

### 2. 功能列表
按优先级列出所有功能，分为：
- P0: MVP 核心功能（第一个 Sprint 必须实现）
- P1: 重要功能（后续 Sprint）
- P2: 锦上添花功能（有时间再做）

### 3. 技术架构
- 前端技术栈
- 后端技术栈
- 数据库设计
- 外部服务依赖

### 4. AI 功能集成
识别可以集成 AI 的功能点：
- RAG 检索增强
- 智能推荐
- 自然语言交互
- 内容生成

### 5. Sprint 分解
将功能分解为 5-10 个 Sprint，每个 Sprint：
- 明确的交付物
- 预计工作量（小时）
- 依赖关系

## 输出格式

请生成两个文件：
1. spec.md - 完整产品规格
2. sprint_plan.md - Sprint 计划
"""

    def __init__(self, context):
        self.ctx = context
        self.spec_path = context.artifact_path("spec.md")
        self.sprint_path = context.artifact_path("sprint_plan.md")

    async def run(self) -> bool:
        """
        运行 Planner

        调用 LLM 生成规格文档，并解析为结构化数据
        """
        logger.info("Planner: Generating product specification...")

        # 调用 LLM 生成规格
        spec_content = await self._generate_spec()
        sprint_content = await self._generate_sprint_plan(spec_content)

        # 保存到文件系统（Agent 间通信的 artifact）
        self._save_artifacts(spec_content, sprint_content)

        # 解析为结构化数据
        await self._parse_spec(spec_content)

        logger.success(f"Planner: Generated spec at {self.spec_path}")
        return True

    async def _generate_spec(self) -> str:
        """调用 LLM 生成产品规格"""
        from harness.llm_client import call_llm

        prompt = f"""
{self.SYSTEM_PROMPT}

## 用户输入
{self.ctx.user_prompt}

## 当前项目上下文
项目类型：菜谱 RAG 系统
目标用户：C 端消费者 + B 端餐饮企业
技术栈：FastAPI + Qdrant + PostgreSQL

请生成完整的 spec.md 内容：
"""

        response = await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=4096,
        )

        return response

    async def _generate_sprint_plan(self, spec_content: str) -> str:
        """基于规格生成 Sprint 计划"""
        from harness.llm_client import call_llm

        prompt = f"""
基于以下产品规格，生成详细的 Sprint 计划。

每个 Sprint 包含：
- Sprint 编号和名称
- 目标功能
- 验收标准（3-5 条）
- 预计工作量

{spec_content[:8000]}  # 截取 spec 内容

请生成 sprint_plan.md：
"""

        return await call_llm(
            model="qwen3.5-plus",
            prompt=prompt,
            max_tokens=3072,
        )

    def _save_artifacts(self, spec: str, sprint_plan: str):
        """保存 artifact 文件"""
        self.spec_path.write_text(spec)
        self.sprint_path.write_text(sprint_plan)
        self.ctx.spec_path = self.spec_path

    async def _parse_spec(self, spec_content: str):
        """解析规格生成 SprintContract 列表"""
        # 这里使用简单的文本解析，实际可以用 LLM 提取结构化数据
        self.ctx.sprint_plans = await self._extract_sprints(self.sprint_path.read_text())

    async def _extract_sprints(self, sprint_content: str) -> list:
        """从 Sprint 计划中提取结构化数据"""
        from harness.agents.contract_negotiator import SprintContract

        sprints = []
        lines = sprint_content.split("\n")
        current_sprint = None

        for line in lines:
            if line.startswith("## Sprint"):
                if current_sprint:
                    sprints.append(current_sprint)
                current_sprint = SprintContract(
                    sprint_number=int(line.split()[1].rstrip(":")) if len(line.split()) > 1 else len(sprints) + 1,
                    feature_name=line.split(":")[-1].strip() if ":" in line else "Unknown",
                    description="",
                )
            elif current_sprint and line.startswith("- "):
                current_sprint.description += line[2:] + "\n"

        if current_sprint:
            sprints.append(current_sprint)

        return sprints
