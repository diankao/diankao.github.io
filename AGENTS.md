# AGENTS.md — 本仓库写作与构建规范（AI 会话必读）

博客：Hugo + PaperMod，部署在 GitHub Pages（push 到 main 自动构建上线）。文章都在 `content/posts/`。

## AI 代写文章时必须遵守

1. 新建文章用 `hugo new content posts/<kebab-case-slug>.md`（或照 `archetypes/posts.md` 创建文件）。
2. front matter 必须包含：`title`（中文标题）、`date`、`slug`（**必须等于文件名去扩展名**）、`draft: false`、`tags`（YAML 列表）。
3. 可选 `syndicate: cnblogs`：保留 = 该文自动同步到博客园；省略 = 仅主站。**禁止 `draft: true` 与 `syndicate` 同时出现**。
4. 禁止使用 `url`、`weight`、`categories`、`lastmod` 字段；**发布后禁止改文件名和 slug**（它是主站 URL 和博客园去重的锚）。
5. 正文标题层级从 `##` 开始（`#` 已被 title 占用）。
6. 图片存 `static/images/<slug>/`，用标准语法 `![alt](/images/<slug>/x.png)`；**禁止 Hugo 短代码**（`{{< figure >}}` 等，同步版会丢内容）。
7. 代码块必须标注语言；中英文之间加空格。
8. 配图删除时同步清理对应 `static/images/<slug>/` 目录。

## 构建与验证

- 本地构建：`hugo --minify --gc`（产物 `public/`，已 gitignore，勿提交）
- 本地预览：`hugo server -D` → http://localhost:1313
- 远端：push 到 main 触发 `.github/workflows/deploy.yml` 自动部署

## 提交校验

pre-commit 钩子（`hooks/pre-commit` → `scripts/check_posts.py`）会拦截不合规文章：缺必填字段、slug 与文件名不一致、draft+syndicate 并存。修好再提交。

## 博客园同步（Task 5–7 实施后生效）

- `.cnblogs-map.json` 是 slug → 博客园文章 ID 映射，由 Actions 维护，勿手改。
- 同步逻辑剔除 Hugo 短代码和 HTML 注释，正文尽量用通用 Markdown。
- 下架：`draft: true` 后主站即隐，但博客园侧需手动删除并清映射条目。

## 其他

- `themes/PaperMod` 是 git 子模块，禁止直接修改其中文件；定制一律放 `layouts/partials/` 覆盖。
- 站点配置在 `hugo.toml`；日期格式 `DateFormat` 已汉化，勿改回 Go 缺省。
