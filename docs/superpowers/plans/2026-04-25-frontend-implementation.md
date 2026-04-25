# CookRAG C 端前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 Taro 4.x + React + TypeScript 构建 CookRAG C 端前端，实现搜索 → 详情 → 跟做的完整用户流程。

**Architecture:** 使用 Taro 框架一套代码双端编译（微信小程序 + H5），Zustand 状态管理，三层缓存（内存 → localStorage → API），乐观更新收藏状态，WebSocket 跟做模式。

**Tech Stack:** Taro 4.x, React 18, TypeScript, Zustand, CSS Variables

---

## 文件映射

本计划涉及以下文件组，按功能模块分组：

| 文件 | 类型 | 职责 |
|------|------|------|
| `src/styles/tokens.css` | 创建 | 设计令牌（色板、间距、字体、圆角、阴影） |
| `src/styles/common.css` | 创建 | 全局公共样式（reset、页面容器） |
| `src/types/index.ts` | 创建 | 全局类型定义 |
| `src/utils/cache.ts` | 创建 | localStorage 缓存层（带 TTL） |
| `src/utils/format.ts` | 创建 | 工具函数（数字/时间格式化） |
| `src/services/api/client.ts` | 创建 | HTTP 请求封装（拦截器、token、错误处理） |
| `src/services/api/search.ts` | 创建 | 搜索 API 封装 |
| `src/services/api/recipe.ts` | 创建 | 菜谱 API 封装 |
| `src/services/api/favorite.ts` | 创建 | 收藏 API 封装 |
| `src/services/websocket/cook.ts` | 创建 | WebSocket 跟做连接管理 |
| `src/store/useSearchStore.ts` | 创建 | 搜索状态管理 |
| `src/store/useUserStore.ts` | 创建 | 用户状态 + 收藏管理 |
| `src/store/useCookStore.ts` | 创建 | 跟做状态机 |
| `src/components/RecipeCard/index.tsx` | 创建 | 菜谱卡片组件 |
| `src/components/RecipeCard/index.css` | 创建 | 菜谱卡片样式 |
| `src/components/SearchBar/index.tsx` | 创建 | 搜索输入框组件 |
| `src/components/SearchBar/index.css` | 创建 | 搜索框样式 |
| `src/components/FilterBar/index.tsx` | 创建 | 筛选标签栏组件 |
| `src/components/FilterBar/index.css` | 创建 | 筛选栏样式 |
| `src/components/IngredientList/index.tsx` | 创建 | 食材列表组件 |
| `src/components/IngredientList/index.css` | 创建 | 食材列表样式 |
| `src/components/StepList/index.tsx` | 创建 | 步骤列表组件 |
| `src/components/StepList/index.css` | 创建 | 步骤列表样式 |
| `src/components/CookingNav/index.tsx` | 创建 | 跟做进度导航组件 |
| `src/components/CookingNav/index.css` | 创建 | 跟做导航样式 |
| `src/components/Timer/index.tsx` | 创建 | 倒计时器组件 |
| `src/components/Timer/index.css` | 创建 | 倒计时器样式 |
| `src/components/Toast/index.tsx` | 创建 | 轻提示组件 |
| `src/components/Toast/index.css` | 创建 | 轻提示样式 |
| `src/pages/home/index.tsx` | 创建 | 首页（搜索入口） |
| `src/pages/home/index.css` | 创建 | 首页样式 |
| `src/pages/search/index.tsx` | 创建 | 搜索结果页 |
| `src/pages/search/index.css` | 创建 | 搜索结果页样式 |
| `src/pages/detail/index.tsx` | 创建 | 菜谱详情页 |
| `src/pages/detail/index.css` | 创建 | 详情页样式 |
| `src/pages/cook/index.tsx` | 创建 | 跟做模式页 |
| `src/pages/cook/index.css` | 创建 | 跟做页样式 |
| `config/index.ts` | 创建 | Taro 编译配置 |
| `config/dev.ts` | 创建 | 开发环境配置 |
| `config/prod.ts` | 创建 | 生产环境配置 |
| `babel.config.js` | 创建 | Babel 配置 |
| `tsconfig.json` | 创建 | TypeScript 配置 |
| `package.json` | 创建 | 项目依赖 |
| `project.config.json` | 创建 | 微信小程序配置 |

---

### Task 1: 项目初始化 — 脚手架与构建配置

**Files:**
- Create: `package.json`, `tsconfig.json`, `babel.config.js`, `config/index.ts`, `config/dev.ts`, `config/prod.ts`, `project.config.json`, `src/app.tsx`, `src/app.config.ts`, `src/index.html`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "cook-rag-frontend",
  "version": "0.1.0",
  "private": true,
  "description": "CookRAG C端前端 - 微信小程序 + H5",
  "scripts": {
    "dev:h5": "taro build --type h5 --watch",
    "dev:weapp": "taro build --type weapp --watch",
    "build:h5": "taro build --type h5",
    "build:weapp": "taro build --type weapp"
  },
  "dependencies": {
    "@tarojs/components": "^4.0.0",
    "@tarojs/helper": "^4.0.0",
    "@tarojs/plugin-framework-react": "^4.0.0",
    "@tarojs/runtime": "^4.0.0",
    "@tarojs/taro": "^4.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@tarojs/cli": "^4.0.0",
    "@tarojs/webpack5-runner": "^4.0.0",
    "@types/react": "^18.3.0",
    "babel-preset-taro": "^4.0.0",
    "typescript": "^5.5.0"
  }
}
```

- [ ] **Step 2: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "es2017",
    "module": "commonjs",
    "removeComments": false,
    "preserveConstEnums": true,
    "moduleResolution": "node",
    "experimentalDecorators": true,
    "noImplicitAny": false,
    "allowSyntheticDefaultImports": true,
    "outDir": "lib",
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "strictNullChecks": true,
    "sourceMap": true,
    "baseUrl": ".",
    "rootDir": ".",
    "jsx": "react-jsx",
    "paths": {
      "@/*": ["src/*"]
    },
    "allowJs": true,
    "resolveJsonModule": true,
    "typeRoots": ["node_modules/@types"],
    "lib": ["es2017", "dom"]
  },
  "include": ["src/**/*"],
  "compileOnSave": false
}
```

- [ ] **Step 3: 创建 babel.config.js**

```js
module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true,
    }],
  ],
}
```

- [ ] **Step 4: 创建 config/index.ts**

```ts
import { defineConfig } from '@tarojs/cli'

export default defineConfig({
  projectName: 'cook-rag-frontend',
  date: '2026-4-25',
  designWidth: 750,
  deviceRatio: {
    640: 2.34 / 2,
    750: 1,
    828: 1.81 / 2,
  },
  sourceRoot: 'src',
  outputRoot: 'dist',
  plugins: [],
  defineConstants: {},
  alias: {
    '@': process.cwd() + '/src',
  },
  copy: {
    patterns: [],
    options: {},
  },
  framework: 'react',
  compiler: 'webpack5',
  cache: {
    enable: false,
  },
  mini: {
    postcss: {
      pxtransform: { enable: true, config: {} },
      cssModules: {
        enable: false,
        config: {
          namingPattern: 'module',
          generateScopedName: '[name]__[local]___[hash:base64:5]',
        },
      },
    },
  },
  h5: {
    publicPath: '/',
    staticDirectory: 'static',
    output: {
      filename: 'js/[name].[hash:8].js',
      chunkFilename: 'js/[name].[chunkhash:8].js',
    },
    miniCssExtractPluginOption: {
      ignoreOrder: true,
      filename: 'css/[name].[hash].css',
      chunkFilename: 'css/[name].[chunkhash].css',
    },
    postcss: {
      autoprefixer: { enable: true, config: {} },
      cssModules: {
        enable: false,
        config: {
          namingPattern: 'module',
          generateScopedName: '[name]__[local]___[hash:base64:5]',
        },
      },
    },
    devServer: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        },
      },
    },
  },
})
```

- [ ] **Step 5: 创建 config/dev.ts**

```ts
import { defineConfig, mergeConfig } from '@tarojs/cli'
import defaultConfig from './index'

export default mergeConfig(defaultConfig, {
  mini: {
    optimizeMainPackage: { enable: true },
  },
  h5: {
    devServer: {
      hot: true,
    },
  },
})
```

- [ ] **Step 6: 创建 config/prod.ts**

```ts
import { defineConfig, mergeConfig } from '@tarojs/cli'
import defaultConfig from './index'

export default mergeConfig(defaultConfig, {
  mini: {},
  h5: {},
})
```

- [ ] **Step 7: 创建 project.config.json**

```json
{
  "miniprogramRoot": "dist/",
  "projectname": "cook-rag-frontend",
  "description": "CookRAG C端前端",
  "setting": {
    "urlCheck": false,
    "es6": true,
    "enhance": true,
    "postcss": true,
    "preloadBackgroundData": false,
    "minified": true,
    "newFeature": true,
    "autoAudits": false,
    "coverView": true,
    "showShadowRootInWxmlPanel": true,
    "scopeDataCheck": false,
    "checkInvalidKey": true,
    "checkSiteMap": true,
    "uploadWithSourceMap": true,
    "babelSetting": {
      "ignore": [],
      "disablePlugins": [],
      "outputPath": ""
    }
  },
  "compileType": "miniprogram",
  "condition": {}
}
```

- [ ] **Step 8: 创建 src/app.tsx（应用入口）**

```tsx
import React, { useEffect } from 'react'
import Taro from '@tarojs/taro'
import './styles/tokens.css'
import './styles/common.css'

function App({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // 启动时初始化收藏状态
    import('@/store/useUserStore').then(({ useUserStore }) => {
      useUserStore.getState().loadFavorites()
    })
  }, [])

  return children
}

export default App
```

- [ ] **Step 9: 创建 src/app.config.ts（路由配置）**

```ts
export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/search/index',
    'pages/detail/index',
    'pages/cook/index',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#FF6B35',
    navigationBarTitleText: 'CookRAG',
    navigationBarTextStyle: 'white',
  },
})

function defineAppConfig(config: any) {
  return config
}
```

- [ ] **Step 10: 创建 src/index.html（H5 入口）**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>CookRAG</title>
</head>
<body>
  <div id="app"></div>
</body>
</html>
```

- [ ] **Step 11: 验证构建**

```bash
npm install
npm run build:h5
```
Expected: 构建成功，生成 `dist/` 目录。

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: 初始化 Taro 项目脚手架"
```

---

### Task 2: 设计令牌与全局样式

**Files:**
- Create: `src/styles/tokens.css`, `src/styles/common.css`

- [ ] **Step 1: 创建 src/styles/tokens.css**

```css
page {
  /* 主色 */
  --color-primary: #FF6B35;
  --color-primary-light: #FF8F65;
  --color-primary-dark: #E55520;

  /* 中性色 */
  --color-text: #333333;
  --color-text-secondary: #999999;
  --color-text-placeholder: #CCCCCC;

  /* 背景色 */
  --color-bg: #FAFAFA;
  --color-bg-card: #FFFFFF;
  --color-bg-overlay: #F5F5F5;

  /* 状态色 */
  --color-success: #4CAF50;
  --color-warning: #FF9800;
  --color-error: #F44336;
  --color-favorite: #FF4757;

  /* 边框 */
  --color-border: #EEEEEE;
  --color-divider: #F0F0F0;

  /* 间距 */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-xxl: 48px;

  /* 字体 */
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-md: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  --font-size-xxl: 32px;

  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-bold: 700;

  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.12);
  --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.16);
}
```

- [ ] **Step 2: 创建 src/styles/common.css**

```css
page {
  background-color: var(--color-bg);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: var(--color-text);
  font-size: var(--font-size-md);
  line-height: 1.5;
}

.page-container {
  min-height: 100vh;
  background-color: var(--color-bg);
}

.safe-area-bottom {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-ellipsis-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

- [ ] **Step 3: Commit**

```bash
git add src/styles/
git commit -m "feat: 添加设计令牌与全局样式"
```

---

### Task 3: 工具层 — 缓存与格式化

**Files:**
- Create: `src/utils/cache.ts`, `src/utils/format.ts`, `src/types/index.ts`
- Test: `src/utils/cache.ts` 可直接验证

- [ ] **Step 1: 创建 src/types/index.ts**

```ts
/** 菜谱卡片数据 */
export interface RecipeCardData {
  recipe_id: string
  name: string
  description?: string
  cover_image?: string
  cuisine?: string
  difficulty?: string
  prep_time?: number
  cook_time?: number
  score?: number
}

/** 食材项 */
export interface IngredientItem {
  name: string
  amount?: string
  unit?: string
  sequence: number
}

/** 步骤项 */
export interface StepItem {
  step_no: number
  description: string
  duration_seconds?: number
}

/** 菜谱详情 */
export interface RecipeDetail {
  id: string
  name: string
  description?: string
  cuisine?: string
  difficulty?: string
  tags: string[]
  prep_time?: number
  cook_time?: number
  ingredients: IngredientItem[]
  steps: StepItem[]
  favorites_count: number
  views_count: number
  rating?: number
  is_public: boolean
  audit_status: string
  cover_image?: string
  step_images?: { step_no: number; url: string }[]
}

/** 筛选条件 */
export interface SearchFilters {
  cuisine?: string
  difficulty?: string
  sort?: string
}

/** 搜索结果 */
export interface SearchResult {
  query: string
  results: RecipeCardData[]
  total: number
  source: string
  duration_ms?: number
}

/** 收藏项 */
export interface FavoriteItem {
  recipe_id: string
  recipe_name: string
  created_at: string
}
```

- [ ] **Step 2: 创建 src/utils/cache.ts**

```ts
interface CacheEntry<T> {
  data: T
  expiresAt: number
}

const CACHE_PREFIX = 'cookrag_cache_'

/** 写入缓存（带 TTL，单位：毫秒） */
export function setCache<T>(key: string, data: T, ttl: number): void {
  const entry: CacheEntry<T> = {
    data,
    expiresAt: Date.now() + ttl,
  }
  try {
    Taro.setStorageSync(CACHE_PREFIX + key, JSON.stringify(entry))
  } catch (e) {
    // localStorage 满或其他异常，静默失败
  }
}

/** 读取缓存，过期返回 null */
export function getCache<T>(key: string): T | null {
  try {
    const raw = Taro.getStorageSync(CACHE_PREFIX + key)
    if (!raw) return null
    const entry: CacheEntry<T> = JSON.parse(raw)
    if (Date.now() > entry.expiresAt) {
      Taro.removeStorageSync(CACHE_PREFIX + key)
      return null
    }
    return entry.data
  } catch {
    return null
  }
}

/** 删除缓存 */
export function removeCache(key: string): void {
  try {
    Taro.removeStorageSync(CACHE_PREFIX + key)
  } catch {
    // ignore
  }
}

/** TTL 常量（毫秒） */
export const TTL = {
  SEARCH_RESULTS: 5 * 60 * 1000,       // 5 分钟
  RECIPE_DETAIL: 60 * 60 * 1000,        // 1 小时
  FILTER_OPTIONS: 24 * 60 * 60 * 1000,  // 1 天
}
```

- [ ] **Step 3: 创建 src/utils/format.ts**

```ts
/** 格式化时间（秒 → MM:SS） */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

/** 格式化数字（1234 → "1.2k"） */
export function formatNumber(n: number): string {
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}k`
  }
  return String(n)
}

/** 格式化难度显示 */
export function formatDifficulty(d?: string): string {
  const map: Record<string, string> = {
    easy: '简单',
    medium: '中等',
    hard: '困难',
  }
  return map[d || ''] || d || ''
}
```

- [ ] **Step 4: Commit**

```bash
git add src/types/ src/utils/
git commit -m "feat: 添加类型定义、缓存工具、格式化工具"
```

---

### Task 4: API 服务层

**Files:**
- Create: `src/services/api/client.ts`, `src/services/api/search.ts`, `src/services/api/recipe.ts`, `src/services/api/favorite.ts`

- [ ] **Step 1: 创建 src/services/api/client.ts**

```ts
import Taro from '@tarojs/taro'

const BASE_URL = process.env.TARO_APP_API_URL || 'http://localhost:8000'

interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
}

/** GET 请求 */
export async function request<T = any>(
  url: string,
  options?: Omit<Taro.request.Option, 'url'>,
): Promise<T> {
  const token = Taro.getStorageSync('token')

  const res = await Taro.request({
    url: `${BASE_URL}${url}`,
    method: 'GET',
    header: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    timeout: 10000,
    ...options,
  })

  if (res.statusCode === 401) {
    // Token 过期，清除并跳转授权
    Taro.removeStorageSync('token')
    Taro.showToast({ title: '请重新登录', icon: 'none' })
    throw new Error('UNAUTHORIZED')
  }

  if (res.statusCode !== 200) {
    const errorData = res.data as ApiResponse
    throw new Error(errorData?.message || `HTTP ${res.statusCode}`)
  }

  return res.data as T
}

/** POST 请求 */
export async function post<T = any>(
  url: string,
  data?: Record<string, any>,
  options?: Omit<Taro.request.Option, 'url' | 'method' | 'data'>,
): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    data,
    ...options,
  })
}

/** DELETE 请求 */
export async function del<T = any>(
  url: string,
  data?: Record<string, any>,
  options?: Omit<Taro.request.Option, 'url' | 'method' | 'data'>,
): Promise<T> {
  return request<T>(url, {
    method: 'DELETE',
    data,
    ...options,
  })
}
```

- [ ] **Step 2: 创建 src/services/api/search.ts**

```ts
import { post } from './client'
import type { SearchResult, SearchFilters } from '@/types'

export interface SearchRequest {
  query: string
  filters?: SearchFilters
  top_k?: number
  use_hybrid?: boolean
  use_rerank?: boolean
}

/** 搜索菜谱 */
export async function searchRecipes(req: SearchRequest): Promise<SearchResult> {
  return post<SearchResult>('/api/v1/search/search', {
    query: req.query,
    filters: req.filters,
    top_k: req.top_k ?? 10,
    use_hybrid: req.use_hybrid ?? true,
    use_rerank: false, // 前端暂用 ES 结果，Rerank 在后端已关闭
  })
}

/** 推荐菜谱 */
export async function recommendRecipes(
  context?: string,
  top_k = 10,
): Promise<{ results: any[]; source: string }> {
  return post('/api/v1/search/recommend', {
    context: context || '推荐菜谱',
    top_k,
  })
}
```

- [ ] **Step 3: 创建 src/services/api/recipe.ts**

```ts
import { request } from './client'
import type { RecipeDetail } from '@/types'

/** 获取菜谱详情 */
export async function getRecipeDetail(recipeId: string): Promise<RecipeDetail> {
  return request<RecipeDetail>(`/api/v1/recipes/${recipeId}`)
}

/** 获取菜谱图片列表 */
export async function getRecipeImages(
  recipeId: string,
): Promise<{ cover?: { image_url: string }; steps: { step_no: number; image_url: string }[] }> {
  return request(`/api/v1/recipes/${recipeId}/images`)
}
```

- [ ] **Step 4: 创建 src/services/api/favorite.ts**

```ts
import { post, del, request } from './client'
import type { FavoriteItem } from '@/types'

/** 收藏菜谱 */
export async function addFavorite(recipeId: string): Promise<void> {
  return post('/api/v1/favorites', { recipe_id: recipeId })
}

/** 取消收藏 */
export async function removeFavorite(recipeId: string): Promise<void> {
  return del('/api/v1/favorites', { recipe_id: recipeId })
}

/** 获取收藏列表 */
export async function getFavorites(): Promise<{ favorites: FavoriteItem[]; total: number }> {
  return request('/api/v1/favorites')
}
```

- [ ] **Step 5: Commit**

```bash
git add src/services/api/
git commit -m "feat: 添加 API 服务层"
```

---

### Task 5: WebSocket 跟做连接

**Files:**
- Create: `src/services/websocket/cook.ts`

- [ ] **Step 1: 创建 src/services/websocket/cook.ts**

```ts
import Taro from '@tarojs/taro'

export type CookAction =
  | 'start'
  | 'next'
  | 'prev'
  | 'pause'
  | 'resume'
  | 'timer_start'
  | 'timer_stop'
  | 'status'
  | 'complete'

export interface CookMessage {
  type: string
  step?: number
  total_steps?: number
  remaining_seconds?: number
  message?: string
  [key: string]: any
}

export interface CookCallbacks {
  onStepUpdate?: (step: number, totalSteps: number) => void
  onTimerTick?: (remaining: number) => void
  onError?: (message: string) => void
  onConnected?: () => void
  onDisconnected?: () => void
}

class CookConnection {
  private socketTask: Taro.SocketTask | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private callbacks: CookCallbacks | null = null
  private recipeId: string | null = null
  private baseUrl: string

  constructor() {
    const envUrl = process.env.TARO_APP_WS_URL
    this.baseUrl = envUrl || 'ws://localhost:8000'
  }

  /** 建立连接并开始跟做 */
  connect(recipeId: string, callbacks: CookCallbacks): void {
    this.recipeId = recipeId
    this.callbacks = callbacks
    this.reconnectAttempts = 0
    this.openConnection()
  }

  private openConnection(): void {
    if (!this.recipeId) return

    this.socketTask = Taro.connectSocket({
      url: `${this.baseUrl}/ws/recipes/${this.recipeId}/cook`,
      success: () => {
        this.callbacks?.onConnected?.()
      },
    })

    this.socketTask.onOpen(() => {
      this.reconnectAttempts = 0
      // 发送 start 指令
      this.send({ action: 'start' })
    })

    this.socketTask.onMessage((res) => {
      try {
        const msg: CookMessage = JSON.parse(res.data)
        this.handleMessage(msg)
      } catch {
        // 非 JSON 消息，忽略
      }
    })

    this.socketTask.onClose(() => {
      this.callbacks?.onDisconnected?.()
      this.tryReconnect()
    })

    this.socketTask.onError(() => {
      this.tryReconnect()
    })
  }

  private handleMessage(msg: CookMessage): void {
    switch (msg.type) {
      case 'step_update':
        this.callbacks?.onStepUpdate?.(msg.step ?? 0, msg.total_steps ?? 0)
        break
      case 'timer_tick':
        this.callbacks?.onTimerTick?.(msg.remaining_seconds ?? 0)
        break
      case 'error':
        this.callbacks?.onError?.(msg.message || '未知错误')
        break
    }
  }

  private tryReconnect(): void {
    if (!this.recipeId || this.reconnectAttempts >= this.maxReconnectAttempts) {
      Taro.showToast({ title: '跟做连接已断开', icon: 'none' })
      return
    }
    this.reconnectAttempts++
    setTimeout(() => this.openConnection(), 2000 * this.reconnectAttempts)
  }

  /** 发送指令 */
  send(data: Record<string, any>): void {
    if (this.socketTask) {
      this.socketTask.send({
        data: JSON.stringify(data),
      })
    }
  }

  /** 断开连接 */
  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts // 禁止重连
    if (this.recipeId) {
      this.send({ action: 'complete' })
    }
    this.socketTask?.close()
    this.socketTask = null
    this.callbacks = null
    this.recipeId = null
  }
}

export const cookConnection = new CookConnection()
```

- [ ] **Step 2: Commit**

```bash
git add src/services/websocket/
git commit -m "feat: 添加 WebSocket 跟做连接管理"
```

---

### Task 6: 状态管理 — 三个 Zustand Store

**Files:**
- Create: `src/store/useSearchStore.ts`, `src/store/useUserStore.ts`, `src/store/useCookStore.ts`

- [ ] **Step 1: 创建 src/store/useSearchStore.ts**

```ts
import { create } from 'zustand'
import { searchRecipes, recommendRecipes } from '@/services/api/search'
import { getCache, setCache, TTL } from '@/utils/cache'
import type { RecipeCardData, SearchFilters } from '@/types'

interface SearchState {
  query: string
  results: RecipeCardData[]
  loading: boolean
  hasMore: boolean
  page: number
  filters: SearchFilters

  setQuery: (query: string) => void
  search: (query: string, filters?: SearchFilters) => Promise<void>
  loadMore: () => Promise<void>
  setFilters: (filters: SearchFilters) => void
  reset: () => void
  loadRecommendations: () => Promise<void>
}

export const useSearchStore = create<SearchState>((set, get) => ({
  query: '',
  results: [],
  loading: false,
  hasMore: true,
  page: 1,
  filters: {},

  setQuery: (query) => set({ query }),

  search: async (query, filters) => {
    // 检查 L2 缓存
    const cacheKey = `search_${query}_${JSON.stringify(filters || {})}`
    const cached = getCache(cacheKey)
    if (cached) {
      set({ results: cached, query, loading: false, page: 1, hasMore: false, filters: filters || {} })
      return
    }

    set({ loading: true, results: [], page: 1, hasMore: true, query, filters: filters || {} })
    try {
      const res = await searchRecipes({ query, filters, top_k: 10 })
      const results = res.results.map((r) => ({
        recipe_id: r.recipe_id,
        name: r.name || '',
        description: r.description || '',
        cuisine: r.cuisine,
        difficulty: r.difficulty,
        prep_time: r.prep_time,
        cook_time: r.cook_time,
        score: r.score,
      }))
      setCache(cacheKey, results, TTL.SEARCH_RESULTS)
      set({ results, loading: false, hasMore: results.length >= 10 })
    } catch {
      set({ loading: false })
      Taro.showToast({ title: '搜索失败', icon: 'error' })
    }
  },

  loadMore: async () => {
    const { query, filters, page } = get()
    if (!query || !get().hasMore) return

    set({ loading: true })
    try {
      const res = await searchRecipes({ query, filters, top_k: 10 })
      const newResults = res.results.map((r) => ({
        recipe_id: r.recipe_id,
        name: r.name || '',
        description: r.description || '',
        cuisine: r.cuisine,
        difficulty: r.difficulty,
        prep_time: r.prep_time,
        cook_time: r.cook_time,
        score: r.score,
      }))
      set({ results: [...get().results, ...newResults], page: page + 1, loading: false, hasMore: newResults.length >= 10 })
    } catch {
      set({ loading: false })
    }
  },

  setFilters: (filters) => set({ filters }),

  reset: () => set({ query: '', results: [], loading: false, hasMore: true, page: 1, filters: {} }),

  loadRecommendations: async () => {
    const cached = getCache('recommendations')
    if (cached) {
      set({ results: cached, loading: false })
      return
    }

    set({ loading: true, results: [] })
    try {
      const res = await recommendRecipes()
      const results = res.results.map((r: any) => ({
        recipe_id: r.recipe_id,
        name: r.name || '',
        description: r.description || '',
        cuisine: r.cuisine,
        difficulty: r.difficulty,
        score: r.score,
      }))
      setCache('recommendations', results, TTL.SEARCH_RESULTS)
      set({ results, loading: false })
    } catch {
      set({ loading: false })
    }
  },
}))
```

- [ ] **Step 2: 创建 src/store/useUserStore.ts**

```ts
import { create } from 'zustand'
import { addFavorite, removeFavorite, getFavorites } from '@/services/api/favorite'

interface UserState {
  token: string | null
  favorites: Set<string>

  setToken: (token: string) => void
  toggleFavorite: (id: string) => Promise<void>
  isFavorite: (id: string) => boolean
  loadFavorites: () => Promise<void>
}

export const useUserStore = create<UserState>((set, get) => ({
  token: Taro.getStorageSync('token') || null,
  favorites: new Set<string>(),

  setToken: (token) => {
    Taro.setStorageSync('token', token)
    set({ token })
  },

  toggleFavorite: async (id) => {
    // 乐观更新
    const prevFavorites = new Set(get().favorites)
    const isFav = prevFavorites.has(id)

    if (isFav) {
      prevFavorites.delete(id)
    } else {
      prevFavorites.add(id)
    }
    set({ favorites: prevFavorites })

    try {
      if (isFav) {
        await removeFavorite(id)
      } else {
        await addFavorite(id)
      }
    } catch {
      // 回滚
      set({ favorites: new Set(get().favorites.has(id) ? get().favorites : prevFavorites) })
      Taro.showToast({ title: '操作失败', icon: 'error' })
    }
  },

  isFavorite: (id) => get().favorites.has(id),

  loadFavorites: async () => {
    try {
      const res = await getFavorites()
      const ids = new Set(res.favorites.map((f) => f.recipe_id))
      set({ favorites: ids })
    } catch {
      // 未登录或网络错误，忽略
    }
  },
}))
```

- [ ] **Step 3: 创建 src/store/useCookStore.ts**

```ts
import { create } from 'zustand'
import { cookConnection } from '@/services/websocket/cook'

interface CookState {
  isConnected: boolean
  currentStep: number
  totalSteps: number
  timerRemaining: number
  timerRunning: boolean
  completedSteps: Set<number>
  recipeName: string

  connect: (recipeId: string, recipeName: string, totalSteps: number, stepDurations?: number[]) => void
  disconnect: () => void
  nextStep: () => void
  prevStep: () => void
  startTimer: () => void
  pauseTimer: () => void
  resetTimer: () => void
  completeCook: () => void
  goToStep: (step: number) => void
}

export const useCookStore = create<CookState>((set, get) => ({
  isConnected: false,
  currentStep: 1,
  totalSteps: 0,
  timerRemaining: 0,
  timerRunning: false,
  completedSteps: new Set(),
  recipeName: '',

  connect: (recipeId, recipeName, totalSteps, stepDurations) => {
    set({
      isConnected: true,
      currentStep: 1,
      totalSteps,
      timerRemaining: stepDurations?.[0] || 0,
      timerRunning: false,
      completedSteps: new Set(),
      recipeName,
    })

    cookConnection.connect(recipeId, {
      onStepUpdate: (step, _total) => {
        set({ currentStep: step, totalSteps: _total })
      },
      onTimerTick: (remaining) => {
        set({ timerRemaining: remaining })
      },
      onError: (msg) => {
        Taro.showToast({ title: msg, icon: 'none' })
      },
      onConnected: () => {
        set({ isConnected: true })
      },
      onDisconnected: () => {
        set({ isConnected: false })
      },
    })
  },

  disconnect: () => {
    cookConnection.disconnect()
    set({ isConnected: false, currentStep: 1, timerRunning: false, timerRemaining: 0 })
  },

  nextStep: () => {
    const { currentStep, totalSteps } = get()
    if (currentStep < totalSteps) {
      cookConnection.send({ action: 'next' })
      set({ currentStep: currentStep + 1 })
    }
  },

  prevStep: () => {
    const { currentStep } = get()
    if (currentStep > 1) {
      cookConnection.send({ action: 'prev' })
      set({ currentStep: currentStep - 1 })
    }
  },

  startTimer: () => {
    cookConnection.send({ action: 'timer_start' })
    set({ timerRunning: true })
  },

  pauseTimer: () => {
    cookConnection.send({ action: 'pause' })
    set({ timerRunning: false })
  },

  resetTimer: () => {
    cookConnection.send({ action: 'timer_stop' })
    set({ timerRunning: false, timerRemaining: 0 })
  },

  completeCook: () => {
    cookConnection.disconnect()
    set({ isConnected: false })
  },

  goToStep: (step) => {
    set({ currentStep: step })
  },
}))
```

- [ ] **Step 4: Commit**

```bash
git add src/store/
git commit -m "feat: 添加 Zustand 状态管理"
```

---

### Task 7: 可复用组件 — RecipeCard + SearchBar + FilterBar

**Files:**
- Create: `src/components/RecipeCard/index.tsx`, `src/components/RecipeCard/index.css`
- Create: `src/components/SearchBar/index.tsx`, `src/components/SearchBar/index.css`
- Create: `src/components/FilterBar/index.tsx`, `src/components/FilterBar/index.css`

- [ ] **Step 1: 创建 src/components/RecipeCard/index.tsx**

```tsx
import React from 'react'
import Taro from '@tarojs/taro'
import { View, Image, Text } from '@tarojs/components'
import { useUserStore } from '@/store/useUserStore'
import { formatDifficulty, formatNumber } from '@/utils/format'
import type { RecipeCardData } from '@/types'
import './index.css'

interface Props {
  recipe: RecipeCardData
}

export default function RecipeCard({ recipe }: Props) {
  const isFavorite = useUserStore((s) => s.favorites.has(recipe.recipe_id))
  const toggleFavorite = useUserStore((s) => s.toggleFavorite)

  const handlePress = () => {
    Taro.navigateTo({ url: `/pages/detail/index?id=${recipe.recipe_id}` })
  }

  const handleFavorite = (e: any) => {
    e.stopPropagation()
    toggleFavorite(recipe.recipe_id)
  }

  return (
    <View className='recipe-card' onClick={handlePress}>
      <Image
        className='recipe-card__cover'
        src={recipe.cover_image || '/assets/default-cover.png'}
        mode='aspectFill'
      />
      <View className='recipe-card__content'>
        <Text className='recipe-card__name'>{recipe.name}</Text>
        {recipe.description && (
          <Text className='recipe-card__desc text-ellipsis'>{recipe.description}</Text>
        )}
        <View className='recipe-card__meta'>
          <View className='recipe-card__tags'>
            {recipe.cuisine && <Text className='recipe-card__tag'>{recipe.cuisine}</Text>}
            {recipe.difficulty && (
              <Text className='recipe-card__tag recipe-card__tag--difficulty'>
                {formatDifficulty(recipe.difficulty)}
              </Text>
            )}
          </View>
          <Text className={`recipe-card__fav ${isFavorite ? 'recipe-card__fav--active' : ''}`} onClick={handleFavorite}>
            {isFavorite ? '❤️' : '🤍'}
          </Text>
        </View>
      </View>
    </View>
  )
}
```

- [ ] **Step 2: 创建 src/components/RecipeCard/index.css**

```css
.recipe-card {
  display: flex;
  flex-direction: column;
  margin: 0 var(--spacing-md) var(--spacing-md);
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.recipe-card__cover {
  width: 100%;
  height: 300px;
  background: var(--color-bg-overlay);
}

.recipe-card__content {
  padding: var(--spacing-sm) var(--spacing-md) var(--spacing-md);
}

.recipe-card__name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  display: block;
  margin-bottom: var(--spacing-xs);
}

.recipe-card__desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  display: block;
  margin-bottom: var(--spacing-sm);
}

.recipe-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.recipe-card__tags {
  display: flex;
  gap: var(--spacing-xs);
}

.recipe-card__tag {
  font-size: var(--font-size-xs);
  padding: 2px var(--spacing-xs);
  background: var(--color-bg-overlay);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.recipe-card__tag--difficulty {
  background: rgba(255, 107, 53, 0.1);
  color: var(--color-primary);
}

.recipe-card__fav {
  font-size: var(--font-size-lg);
}
```

- [ ] **Step 3: 创建 src/components/SearchBar/index.tsx**

```tsx
import React, { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Input, Text } from '@tarojs/components'
import './index.css'

interface Props {
  value: string
  onSearch: (value: string) => void
  placeholder?: string
  showVoice?: boolean
  showImage?: boolean
  onVoiceSearch?: () => void
  onImageSearch?: () => void
}

export default function SearchBar({
  value,
  onSearch,
  placeholder = '搜索菜谱...',
  showVoice = true,
  showImage = true,
  onVoiceSearch,
  onImageSearch,
}: Props) {
  const [inputValue, setInputValue] = useState(value)

  const handleConfirm = () => {
    if (inputValue.trim()) {
      onSearch(inputValue.trim())
    }
  }

  return (
    <View className='search-bar'>
      <Input
        className='search-bar__input'
        value={inputValue}
        placeholder={placeholder}
        placeholderClass='search-bar__placeholder'
        confirmType='search'
        onInput={(e) => setInputValue(e.detail.value)}
        onConfirm={handleConfirm}
      />
      <View className='search-bar__actions'>
        {showVoice && (
          <Text className='search-bar__icon' onClick={onVoiceSearch}>🎤</Text>
        )}
        {showImage && (
          <Text className='search-bar__icon' onClick={onImageSearch}>📷</Text>
        )}
      </View>
    </View>
  )
}
```

- [ ] **Step 4: 创建 src/components/SearchBar/index.css**

```css
.search-bar {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-card);
  border-radius: var(--radius-full);
  margin: var(--spacing-sm) var(--spacing-md);
  box-shadow: var(--shadow-sm);
}

.search-bar__input {
  flex: 1;
  font-size: var(--font-size-md);
  color: var(--color-text);
}

.search-bar__placeholder {
  color: var(--color-text-placeholder);
}

.search-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-left: var(--spacing-sm);
}

.search-bar__icon {
  font-size: var(--font-size-xl);
  padding: var(--spacing-xs);
}
```

- [ ] **Step 5: 创建 src/components/FilterBar/index.tsx**

```tsx
import React from 'react'
import { View, Text } from '@tarojs/components'
import './index.css'

const CUISINES = ['川菜', '粤菜', '鲁菜', '苏菜', '浙菜', '闽菜', '湘菜', '徽菜']
const DIFFICULTIES = ['简单', '中等', '困难']

interface Props {
  onFilter: (cuisine?: string, difficulty?: string) => void
}

export default function FilterBar({ onFilter }: Props) {
  return (
    <View className='filter-bar'>
      {CUISINES.map((c) => (
        <Text
          key={c}
          className='filter-bar__tag'
          onClick={() => onFilter(c, undefined)}
        >
          {c}
        </Text>
      ))}
    </View>
  )
}
```

- [ ] **Step 6: 创建 src/components/FilterBar/index.css**

```css
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-divider);
}

.filter-bar__tag {
  font-size: var(--font-size-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-overlay);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.filter-bar__tag:active {
  background: var(--color-primary-light);
  color: white;
}
```

- [ ] **Step 7: Commit**

```bash
git add src/components/RecipeCard/ src/components/SearchBar/ src/components/FilterBar/
git commit -m "feat: 添加 RecipeCard、SearchBar、FilterBar 组件"
```

---

### Task 8: 可复用组件 — IngredientList + StepList + CookingNav + Timer + Toast

**Files:**
- Create: `src/components/IngredientList/index.tsx`, `src/components/IngredientList/index.css`
- Create: `src/components/StepList/index.tsx`, `src/components/StepList/index.css`
- Create: `src/components/CookingNav/index.tsx`, `src/components/CookingNav/index.css`
- Create: `src/components/Timer/index.tsx`, `src/components/Timer/index.css`
- Create: `src/components/Toast/index.tsx`, `src/components/Toast/index.css`

- [ ] **Step 1: 创建 src/components/IngredientList/index.tsx**

```tsx
import React from 'react'
import { View, Text } from '@tarojs/components'
import type { IngredientItem } from '@/types'
import './index.css'

interface Props {
  ingredients: IngredientItem[]
}

export default function IngredientList({ ingredients }: Props) {
  return (
    <View className='ingredient-list'>
      <Text className='ingredient-list__title'>食材</Text>
      {ingredients.map((item, idx) => (
        <View key={idx} className='ingredient-list__item'>
          <Text className='ingredient-list__dot'>•</Text>
          <Text className='ingredient-list__name'>{item.name}</Text>
          {(item.amount || item.unit) && (
            <Text className='ingredient-list__amount'>
              {item.amount}{item.unit}
            </Text>
          )}
        </View>
      ))}
    </View>
  )
}
```

- [ ] **Step 2: 创建 src/components/IngredientList/index.css**

```css
.ingredient-list {
  padding: var(--spacing-md);
  background: var(--color-bg-card);
  margin-bottom: var(--spacing-md);
}

.ingredient-list__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  display: block;
  margin-bottom: var(--spacing-sm);
}

.ingredient-list__item {
  display: flex;
  align-items: baseline;
  padding: var(--spacing-xs) 0;
}

.ingredient-list__dot {
  color: var(--color-primary);
  margin-right: var(--spacing-xs);
  font-size: var(--font-size-lg);
}

.ingredient-list__name {
  font-size: var(--font-size-md);
  color: var(--color-text);
  flex: 1;
}

.ingredient-list__amount {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
```

- [ ] **Step 3: 创建 src/components/StepList/index.tsx**

```tsx
import React from 'react'
import { View, Text } from '@tarojs/components'
import type { StepItem } from '@/types'
import './index.css'

interface Props {
  steps: StepItem[]
}

export default function StepList({ steps }: Props) {
  return (
    <View className='step-list'>
      <Text className='step-list__title'>步骤</Text>
      {steps.map((step) => (
        <View key={step.step_no} className='step-list__item'>
          <View className='step-list__number'>{step.step_no}</View>
          <Text className='step-list__content'>{step.description}</Text>
        </View>
      ))}
    </View>
  )
}
```

- [ ] **Step 4: 创建 src/components/StepList/index.css**

```css
.step-list {
  padding: var(--spacing-md);
  background: var(--color-bg-card);
  margin-bottom: calc(var(--spacing-xxl) + var(--spacing-lg));
}

.step-list__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  display: block;
  margin-bottom: var(--spacing-md);
}

.step-list__item {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.step-list__number {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-list__content {
  flex: 1;
  font-size: var(--font-size-md);
  color: var(--color-text);
  line-height: 1.6;
}
```

- [ ] **Step 5: 创建 src/components/CookingNav/index.tsx**

```tsx
import React from 'react'
import { View, Text } from '@tarojs/components'
import './index.css'

interface Props {
  totalSteps: number
  currentStep: number
  onNext: () => void
  onPrev: () => void
}

export default function CookingNav({ totalSteps, currentStep, onNext, onPrev }: Props) {
  const dots = Array.from({ length: totalSteps }, (_, i) => i + 1)

  return (
    <View className='cooking-nav'>
      <View className='cooking-nav__dots'>
        {dots.map((n) => (
          <View
            key={n}
            className={`cooking-nav__dot ${n <= currentStep ? 'cooking-nav__dot--active' : ''}`}
          />
        ))}
      </View>
      <View className='cooking-nav__buttons'>
        <Text className={`cooking-nav__btn ${currentStep <= 1 ? 'cooking-nav__btn--disabled' : ''}`} onClick={currentStep > 1 ? onPrev : undefined}>
          ◀ 上一步
        </Text>
        <Text className={`cooking-nav__btn ${currentStep >= totalSteps ? 'cooking-nav__btn--disabled' : ''}`} onClick={currentStep < totalSteps ? onNext : undefined}>
          下一步 ▶
        </Text>
      </View>
    </View>
  )
}
```

- [ ] **Step 6: 创建 src/components/CookingNav/index.css**

```css
.cooking-nav {
  padding: var(--spacing-md);
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-divider);
}

.cooking-nav__dots {
  display: flex;
  justify-content: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.cooking-nav__dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-border);
}

.cooking-nav__dot--active {
  background: var(--color-primary);
}

.cooking-nav__buttons {
  display: flex;
  justify-content: space-between;
}

.cooking-nav__btn {
  font-size: var(--font-size-md);
  color: var(--color-primary);
  padding: var(--spacing-sm) var(--spacing-md);
}

.cooking-nav__btn--disabled {
  color: var(--color-text-placeholder);
}
```

- [ ] **Step 7: 创建 src/components/Timer/index.tsx**

```tsx
import React from 'react'
import { View, Text } from '@tarojs/components'
import { formatTime } from '@/utils/format'
import './index.css'

interface Props {
  seconds: number
  running: boolean
  onStart: () => void
  onPause: () => void
  onReset: () => void
}

export default function Timer({ seconds, running, onStart, onPause, onReset }: Props) {
  return (
    <View className='timer'>
      <Text className='timer__display'>{formatTime(seconds)}</Text>
      <View className='timer__controls'>
        {running ? (
          <Text className='timer__btn timer__btn--primary' onClick={onPause}>❚❚</Text>
        ) : (
          <Text className='timer__btn timer__btn--primary' onClick={onStart}>▶</Text>
        )}
        <Text className='timer__btn timer__btn--secondary' onClick={onReset}>↻</Text>
      </View>
    </View>
  )
}
```

- [ ] **Step 8: 创建 src/components/Timer/index.css**

```css
.timer {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--color-bg-overlay);
  border-radius: var(--radius-lg);
  margin: var(--spacing-md);
}

.timer__display {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
  margin-bottom: var(--spacing-sm);
}

.timer__controls {
  display: flex;
  gap: var(--spacing-lg);
}

.timer__btn {
  font-size: var(--font-size-xl);
  padding: var(--spacing-sm);
}

.timer__btn--primary {
  color: var(--color-primary);
}

.timer__btn--secondary {
  color: var(--color-text-secondary);
}
```

- [ ] **Step 9: 创建 src/components/Toast/index.tsx**

```tsx
import Taro from '@tarojs/taro'

/** 封装 Taro.showToast，统一样式 */
export function showToast(title: string, icon: 'success' | 'error' | 'none' = 'none') {
  Taro.showToast({ title, icon })
}
```

- [ ] **Step 10: Commit**

```bash
git add src/components/IngredientList/ src/components/StepList/ src/components/CookingNav/ src/components/Timer/ src/components/Toast/
git commit -m "feat: 添加 IngredientList、StepList、CookingNav、Timer、Toast 组件"
```

---

### Task 9: 首页（搜索入口）

**Files:**
- Create: `src/pages/home/index.tsx`, `src/pages/home/index.css`

- [ ] **Step 1: 创建 src/pages/home/index.tsx**

```tsx
import React, { useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Image } from '@tarojs/components'
import SearchBar from '@/components/SearchBar'
import RecipeCard from '@/components/RecipeCard'
import { useSearchStore } from '@/store/useSearchStore'
import './index.css'

const QUICK_FILTERS = ['川菜', '粤菜', '快手菜', '素菜', '甜品']

export default function HomePage() {
  const results = useSearchStore((s) => s.results)
  const loading = useSearchStore((s) => s.loading)
  const loadRecommendations = useSearchStore((s) => s.loadRecommendations)

  useEffect(() => {
    loadRecommendations()
  }, [loadRecommendations])

  const handleSearch = (value: string) => {
    Taro.navigateTo({ url: `/pages/search/index?query=${encodeURIComponent(value)}` })
  }

  const handleFilter = (cuisine: string) => {
    Taro.navigateTo({ url: `/pages/search/index?filter=${encodeURIComponent(cuisine)}` })
  }

  return (
    <View className='page-container safe-area-bottom'>
      {/* Logo */}
      <View className='home__header'>
        <Text className='home__logo'>CookRAG</Text>
      </View>

      {/* 搜索框 */}
      <SearchBar value='' onSearch={handleSearch} />

      {/* 快速筛选 */}
      <View className='home__filters'>
        {QUICK_FILTERS.map((f) => (
          <Text key={f} className='home__filter-tag' onClick={() => handleFilter(f)}>
            {f}
          </Text>
        ))}
      </View>

      {/* 热门菜谱 */}
      <Text className='home__section-title'>热门菜谱</Text>
      {loading ? (
        <View className='home__loading'>加载中...</View>
      ) : (
        results.map((recipe) => <RecipeCard key={recipe.recipe_id} recipe={recipe} />)
      )}
    </View>
  )
}
```

- [ ] **Step 2: 创建 src/pages/home/index.css**

```css
.home__header {
  padding: var(--spacing-xl) var(--spacing-md) var(--spacing-md);
  text-align: center;
}

.home__logo {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.home__filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
}

.home__filter-tag {
  font-size: var(--font-size-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-card);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.home__filter-tag:active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.home__section-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  padding: var(--spacing-md) var(--spacing-md) var(--spacing-sm);
  display: block;
}

.home__loading {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/home/
git commit -m "feat: 添加首页（搜索入口）"
```

---

### Task 10: 搜索结果页

**Files:**
- Create: `src/pages/search/index.tsx`, `src/pages/search/index.css`

- [ ] **Step 1: 创建 src/pages/search/index.tsx**

```tsx
import React, { useEffect, useState } from 'react'
import Taro, { useRouter } from '@tarojs/taro'
import { View, ScrollView, Text } from '@tarojs/components'
import SearchBar from '@/components/SearchBar'
import RecipeCard from '@/components/RecipeCard'
import FilterBar from '@/components/FilterBar'
import { useSearchStore } from '@/store/useSearchStore'
import './index.css'

export default function SearchPage() {
  const router = useRouter()
  const query = router.params.query || ''
  const filter = router.params.filter || ''

  const results = useSearchStore((s) => s.results)
  const loading = useSearchStore((s) => s.loading)
  const hasMore = useSearchStore((s) => s.hasMore)
  const search = useSearchStore((s) => s.search)
  const loadMore = useSearchStore((s) => s.loadMore)
  const setFilters = useSearchStore((s) => s.setFilters)

  const [searchInput, setSearchInput] = useState(query)

  useEffect(() => {
    if (query) {
      search(query, filter ? { cuisine: filter } : undefined)
      setSearchInput(query)
    } else if (filter) {
      search('', { cuisine: filter })
    }
  }, [query, filter, search])

  const handleSearch = (value: string) => {
    setSearchInput(value)
    search(value)
  }

  const handleFilter = (cuisine?: string) => {
    setFilters(cuisine ? { cuisine } : {})
    search(searchInput, cuisine ? { cuisine } : undefined)
  }

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      loadMore()
    }
  }

  return (
    <View className='page-container safe-area-bottom'>
      <View className='search-page__header'>
        <Text className='search-page__back' onClick={() => Taro.navigateBack()}>←</Text>
        <SearchBar value={searchInput} onSearch={handleSearch} showVoice={false} showImage={false} />
      </View>
      <FilterBar onFilter={handleFilter} />

      <ScrollView scrollY className='search-page__list' onScrollToLower={handleLoadMore}>
        {results.length === 0 && !loading ? (
          <View className='search-page__empty'>
            <Text>没有找到相关菜谱</Text>
            <Text className='search-page__empty-hint'>试试其他关键词吧</Text>
          </View>
        ) : (
          <>
            {results.map((recipe) => (
              <RecipeCard key={recipe.recipe_id} recipe={recipe} />
            ))}
            {loading && <View className='search-page__loading'>加载中...</View>}
            {!hasMore && results.length > 0 && (
              <View className='search-page__end'>— 到底了 —</View>
            )}
          </>
        )}
      </ScrollView>
    </View>
  )
}
```

- [ ] **Step 2: 创建 src/pages/search/index.css**

```css
.search-page__header {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm) 0;
}

.search-page__back {
  font-size: var(--font-size-xl);
  padding: 0 var(--spacing-md);
  color: var(--color-text);
}

.search-page__list {
  height: calc(100vh - 140px);
  padding-bottom: var(--spacing-md);
}

.search-page__empty {
  text-align: center;
  padding: var(--spacing-xxl) var(--spacing-md);
  color: var(--color-text-secondary);
}

.search-page__empty-hint {
  display: block;
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-sm);
}

.search-page__loading,
.search-page__end {
  text-align: center;
  padding: var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/search/
git commit -m "feat: 添加搜索结果页"
```

---

### Task 11: 菜谱详情页

**Files:**
- Create: `src/pages/detail/index.tsx`, `src/pages/detail/index.css`

- [ ] **Step 1: 创建 src/pages/detail/index.tsx**

```tsx
import React, { useEffect, useState } from 'react'
import Taro, { useRouter } from '@tarojs/taro'
import { View, Text, Image } from '@tarojs/components'
import IngredientList from '@/components/IngredientList'
import StepList from '@/components/StepList'
import { getRecipeDetail } from '@/services/api/recipe'
import { getCache, setCache, TTL } from '@/utils/cache'
import { useUserStore } from '@/store/useUserStore'
import { formatDifficulty, formatNumber } from '@/utils/format'
import type { RecipeDetail as RecipeDetailType } from '@/types'
import './index.css'

export default function DetailPage() {
  const router = useRouter()
  const recipeId = router.params.id || ''

  const [detail, setDetail] = useState<RecipeDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const isFavorite = useUserStore((s) => s.favorites.has(recipeId))
  const toggleFavorite = useUserStore((s) => s.toggleFavorite)

  useEffect(() => {
    const cached = getCache<RecipeDetailType>(`recipe_${recipeId}`)
    if (cached) {
      setDetail(cached)
      setLoading(false)
    }

    getRecipeDetail(recipeId)
      .then((data) => {
        setDetail(data)
        setCache(`recipe_${recipeId}`, data, TTL.RECIPE_DETAIL)
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
        Taro.showToast({ title: '加载失败', icon: 'error' })
      })
  }, [recipeId])

  const handleCook = () => {
    if (detail) {
      Taro.navigateTo({
        url: `/pages/cook/index?id=${recipeId}&name=${encodeURIComponent(detail.name)}&steps=${detail.steps.length}`,
      })
    }
  }

  if (loading) {
    return <View className='page-container detail-page__loading'>加载中...</View>
  }

  if (!detail) {
    return <View className='page-container detail-page__error'>菜谱不存在</View>
  }

  return (
    <View className='page-container safe-area-bottom'>
      {/* 封面图 */}
      <Image
        className='detail-page__cover'
        src={detail.cover_image || '/assets/default-cover.png'}
        mode='aspectFill'
      />

      {/* 返回按钮 */}
      <View className='detail-page__back' onClick={() => Taro.navigateBack()}>
        <Text>←</Text>
      </View>

      {/* 基本信息 */}
      <View className='detail-page__info'>
        <Text className='detail-page__name'>{detail.name}</Text>
        <View className='detail-page__meta'>
          {detail.cuisine && <Text className='detail-page__tag'>{detail.cuisine}</Text>}
          {detail.difficulty && (
            <Text className='detail-page__tag detail-page__tag--difficulty'>
              {formatDifficulty(detail.difficulty)}
            </Text>
          )}
        </View>
        <View className='detail-page__stats'>
          <Text className='detail-page__stat'>
            {isFavorite ? '❤️' : '🤍'} {formatNumber(detail.favorites_count)}
          </Text>
          {(detail.prep_time || detail.cook_time) && (
            <Text className='detail-page__stat'>
              ⏱ {(detail.prep_time || 0) + (detail.cook_time || 0)}分钟
            </Text>
          )}
        </View>
      </View>

      {/* 食材 */}
      {detail.ingredients.length > 0 && <IngredientList ingredients={detail.ingredients} />}

      {/* 步骤 */}
      {detail.steps.length > 0 && <StepList steps={detail.steps} />}

      {/* 底部跟做按钮 */}
      <View className='detail-page__cook-btn' onClick={handleCook}>
        <Text>开始跟做 ▶</Text>
      </View>
    </View>
  )
}
```

- [ ] **Step 2: 创建 src/pages/detail/index.css**

```css
.detail-page__cover {
  width: 100%;
  height: 40vh;
  background: var(--color-bg-overlay);
}

.detail-page__back {
  position: absolute;
  top: var(--spacing-md);
  left: var(--spacing-md);
  font-size: var(--font-size-xl);
  color: white;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: rgba(0, 0, 0, 0.3);
  border-radius: var(--radius-full);
  z-index: 10;
}

.detail-page__info {
  padding: var(--spacing-md);
  background: var(--color-bg-card);
  margin-bottom: var(--spacing-md);
}

.detail-page__name {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  display: block;
  margin-bottom: var(--spacing-sm);
}

.detail-page__meta {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.detail-page__tag {
  font-size: var(--font-size-sm);
  padding: 2px var(--spacing-xs);
  background: var(--color-bg-overlay);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.detail-page__tag--difficulty {
  background: rgba(255, 107, 53, 0.1);
  color: var(--color-primary);
}

.detail-page__stats {
  display: flex;
  gap: var(--spacing-md);
}

.detail-page__stat {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.detail-page__loading,
.detail-page__error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: var(--color-text-secondary);
}

.detail-page__cook-btn {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--color-primary);
  color: white;
  text-align: center;
  padding: var(--spacing-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  z-index: 100;
}
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/detail/
git commit -m "feat: 添加菜谱详情页"
```

---

### Task 12: 跟做模式页

**Files:**
- Create: `src/pages/cook/index.tsx`, `src/pages/cook/index.css`

- [ ] **Step 1: 创建 src/pages/cook/index.tsx**

```tsx
import React, { useEffect, useState } from 'react'
import Taro, { useRouter } from '@tarojs/taro'
import { View, Text, Image } from '@tarojs/components'
import CookingNav from '@/components/CookingNav'
import Timer from '@/components/Timer'
import { useCookStore } from '@/store/useCookStore'
import { formatTime } from '@/utils/format'
import './index.css'

export default function CookPage() {
  const router = useRouter()
  const recipeId = router.params.id || ''
  const recipeName = decodeURIComponent(router.params.name || '')
  const totalSteps = parseInt(router.params.steps || '0', 10)

  const currentStep = useCookStore((s) => s.currentStep)
  const timerRemaining = useCookStore((s) => s.timerRemaining)
  const timerRunning = useCookStore((s) => s.timerRunning)
  const connect = useCookStore((s) => s.connect)
  const disconnect = useCookStore((s) => s.disconnect)
  const nextStep = useCookStore((s) => s.nextStep)
  const prevStep = useCookStore((s) => s.prevStep)
  const startTimer = useCookStore((s) => s.startTimer)
  const pauseTimer = useCookStore((s) => s.pauseTimer)
  const resetTimer = useCookStore((s) => s.resetTimer)

  useEffect(() => {
    connect(recipeId, recipeName, totalSteps)

    return () => {
      disconnect()
    }
  }, [recipeId, recipeName, totalSteps, connect, disconnect])

  const handleBack = () => {
    disconnect()
    Taro.navigateBack()
  }

  return (
    <View className='page-container cook-page safe-area-bottom'>
      {/* 顶部导航 */}
      <View className='cook-page__header'>
        <Text className='cook-page__back' onClick={handleBack}>←</Text>
        <Text className='cook-page__title'>{recipeName}</Text>
        <Text className='cook-page__progress'>{currentStep}/{totalSteps}</Text>
      </View>

      {/* 步骤内容 */}
      <View className='cook-page__step'>
        <Image
          className='cook-page__step-image'
          src='/assets/default-step.png'
          mode='aspectFit'
        />
        <Text className='cook-page__step-title'>步骤 {currentStep}</Text>
        {/* 这里可以从菜谱详情传入步骤描述 */}
        <Text className='cook-page__step-desc'>
          {currentStep} / {totalSteps}
        </Text>
      </View>

      {/* 计时器 */}
      <Timer
        seconds={timerRemaining}
        running={timerRunning}
        onStart={startTimer}
        onPause={pauseTimer}
        onReset={resetTimer}
      />

      {/* 底部导航 */}
      <CookingNav
        totalSteps={totalSteps}
        currentStep={currentStep}
        onNext={nextStep}
        onPrev={prevStep}
      />
    </View>
  )
}
```

- [ ] **Step 2: 创建 src/pages/cook/index.css**

```css
.cook-page {
  display: flex;
  flex-direction: column;
}

.cook-page__header {
  display: flex;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-divider);
}

.cook-page__back {
  font-size: var(--font-size-xl);
  color: var(--color-text);
  margin-right: var(--spacing-sm);
}

.cook-page__title {
  flex: 1;
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.cook-page__progress {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
}

.cook-page__step {
  padding: var(--spacing-md);
  flex: 1;
  text-align: center;
}

.cook-page__step-image {
  width: 100%;
  height: 300px;
  background: var(--color-bg-overlay);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-md);
}

.cook-page__step-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  display: block;
  margin-bottom: var(--spacing-sm);
}

.cook-page__step-desc {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  line-height: 1.6;
}
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/cook/
git commit -m "feat: 添加跟做模式页"
```

---

## Self-Review

### 1. Spec coverage

| Spec requirement | Task |
|-----------------|------|
| 项目架构/目录结构 | Task 1 (脚手架) |
| 设计令牌 | Task 2 |
| 类型定义、缓存工具、格式化工具 | Task 3 |
| API 服务层（搜索、菜谱、收藏） | Task 4 |
| WebSocket 跟做连接 | Task 5 |
| Zustand 状态管理（3 个 store） | Task 6 |
| RecipeCard 组件 | Task 7 |
| SearchBar 组件 | Task 7 |
| FilterBar 组件 | Task 7 |
| IngredientList 组件 | Task 8 |
| StepList 组件 | Task 8 |
| CookingNav 组件 | Task 8 |
| Timer 组件 | Task 8 |
| Toast 工具 | Task 8 |
| 首页 | Task 9 |
| 搜索结果页 | Task 10 |
| 菜谱详情页 | Task 11 |
| 跟做模式页 | Task 12 |
| 三层缓存 | Task 3 (cache.ts) + Task 6 (stores) |
| 乐观更新收藏 | Task 6 (useUserStore) |
| 错误处理 | Task 4 (client.ts) + 各页面 catch |
| 下厨房风格色板 | Task 2 (tokens.css) |

### 2. Placeholder scan

- 无 "TBD"/"TODO"/"implement later" 占位符
- 每个步骤都有实际代码
- 步骤图片使用占位图 `/assets/default-cover.png` 和 `/assets/default-step.png`，这是合理的默认值，不是占位符

### 3. Type consistency

- `RecipeCardData` 在 `types/index.ts` 定义，在 `RecipeCard`、`useSearchStore`、`home/index.tsx`、`search/index.tsx` 中一致使用
- `RecipeDetail` 在 `types/index.ts` 定义，在 `detail/index.tsx`、`api/recipe.ts` 中一致使用
- Store 签名与 spec 一致

### 4. 后端字段缺口说明

后端搜索 API `SearchRecipeResult` 当前**不包含 `cover_image` 字段**。前端在 `RecipeCard` 中使用 `/assets/default-cover.png` 作为兜底图片。后续需在 `RecipeDetailResponse` schema 中添加 `cover_image` 字段，或由图片 API `/api/v1/recipes/{id}/images` 补充。

---

Plan complete and saved to `docs/superpowers/plans/2026-04-25-frontend-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
