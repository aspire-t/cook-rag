# CookRAG Harness Agents

多 Agent 协作系统，基于 Anthropic Harness 设计模式。

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Planner    │ --> │  Generator  │ --> │  Evaluator  │
│  (规划)      │     │  (生成)      │     │  (评估)      │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Agent 职责

### Planner
- 将用户简短输入扩展为完整产品规格
- 分解为可执行的 Sprint 计划
- 识别 AI 功能集成点

### Generator
- 按 Sprint Contract 实现功能
- 自评估代码质量
- 修复 Evaluator 发现的 Bug

### Evaluator
- 使用 Playwright 自动化测试
- 根据验收标准打分
- 生成详细 Bug 报告

## 使用方式

```python
from harness.orchestrator import run_harness

# 运行完整 Harness
await run_harness("创建一个菜谱搜索应用")
```
