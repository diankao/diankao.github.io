# AGENTS.md — 本仓库写作与构建规范（AI 会话必读）

博客：Hugo + PaperMod，部署在 GitHub Pages（push 到 main 自动构建上线）。文章都在 `content/posts/`。

## AI 代写文章时必须遵守

1. 新建文章用 `hugo new content posts/<kebab-case-slug>.md`（或照 `archetypes/posts.md` 创建文件）。
2. front matter 必须包含：`title`（中文标题）、`date`（**不得晚于当前时间**）、`slug`（**必须等于文件名去扩展名**）、`draft`、`tags`（YAML 列表）。
3. **AI 初稿一律 `draft: true`**：草稿不会被构建和部署，可放心提交推送。**禁止 AI 写 `reviewed` 字段**。
4. 发布是人工动作：站长本人审核修改后，由人把 `draft` 改为 `false` 并在 front matter 添加 `reviewed: true`。非 draft 文章缺 `reviewed: true` 会被 pre-commit 和 CI 双重拦截，上不了线。
5. 可选 `syndicate: cnblogs`：保留 = 该文自动同步到博客园；省略 = 仅主站。**禁止 `draft: true` 与 `syndicate` 同时出现**（是否同步在发布时由人决定）。
6. 禁止使用 `url`、`weight`、`categories`、`lastmod` 字段（额外字段只允许人工标记用的 `reviewed`）；**发布后禁止改文件名和 slug**（它是主站 URL 和博客园去重的锚）。
7. 正文标题层级从 `##` 开始（`#` 已被 title 占用）。
8. 图片存 `static/images/<slug>/`，用标准语法 `![alt](/images/<slug>/x.png)`；**禁止 Hugo 短代码**（`{{< figure >}}` 等，同步版会丢内容）。
9. 代码块必须标注语言；中英文之间加空格。
10. 配图删除时同步清理对应 `static/images/<slug>/` 目录。

## 构建与验证

- 本地构建：`hugo --minify --gc`（产物 `public/`，已 gitignore，勿提交）
- 本地预览：`hugo server -D` → http://localhost:1313
- 远端：push 到 main 触发 `.github/workflows/deploy.yml` 自动部署

## 提交校验

pre-commit 钩子（`hooks/pre-commit` → `scripts/check_posts.py`）拦截暂存的不合规文章；CI（`deploy.yml`）在构建前用 `--all` 全量复查，被拦则部署失败、线上保持上一个成功版本。拦截项：缺必填字段、slug 与文件名不一致、draft+syndicate 并存、draft 带 reviewed、**非 draft 缺 `reviewed: true`**、date 在未来。修好再提交。

## 博客园同步（Task 5–7 实施后生效）

- `.cnblogs-map.json` 是 slug → 博客园文章 ID 映射，由 Actions 维护，勿手改。
- 同步逻辑剔除 Hugo 短代码和 HTML 注释，正文尽量用通用 Markdown。
- 下架：`draft: true` 后主站即隐，但博客园侧需手动删除并清映射条目。

## 其他

- `themes/PaperMod` 是 git 子模块，禁止直接修改其中文件；定制一律放 `layouts/partials/` 覆盖。
- 站点配置在 `hugo.toml`；日期格式 `DateFormat` 已汉化，勿改回 Go 缺省。
