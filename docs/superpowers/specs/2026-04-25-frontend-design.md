# CookRAG C 端前端设计文档

**日期**: 2026-04-25
**子项目**: A — 搜索结果 + 菜谱详情 + 跟做模式
**目标平台**: 微信小程序 + H5 双端
**技术栈**: Taro 4.x + React + TypeScript

---

## 1. 概述

为 CookRAG 企业级菜谱 RAG 系统构建 C 端前端应用，覆盖用户从搜索到跟做的完整流程。采用一套代码、双端编译策略（Taro），降低后期维护成本。

### 1.1 范围

本设计覆盖子项目 A 的 4 个页面：
- 首页（搜索入口）
- 搜索结果页
- 菜谱详情页
- 跟做模式页

监控仪表盘（子项目 C）独立设计，不在此文档范围内。

### 1.2 设计原则

- **下厨房风格** — 暖色调、生活感、照片为主、亲和力强
- **前端强缓存** — 三层缓存模型，收藏操作乐观更新
- **双端一致体验** — 小程序与 H5 的 UI/交互保持一致

---

## 2. 项目架构

### 2.1 目录结构

```
cook-rag-frontend/
├── src/
│   ├── pages/                    # 页面路由
│   │   ├── home/                 #   首页（搜索入口）
│   │   ├── search/               #   搜索结果页
│   │   ├── detail/[id]/          #   菜谱详情页
│   │   └── cook/[id]/            #   跟做模式页
│   │
│   ├── components/               # 可复用组件
│   │   ├── RecipeCard/           #   菜谱卡片（搜索列表项）
│   │   ├── SearchBar/            #   搜索输入框 + 语音 + 图片
│   │   ├── FilterBar/            #   快速筛选标签
│   │   ├── IngredientList/       #   食材列表
│   │   ├── StepList/             #   步骤列表
│   │   ├── CookingNav/           #   跟做进度导航
│   │   ├── Timer/                #   倒计时器
│   │   └── Toast/                #   轻提示
│   │
│   ├── services/                 # API 层
│   │   ├── api/                  #   HTTP 请求封装
│   │   ├── websocket/            #   WebSocket 连接管理
│   │   └── cache/                #   前端缓存策略
│   │
│   ├── store/                    # 状态管理（Zustand）
│   │   ├── useSearchStore.ts     #   搜索状态
│   │   ├── useUserStore.ts       #   用户状态 + 收藏
│   │   └── useCookStore.ts       #   跟做状态机
│   │
│   ├── styles/                   # 全局样式
│   │   ├── tokens.css            #   设计令牌（色板、间距、字体）
│   │   └── common.css            #   公共样式
│   │
│   └── utils/                    # 工具函数
│       ├── format.ts             #   数字/时间格式化
│       └── image.ts              #   图片尺寸适配
│
├── config/                       # Taro 环境配置
│   ├── dev.ts
│   ├── prod.ts
│   └── index.ts
│
├── project.config.json           # 微信小程序配置
└── taro.config.js                # Taro 编译配置
```

### 2.2 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 跨端框架 | Taro 4.x | 一套代码编译到小程序 + H5 |
| UI 框架 | React 18 | Taro 首选，生态成熟 |
| 语言 | TypeScript | 类型安全，减少运行时错误 |
| 状态管理 | Zustand | 轻量、无 boilerplate、跨平台兼容 |
| HTTP 层 | Taro.request 封装 | 统一拦截器处理 token 和错误 |
| 缓存策略 | localStorage + TTL | 小程序和 H5 都支持，无额外依赖 |
| WebSocket | Taro.connectSocket | 双端统一的 API |
| 样式方案 | CSS + CSS 变量（设计令牌） | Taro 原生支持，平台差异小 |

---

## 3. 页面设计

### 3.1 首页（搜索入口）

**路由**: `pages/home/index`

**布局**:
```
┌─────────────────────────┐
│      CookRAG Logo       │
│                         │
│   ┌─────────────────┐   │
│   │ 🔍 搜索菜谱...  │   │
│   └─────────────────┘   │
│                         │
│   [川菜] [粤菜] [快手菜] │
│   [川菜] [素菜] [甜品]   │
│                         │
│   ─── 热门菜谱 ───      │
│   ┌─────────────┐       │
│   │ [封面图]     │       │
│   │  红烧肉       │       │
│   │  川菜 · 中等  ❤️│   │
│   └─────────────┘       │
└─────────────────────────┘
```

**交互行为**:
- 点击搜索框 → 弹出半屏面板（搜索历史、热门搜索、语音/图片入口）
- 点击筛选标签 → `navigateTo` 到搜索结果页，携带预设筛选参数
- 点击菜谱卡片 → `navigateTo` 到详情页
- 热门菜谱列表 → 启动时从 API 获取，走 L2 缓存

### 3.2 搜索结果页

**路由**: `pages/search/index`

**布局**:
```
┌─────────────────────────┐
│ ←  🔍 红烧肉       🔍📷 │
├─────────────────────────┤
│ [川菜▼] [难度▼] [排序▼] │
├─────────────────────────┤
│ ┌───────────────────┐   │
│ │ [封面图]           │   │
│ │  红烧肉              │   │
│ │  经典川菜，肥而不腻  │   │
│ │  川菜 · 中等       ❤️ │   │
│ └───────────────────┘   │
│     加载更多...         │
└─────────────────────────┘
```

**菜谱卡片组件 (RecipeCard)** 展示字段：
- 封面图（固定宽高比 4:3）
- 菜名（主标题，截断最多 2 行）
- 简介（副标题，截断最多 1 行）
- 菜系标签（左）
- 难度等级（左，标签样式）
- 收藏状态（右，❤️ 图标）

**交互行为**:
- 下拉刷新 → 重新搜索
- 滚动到底 → 自动加载更多（分页，page_size=10）
- 点击收藏 → 乐观更新 + 后台同步
- 点击卡片 → `navigateTo` 到详情页

### 3.3 菜谱详情页

**路由**: `pages/detail/[id]/index`

**布局**:
```
┌─────────────────────────┐
│    [封面大图]            │
│  红烧肉                  │
│  川菜 · 中等难度          │
│  ❤️ 128   ⏱ 45分钟      │
├─────────────────────────┤
│  食材                     │
│  · 五花肉 500g           │
│  · 冰糖 30g              │
│  · 料酒 2勺               │
├─────────────────────────┤
│  步骤                     │
│  1. 五花肉切块...         │
│  2. 冷水下锅焯水...       │
│  3. 炒糖色...             │
├─────────────────────────┤
│   ┌─────────────────┐   │
│   │   开始跟做 ▶     │   │
│   └─────────────────┘   │
└─────────────────────────┘
```

**数据来源**: `GET /api/v1/recipes/{id}`

**内容结构**:
- 封面大图（全宽，占屏幕 40% 高度）
- 菜名（24px，粗体）
- 标签行（菜系 + 难度，灰色文字）
- 统计行（收藏数 + 预计时间）
- 食材列表（左对齐圆点标记，含用量）
- 步骤列表（编号列表，每步间隔 16px）
- 底部固定"开始跟做"按钮

**交互行为**:
- 封面图区域可点击放大预览
- "开始跟做"按钮 → `navigateTo` 到跟做模式页

### 3.4 跟做模式页

**路由**: `pages/cook/[id]/index`

**布局**:
```
┌─────────────────────────┐
│ ←  红烧肉         3/8   │
├─────────────────────────┤
│    [步骤大图/插图]       │
│  步骤 3: 炒糖色          │
│  锅中放少许油，加入冰糖   │
│  小火炒至融化呈琥珀色     │
│  ┌─────────────────┐    │
│  │   ⏱ 05:00       │    │
│  │  ▶ ❚❚ ↻         │    │
│  └─────────────────┘    │
├─────────────────────────┤
│  ● ● ● ○ ○ ○ ○ ○       │
│  ◀ 上一步        下一步 ▶│
└─────────────────────────┘
```

**数据来源**: 详情页传入菜谱数据 + WebSocket 实时状态

**组件**:
- **CookingNav** — 步骤进度圆点导航（8 个圆点，当前步骤高亮）
- **Timer** — 倒计时器（支持开始/暂停/重置）

**交互行为**:
- 进入页面 → 建立 WS 连接，发送 `{ action: "start" }`
- 点击"下一步"/"上一步" → 发送 WS 指令 + 更新 UI
- 点击计时器 ▶ → 发送 `timer_start`，开始倒计时
- 点击计时器 ❚❚ → 发送 `timer_pause`
- 点击计时器 ↻ → 发送 `timer_stop`，重置倒计时
- 点击返回 → 发送 `{ action: "complete" }` + 断开连接

---

## 4. 数据流与缓存

### 4.1 API 对接映射

| 前端操作 | 后端 API | 方法 |
|---------|---------|------|
| 搜索菜谱 | `POST /api/v1/search/search` | 搜索页 |
| 获取菜谱详情 | `GET /api/v1/recipes/{id}` | 详情页 |
| 收藏/取消收藏 | `POST/DELETE /api/v1/favorites` | 收藏操作 |
| 获取收藏状态 | `GET /api/v1/favorites` | 列表加载 |
| 跟做模式 WebSocket | `WS /ws/recipes/{id}/cook` | 跟做页 |
| 图片搜索 | `POST /api/v1/search/multimodal` | 搜索页 |

### 4.2 三层缓存模型

```
组件请求
  │
  ├─ L1: 内存缓存 (Zustand store)  → 命中: 立即返回
  │     未命中 ↓
  ├─ L2: localStorage (带 TTL)     → 命中: 返回并静默刷新
  │     未命中 ↓
  └─ L3: 后端 API                   → 写入 L2 + L1
```

### 4.3 缓存策略

| 数据类型 | 缓存时间 | 失效策略 |
|---------|---------|---------|
| 搜索结果 | 5 分钟 | 相同 query 复用，新 query 独立 |
| 菜谱详情 | 1 小时 | 用户上传后主动失效 |
| 收藏状态 | 实时更新 | 乐观更新 + 后台同步 |
| 搜索历史 | 持久化 | 用户手动清除 |
| 筛选标签选项 | 1 天 | 后台定时刷新 |

### 4.4 乐观更新流程（收藏）

1. 立即切换 UI 状态（乐观更新）
2. 写入 localStorage（防刷新丢失）
3. 发起后台 API 请求
   - 成功：确认状态，无需操作
   - 失败：回滚 UI + 显示 Toast 提示
4. 更新 Zustand store 广播到其他组件

### 4.5 WebSocket 跟做连接流程

1. 建立 WS 连接 `/ws/recipes/{id}/cook`
2. 发送 `{ action: "start" }` 初始化
3. 监听 WS 消息：
   - `step_update` → 更新当前步骤
   - `timer_tick` → 更新倒计时显示
   - `error` → 显示错误提示
4. 用户操作 → 发送 WS 指令
5. 离开页面 → 发送 `{ action: "complete" }` + 断开连接

### 4.6 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 网络断开 | 显示"网络异常"Toast，使用缓存数据 |
| Token 过期 | 自动跳转微信重新授权 |
| 搜索无结果 | 显示空状态 + 推荐热门搜索 |
| WS 断线重连 | 自动重连 3 次，失败后提示"跟做连接已断开" |
| 后端报错 | 根据错误码分类处理，显示对应 Toast |

---

## 5. 设计令牌（Design Tokens）

### 5.1 色板（下厨房风格）

```css
:root {
  /* 主色 */
  --color-primary: #FF6B35;       /* 暖橙色 */
  --color-primary-light: #FF8F65; /* 浅暖橙 */
  --color-primary-dark: #E55520;  /* 深暖橙 */

  /* 中性色 */
  --color-text: #333333;          /* 正文 */
  --color-text-secondary: #999999; /* 次要文字 */
  --color-text-placeholder: #CCCCCC;

  /* 背景色 */
  --color-bg: #FAFAFA;            /* 页面背景 */
  --color-bg-card: #FFFFFF;       /* 卡片背景 */
  --color-bg-overlay: #F5F5F5;    /* 叠加层背景 */

  /* 状态色 */
  --color-success: #4CAF50;       /* 成功 */
  --color-warning: #FF9800;       /* 警告 */
  --color-error: #F44336;         /* 错误 */
  --color-favorite: #FF4757;      /* 收藏红 */

  /* 边框 */
  --color-border: #EEEEEE;
  --color-divider: #F0F0F0;
}
```

### 5.2 间距

```css
:root {
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-xxl: 48px;
}
```

### 5.3 字体

```css
:root {
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-md: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  --font-size-xxl: 32px;

  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-bold: 700;
}
```

### 5.4 圆角

```css
:root {
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;
}
```

### 5.5 阴影

```css
:root {
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.12);
  --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.16);
}
```

---

## 6. 组件规范

### 6.1 RecipeCard

**Props**:
```typescript
interface RecipeCardProps {
  id: string;
  name: string;
  description: string;
  coverImage: string;
  cuisine: string;
  difficulty: '简单' | '中等' | '困难';
  isFavorite: boolean;
  onFavoriteToggle: (id: string) => void;
  onPress: (id: string) => void;
}
```

### 6.2 SearchBar

**Props**:
```typescript
interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: (value: string) => void;
  onVoiceSearch?: () => void;
  onImageSearch?: () => void;
  placeholder?: string;
}
```

### 6.3 CookingNav

**Props**:
```typescript
interface CookingNavProps {
  totalSteps: number;
  currentStep: number;
  onStepChange: (step: number) => void;
  onNext: () => void;
  onPrev: () => void;
}
```

### 6.4 Timer

**Props**:
```typescript
interface TimerProps {
  initialSeconds: number;
  onTick?: (remaining: number) => void;
  onComplete?: () => void;
  onStart?: () => void;
  onPause?: () => void;
  onReset?: () => void;
}
```

---

## 7. 状态管理

### 7.1 useSearchStore

```typescript
interface SearchState {
  query: string;
  results: RecipeCard[];
  loading: boolean;
  hasMore: boolean;
  page: number;
  filters: { cuisine?: string; difficulty?: string; sort?: string };

  setQuery: (query: string) => void;
  search: (query: string, filters?: Filters) => Promise<void>;
  loadMore: () => Promise<void>;
  setFilters: (filters: Filters) => void;
  reset: () => void;
}
```

### 7.2 useUserStore

```typescript
interface UserState {
  token: string | null;
  favorites: Set<string>;

  setToken: (token: string) => void;
  toggleFavorite: (id: string) => Promise<void>;
  isFavorite: (id: string) => boolean;
  loadFavorites: () => Promise<void>;
}
```

### 7.3 useCookStore

```typescript
interface CookState {
  isConnected: boolean;
  currentStep: number;
  totalSteps: number;
  timerRemaining: number;
  timerRunning: boolean;
  completedSteps: Set<number>;

  connect: (recipeId: string) => void;
  disconnect: () => void;
  nextStep: () => void;
  prevStep: () => void;
  startTimer: () => void;
  pauseTimer: () => void;
  resetTimer: () => void;
  completeCook: () => void;
}
```

---

## 8. 子项目 B 和 C 说明

本设计仅覆盖子项目 A（搜索结果 + 菜谱详情 + 跟做模式）。后续子项目：

- **子项目 B**: 监控仪表盘 — 独立于用户流程的运维视图，复用设计令牌
- **子项目 C**: 已合入本设计（跟做模式）

---

## 9. 非功能性要求

| 指标 | 目标值 |
|------|--------|
| 首屏加载时间（H5） | < 2s |
| 首屏加载时间（小程序） | < 1.5s |
| 列表滑动帧率 | > 55 fps |
| 图片懒加载 | 进入视口前 100px 预加载 |
| 包体积（小程序） | < 2MB |

---

## 10. 后续依赖

子项目 A 完成后，后续工作：
1. **子项目 B**: 监控仪表盘页面（独立 spec）
2. **后端适配**: 确保搜索 API 返回封面图 URL、难度、收藏状态等字段
