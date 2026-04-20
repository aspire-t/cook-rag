# CookRAG - 企业级菜谱 RAG 系统

基于 Anthropic Harness 设计模式的 long-running 多 agent 协作系统。

## 架构设计

### 三 Agent 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Planner    │ --> │  Generator  │ --> │  Evaluator  │
│  (规划)      │     │  (生成)      │     │  (评估)      │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      │   Spec.md         │   Code            │   Bug Report
      │   Sprint Plan     │   Test Results    │   QA Feedback
      ▼                   ▼                   ▼
```

### 核心模式

1. **Sprint Contract** - 每轮开发前 Generator 和 Evaluator 协商"完成"标准
2. **文件通信** - Agent 间通过 artifact 文件传递上下文
3. **Playwright 验证** - Evaluator 自动化测试 running app
4. **迭代循环** - 根据反馈持续改进直到通过验收

## 项目结构

```
cook-rag/
├── docs/
│   └── architecture/
│       └── design.md          # 架构设计文档
├── harness/
│   ├── agents/
│   │   ├── planner.py         # Planner Agent
│   │   ├── generator.py       # Generator Agent
│   │   └── evaluator.py       # Evaluator Agent
│   ├── contracts/
│   │   └── sprint_contract.py # Sprint Contract 定义
│   ├── artifacts/
│   │   ├── spec.md            # 产品规格书
│   │   ├── sprint_plan.md     # Sprint 计划
│   │   ├── qa_report.md       # QA 报告
│   │   └── bug_list.md        # Bug 列表
│   └── orchestrator.py        # 编排引擎
├── app/
│   ├── main.py                # FastAPI 入口
│   ├── services/              # 业务服务
│   ├── models/                # 数据模型
│   └── api/                   # API 路由
├── tests/
│   └── e2e/                   # E2E 测试 (Playwright)
├── docker-compose.yml
└── requirements.txt
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发环境
docker-compose up -d

# 运行 Harness
python harness/orchestrator.py --prompt "创建一个菜谱搜索应用"
```

## Long-Running 设计原则

1. **任务分解** - 大任务拆分为可管理的 Sprint
2. **清晰交接** - 通过文件 artifact 传递上下文
3. **独立评估** - Generator 和 Evaluator 分离
4. **自动化验证** - Playwright 自动化 UI 测试
5. **持续迭代** - 基于反馈循环持续改进
