# 菜谱图片切换至 king-jingxiang/HowToCook

## 目标

将 CookRAG 所有菜谱的图片替换为 king-jingxiang/HowToCook 仓库中的图片。第一步使用其 GitHub Pages CDN，第二步暂不实现图片生成管线（后续 sprint 规划）。

## 当前状态

- 图片存储在本地 `data/howtocook/public/images/dishes/`，按类别分目录
- `RecipeImage` 模型 `image_url` 字段存储 CDN URL
- 当前 CDN 配置: `https://cdn.jsdelivr.net/gh/aspire-t/cook-rag-images@main/`
- 静态文件通过 `/howtocook-images` 挂载提供

## 目标源

- king-jingxiang/HowToCook: GitHub Pages 托管的图片，4K 分辨率 9:16 比例
- 图片路径: `public/images/dishes/{category}/{dish_name}.jpeg`

## 架构设计

### Phase 1: 数据迁移脚本

位置: `scripts/migrate_images_to_howtocook.py`

流程:
1. 从本地 `data/howtocook/public/images/` 读取图片目录结构
2. 遍历 `recipe_images` 表，按文件名匹配
3. 匹配成功 → 构建 GitHub Pages URL 写入 `image_url`
4. 匹配失败 → 保留原 URL，记录到缺失列表
5. 输出覆盖率统计: 成功/失败数量 + 缺失菜谱名列表

URL 格式:
```
https://king-jingxiang.github.io/HowToCook/images/dishes/{category}/{dish_name}.jpeg
```

### Phase 2: API 层适配

1. 更新 `app/core/config.py`:
   - `IMAGE_BASE_CDN_URL` → `https://king-jingxiang.github.io/HowToCook/`
   - `IMAGE_REPO_OWNER` → `king-jingxiang`
   - `IMAGE_REPO_NAME` → `HowToCook`

2. 更新搜索 API 返回逻辑，确保 `cover_image` / `images` 字段使用新 URL

3. 前端增加 fallback 机制: 新 URL 加载失败时回退到本地 `/howtocook-images` 路径

### Phase 3: 静态文件兜底（保留现有）

保留 `/howtocook-images` 静态文件挂载，作为 GitHub Pages 不可用时的离线兜底。

## 数据流

```
本地 howtocook repo (data/howtocook/public/images/)
  → 按文件名匹配 recipe_images.source_path
  → 构建 GitHub Pages URL
  → 批量更新 recipe_images.image_url
  → API 返回新 URL
  → 前端展示 (fallback → 本地静态文件)
```

## 错误处理

- 图片 404: 前端 fallback 到本地 `/howtocook-images/{category}/{dish_name}.jpeg`
- 匹配失败: 迁移脚本记录到 CSV 文件，便于人工补全
- 网络不可用: 本地静态文件兜底

## 验证方式

1. 运行迁移脚本，查看覆盖率统计
2. 调用搜索 API，确认返回的 `image_url` 为新 GitHub Pages 地址
3. 浏览器随机抽检 10 道菜，确认图片正常加载

## 暂不实现（后续 Sprint）

- AI 菜谱图片生成管线（NanoBananaPro / Gemini / SD）
- 图片质量校验（CLIP 评分过滤）
