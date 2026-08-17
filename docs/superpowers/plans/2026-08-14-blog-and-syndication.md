# 个人博客与分发体系 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个 Hugo 静态博客主站（Cloudflare Pages 托管、giscus 评论），并通过 GitHub Actions 自动将勾选的文章同步到博客园，形成"主站吃 Google/Bing 流量、平台分发吃百度流量"的分发体系。

**Architecture:** Markdown 文章提交到 GitHub 仓库即完成全部发布：Cloudflare Pages 自动构建主站；独立 workflow 调用博客园 MetaWeblog API 同步全文并回写文章 ID 映射（二次修改走编辑而非重发）。博客与服务器完全解耦，后期购入轻量云服务器仅作为 frp/监控入口，主站无需迁移。

**Tech Stack:** Hugo（PaperMod 主题）· Cloudflare Pages · GitHub Actions · Python 3 标准库（xmlrpc）· giscus · 博客园 MetaWeblog API

---

## 一、已定决策（讨论结论存档）

| 事项 | 决策 | 理由 |
|------|------|------|
| 博客形态 | 静态博客，不上 WordPress/Ghost | 零运维、免服务器、文章资产在 git 里天然可迁移 |
| 框架 | Hugo + PaperMod 主题 | 构建快、主题成熟、配置简单 |
| 托管 | Cloudflare Pages | 国内访问比 Vercel/GitHub Pages 稳，免费，自动 CI |
| 域名/备案 | 先用 `*.pages.dev`，域名后补；不备案 | 博客走海外托管免备案；云服务器将来只跑非网站服务（frp/MC）同样免备案 |
| 评论 | giscus（GitHub Discussions） | 免费、无后端、不泄露读者数据 |
| 一文多发 | 博客园走 Actions + MetaWeblog 全自动；B站/知乎/掘金手动贴 | 有官方 API 的才自动化，无 API 的平台浏览器自动化太脆且有风控/封号风险 |
| 重复内容策略 | 同步版全文末尾附"本文首发于 主站链接" | 接受平台版本在百度排名更高的现实，定位为引流渠道 |
| 服务器演进 | 阶段三再买轻量云（仅 frp 服务端 + Uptime Kuma）；MC/Gitea/RSS 放家里设备 Docker Compose | 云当公网入口，家里当算力；上 k8s 无必要 |
| 迁移路径 | 后期可把同一仓库改成 Actions 构建后 rsync 推到自己服务器 | 静态产物放哪都行，域名换解析即切换 |

## 二、前置条件（需要你本人完成的账号类操作）

- [ ] GitHub 账号（仓库需**公开**，giscus 依赖公开仓库的 Discussions）
- [ ] Cloudflare 账号（免费版即可）
- [ ] 博客园账号，并在后台「设置」中**开启 MetaWeblog**，记下：博客名、用户名、MetaWeblog 访问令牌
- [ ] （可选，后期再办）购买域名 `.com`/`.me`/`.dev`
- 本机已有 Git（Git Bash）；Hugo 与 Python 由 Task 1 安装

## 三、阶段总览

| 阶段 | 内容 | 状态 |
|------|------|------|
| 一（本计划 Task 1–4） | 本地 Hugo 站 → GitHub → Cloudflare Pages 上线 + giscus | 现在实施 |
| 二（本计划 Task 5–7） | 博客园自动同步（含编辑去重） | 现在实施 |
| 三（路线图） | 轻量云服务器：frp 服务端 + Uptime Kuma | 有需求时另立计划 |
| 四（路线图） | 家里设备：MC 服务器 / Gitea / RSS | 有需求时另立计划 |

---

## Task 1: 安装工具并初始化 Hugo 站点

**Files:**
- Create: `hugo.toml`、`.gitignore`、`archetypes/default.md`（hugo 生成）、目录骨架

- [ ] **Step 1: 安装 Hugo Extended 与 Python**

```bash
winget install --id Hugo.Hugo.Extended
winget install --id Python.Python.3.12
```

新开的 Git Bash 中验证：

```bash
hugo version    # 期望: hugin v0.1xx.x+ windows/amd64 ...（记下版本号，部署时要用）
python --version  # 期望: Python 3.12.x
```

- [ ] **Step 2: 初始化 git 仓库与 Hugo 站点**

在 `D:\source-other\selfblog` 下执行：

```bash
git init -b main
hugo new site . --force
```

期望：生成 `hugo.toml`、`archetypes/`、`content/`、`layouts/`、`static/` 等目录，无报错。

- [ ] **Step 3: 添加 PaperMod 主题（子模块）**

```bash
git submodule add --depth=1 https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod
```

- [ ] **Step 4: 写入站点配置**

将 `hugo.toml` 整体替换为：

```toml
baseURL = "https://selfblog.pages.dev/"
languageCode = "zh-cn"
defaultContentLanguage = "zh-cn"
title = "我的博客"
theme = "PaperMod"
enableEmoji = true

[permalinks]
posts = "/posts/:slug/"

[markup]
[markup.highlight]
noClasses = false
[markup.goldmark]
[markup.goldmark.renderer]
unsafe = true

[outputs]
home = ["HTML", "RSS", "JSON"]

[params]
env = "production"
defaultTheme = "auto"
ShowReadingTime = true
ShowPostNavLinks = true
ShowBreadCrumbs = true
ShowCodeCopyButtons = true
ShowShareButtons = false

[params.homeInfoParams]
Title = "你好，我是……"
Content = "在这里记录技术与生活"

[[params.socialIcons]]
name = "github"
url = "https://github.com/你的用户名"
```

说明：`baseURL` 先按 Cloudflare Pages 默认域名填写；Task 3 部署时如项目名被占用导致域名不同，回到这里同步修改。

- [ ] **Step 5: 写 .gitignore**

创建 `.gitignore`：

```
public/
resources/
.hugo_build.lock
__pycache__/
```

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "chore: init hugo site with PaperMod theme"
```

## Task 2: 首篇文章与本地验证

**Files:**
- Create: `content/posts/hello-world.md`

- [ ] **Step 1: 写第一篇文章**

创建 `content/posts/hello-world.md`：

```markdown
---
title: "第一篇文章：博客上线"
date: 2026-08-14
slug: hello-world
draft: false
tags: ["随笔"]
syndicate: cnblogs
---

博客开张。这篇文章用于验证主站与博客园同步链路。

正文用 Markdown 书写；`syndicate: cnblogs` 表示这篇文章要自动同步到博客园，删掉这行则只在主站发布。
```

注意：`slug` 决定 URL（`/posts/hello-world/`），也是同步去重的键，发布后不要再改。

- [ ] **Step 2: 本地预览**

```bash
hugo server -D
```

期望：浏览器打开 `http://localhost:1313`，能看到首页信息与该文章；`Ctrl+C` 退出。

- [ ] **Step 3: 提交**

```bash
git add content/
git commit -m "post: hello world"
```

## Task 3: 推送 GitHub 并部署到 Cloudflare Pages

- [ ] **Step 1: 创建 GitHub 公开仓库并推送**

在 github.com 网页新建**公开**仓库 `selfblog`（不要勾选初始化 README），然后：

```bash
git remote add origin https://github.com/你的用户名/selfblog.git
git push -u origin main
```

期望：push 成功，网页上能看到代码。

- [ ] **Step 2: 连接 Cloudflare Pages**

浏览器操作（dash.cloudflare.com）：

1. Workers & Pages → Create → Pages 标签 → Connect to Git → 授权并选择 `selfblog` 仓库；
2. Build configuration：
   - Framework preset: `Hugo`（或 None）
   - Build command: `hugo --minify --gc`
   - Build output directory: `public`
   - Environment variables（Production 和 Preview 都加）: `HUGO_VERSION` = Step 1 记下的本地版本号（如 `0.146.0`，只要数字）
3. Save and Deploy。

期望：几分钟后部署成功，访问 `https://<项目名>.pages.dev` 能看到博客。

- [ ] **Step 3: 校正 baseURL**

若实际分配的域名与配置不同（如项目名被占用），修改 `hugo.toml` 的 `baseURL` 后：

```bash
git add hugo.toml
git commit -m "config: align baseURL with pages.dev domain"
git push
```

期望：push 触发自动重新部署。

- [ ] **Step 4: （可选，有域名时）绑定自定义域名**

Cloudflare Pages → Custom domains → 添加域名（域名 DNS 需托管在 Cloudflare，自动配 CNAME）；随后把 `baseURL` 改为正式域名并 push。

- [ ] **Step 5: 提交搜索引擎收录**

到 Google Search Console 与 Bing Webmaster 添加资源，提交 `https://<你的域名>/sitemap.xml`（Hugo 自带 sitemap）。

## Task 4: giscus 评论

**Files:**
- Create: `layouts/partials/comments.html`
- Modify: `hugo.toml`

- [ ] **Step 1: 开启 Discussions 并安装 giscus App**

GitHub 仓库 → Settings → Features 勾选 **Discussions**；到 `github.com/apps/giscus` 将 App 安装到该仓库。

- [ ] **Step 2: 生成配置片段**

打开 `giscus.app/zh-CN`，填入仓库名 `你的用户名/selfblog`，Mapping 选 `pathname`，分类选 `Announcements`（或 General），复制页面生成的 `<script>` 代码块。

- [ ] **Step 3: 写入 comments partial**

创建 `layouts/partials/comments.html`，粘贴上一步的脚本，形如：

```html
<script src="https://giscus.app/client.js"
        data-repo="你的用户名/selfblog"
        data-repo-id="giscus.app 生成的 ID"
        data-category="Announcements"
        data-category-id="giscus.app 生成的 ID"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="top"
        data-theme="preferred_color_scheme"
        data-lang="zh-CN"
        crossorigin="anonymous"
        async>
</script>
```

- [ ] **Step 4: 开启评论参数**

`hugo.toml` 的 `[params]` 段中加一行：

```toml
comments = true
```

- [ ] **Step 5: 部署验证**

```bash
git add layouts/ hugo.toml
git commit -m "feat: enable giscus comments"
git push
```

期望：部署后打开线上文章页，底部出现评论区（本地 `hugo server` 下 giscus 可能不显示，以线上为准）。

## Task 5: 同步脚本——先写测试（TDD）

**Files:**
- Create: `tests/test_sync_cnblogs.py`
- Create: `scripts/sync_cnblogs.py`（本任务先建空壳）

- [ ] **Step 1: 建空壳实现**

创建 `scripts/sync_cnblogs.py`，先只放签名，保证测试可导入：

```python
#!/usr/bin/env python3
"""将带 syndicate: cnblogs 标记的文章同步到博客园（MetaWeblog API）。"""


def parse_front_matter(text):
    raise NotImplementedError


def clean_markdown(body):
    raise NotImplementedError


def append_source_link(body, url):
    raise NotImplementedError


def main():
    raise NotImplementedError
```

- [ ] **Step 2: 写测试文件**

创建 `tests/test_sync_cnblogs.py`：

```python
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from sync_cnblogs import append_source_link, clean_markdown, main, parse_front_matter

SAMPLE = '''---
title: "测试文章"
date: 2026-08-14
slug: hello-world
syndicate: cnblogs
tags: ["随笔"]
---

正文第一段。

{{< figure src="a.png" title="图" >}}

正文第二段。
'''


class TestParseFrontMatter(unittest.TestCase):
    def test_extracts_fields_and_strips_block(self):
        meta, body = parse_front_matter(SAMPLE)
        self.assertEqual(meta["title"], "测试文章")
        self.assertEqual(meta["syndicate"], "cnblogs")
        self.assertNotIn("title:", body)
        self.assertIn("正文第一段", body)

    def test_text_without_front_matter(self):
        meta, body = parse_front_matter("只有正文")
        self.assertEqual(meta, {})
        self.assertIn("只有正文", body)


class TestCleanMarkdown(unittest.TestCase):
    def test_strips_hugo_shortcodes(self):
        out = clean_markdown("前文\n\n{{< figure src=\"a.png\" >}}\n\n后文")
        self.assertNotIn("figure", out)
        self.assertIn("前文", out)
        self.assertIn("后文", out)


class TestAppendSourceLink(unittest.TestCase):
    def test_appends_origin_url(self):
        out = append_source_link("正文", "https://ex.com/posts/hello-world/")
        self.assertIn("https://ex.com/posts/hello-world/", out)


class TestMain(unittest.TestCase):
    ENV = {
        "CNBLOGS_METAWEBLOG_URL": "https://rpc.cnblogs.com/metaweblog/fakeblog",
        "CNBLOGS_USERNAME": "tester",
        "CNBLOGS_TOKEN": "fake-token",
        "SITE_BASE_URL": "https://ex.com",
    }

    def test_first_run_publishes_then_second_run_edits(self):
        server = mock.MagicMock()
        server.metaWeblog.newPost.return_value = "10086"
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict(os.environ, self.ENV), \
                mock.patch("sync_cnblogs.ServerProxy", return_value=server):
            os.chdir(d)
            post = os.path.join(d, "hello-world.md")
            with open(post, "w", encoding="utf-8") as f:
                f.write(SAMPLE)

            # 第一次运行：应调用 newPost 发布，并落盘 ID 映射
            with mock.patch("sys.argv", ["sync_cnblogs.py", post]):
                main()
            server.metaWeblog.newPost.assert_called_once()
            sent = server.metaWeblog.newPost.call_args[0][3]
            self.assertIn("https://ex.com/posts/hello-world/", sent["description"])
            self.assertTrue(os.path.exists(".cnblogs-map.json"))

            # 第二次运行同一篇：应改为 editPost，不再重发
            server.reset_mock()
            with mock.patch("sys.argv", ["sync_cnblogs.py", post]):
                main()
            server.metaWeblog.newPost.assert_not_called()
            server.metaWeblog.editPost.assert_called_once()
            self.assertEqual(server.metaWeblog.editPost.call_args[0][0], "10086")

    def test_skips_posts_without_flag(self):
        server = mock.MagicMock()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict(os.environ, self.ENV), \
                mock.patch("sync_cnblogs.ServerProxy", return_value=server):
            os.chdir(d)
            post = os.path.join(d, "local-only.md")
            with open(post, "w", encoding="utf-8") as f:
                f.write("---\ntitle: 仅主站\nslug: local-only\n---\n正文")
            with mock.patch("sys.argv", ["sync_cnblogs.py", post]):
                main()
        server.metaWeblog.newPost.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行测试，确认失败**

```bash
python -m unittest discover tests -v
```

期望：多条 FAIL/ERROR（`NotImplementedError` 或导入失败）。

## Task 6: 同步脚本——实现

**Files:**
- Modify: `scripts/sync_cnblogs.py`（整体替换为完整实现）

- [ ] **Step 1: 写完整实现**

```python
#!/usr/bin/env python3
"""将带 syndicate: cnblogs 标记的文章同步到博客园（MetaWeblog API）。

用法: python scripts/sync_cnblogs.py <file.md> [file2.md ...]
环境变量:
  CNBLOGS_METAWEBLOG_URL  https://rpc.cnblogs.com/metaweblog/<博客名>
  CNBLOGS_USERNAME        博客园用户名
  CNBLOGS_TOKEN           博客园后台生成的 MetaWeblog 访问令牌（不是登录密码）
  SITE_BASE_URL           主站域名，如 https://selfblog.pages.dev
"""
import json
import os
import re
import sys
from xmlrpc.client import ServerProxy

MAP_FILE = ".cnblogs-map.json"
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
KV_RE = re.compile(r"^([\w-]+):\s*(.*)$")
SHORTCODE_RE = re.compile(r"\{\{[<>%].*?[<>%]\}\}", re.DOTALL)


def parse_front_matter(text):
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        kv = KV_RE.match(line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
    return meta, text[m.end():]


def clean_markdown(body):
    return SHORTCODE_RE.sub("", body).strip()


def append_source_link(body, url):
    return f"{body}\n\n---\n\n> 本文首发于：{url}"


def load_map():
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_map(mapping):
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)


def publish(server, username, token, title, body, old_id=None):
    post = {"title": title, "description": body}
    if old_id:
        return server.metaWeblog.editPost(old_id, username, token, post, True)
    return server.metaWeblog.newPost("1", username, token, post, True)


def main():
    endpoint = os.environ["CNBLOGS_METAWEBLOG_URL"]
    username = os.environ["CNBLOGS_USERNAME"]
    token = os.environ["CNBLOGS_TOKEN"]
    base_url = os.environ["SITE_BASE_URL"].rstrip("/")

    mapping = load_map()
    server = ServerProxy(endpoint)

    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        meta, body = parse_front_matter(text)
        if meta.get("syndicate") != "cnblogs":
            continue
        slug = meta.get("slug") or os.path.splitext(os.path.basename(path))[0]
        body = append_source_link(clean_markdown(body), f"{base_url}/posts/{slug}/")
        post_id = publish(server, username, token, meta.get("title", "无标题"),
                          body, mapping.get(slug))
        mapping[slug] = str(post_id)
        print(f"已同步 {path} -> 博客园文章ID {post_id}")

    save_map(mapping)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行测试，确认全部通过**

```bash
python -m unittest discover tests -v
```

期望：`OK`（6 个测试用例全部 PASS）。

- [ ] **Step 3: 提交**

```bash
git add scripts/ tests/
git commit -m "feat: cnblogs metaweblog sync script with edit dedup"
```

## Task 7: GitHub Actions 自动同步工作流

**Files:**
- Create: `.github/workflows/sync-cnblogs.yml`

- [ ] **Step 1: 配置仓库 Secrets**

GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret，添加 4 个：

| Secret 名 | 值 |
|-----------|-----|
| `CNBLOGS_METAWEBLOG_URL` | `https://rpc.cnblogs.com/metaweblog/<你的博客名>` |
| `CNBLOGS_USERNAME` | 博客园用户名 |
| `CNBLOGS_TOKEN` | 博客园后台生成的 MetaWeblog 访问令牌 |
| `SITE_BASE_URL` | 主站域名（当前为 `https://<项目名>.pages.dev`） |

- [ ] **Step 2: 创建 workflow 文件**

`.github/workflows/sync-cnblogs.yml`：

```yaml
name: sync-cnblogs

on:
  push:
    branches: [main]
    paths: ["content/posts/**"]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: 找出本次变更的文章
        id: files
        run: |
          {
            echo 'files<<EOF'
            git diff --name-only HEAD~1 HEAD -- 'content/posts/*.md' || true
            echo 'EOF'
          } >> "$GITHUB_OUTPUT"

      - name: 同步到博客园
        if: ${{ steps.files.outputs.files != '' }}
        env:
          CNBLOGS_METAWEBLOG_URL: ${{ secrets.CNBLOGS_METAWEBLOG_URL }}
          CNBLOGS_USERNAME: ${{ secrets.CNBLOGS_USERNAME }}
          CNBLOGS_TOKEN: ${{ secrets.CNBLOGS_TOKEN }}
          SITE_BASE_URL: ${{ secrets.SITE_BASE_URL }}
        run: python scripts/sync_cnblogs.py ${{ steps.files.outputs.files }}

      - name: 回写文章ID映射
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add .cnblogs-map.json || true
          git diff --cached --quiet || (git commit -m "chore: update cnblogs post map [skip ci]" && git push)
```

- [ ] **Step 3: 端到端验证**

```bash
git add .github/
git commit -m "ci: auto sync posts to cnblogs via metaweblog"
git push
```

期望：Actions 页出现 `sync-cnblogs` 运行记录且绿灯；打开博客园后台，`hello-world` 一文已发布且文末带"本文首发于"链接。

- [ ] **Step 4: 验证编辑去重**

修改 `content/posts/hello-world.md` 正文（保留 slug），push。

期望：博客园上**同一篇文章被更新**，而不是出现第二篇；Actions 日志显示走通。

---

## 四、阶段三/四：路线图（按需启动，不在本计划内实施）

### 阶段三：轻量云服务器（公网入口）

腾讯云/阿里云轻量 2核2G 起步，仅跑非网站服务，免备案。参考编排：

```yaml
# cloud/docker-compose.yml（届时另立仓库/计划）
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    restart: unless-stopped
    ports: ["3001:3001"]
    volumes: ["kuma:/data"]
  frps:
    image: snowdreamtech/frps:latest
    restart: unless-stopped
    network_mode: host
    volumes: ["./frps.toml:/etc/frp/frps.toml"]
volumes:
  kuma: {}
```

`frps.toml` 核心：`bindPort = 7000` + 强 token；云防火墙放行 7000 与 MC 转发端口。届时把 Uptime Kuma 指向主站与各服务做可用性监控。

### 阶段四：家里设备（算力）

旧电脑或 N100 小主机，Docker Compose 跑：MC 服务器（`itzg/minecraft-server`，`EULA=TRUE`、`MEMORY=4G`）、Gitea、FreshRSS；经 frpc 隧道（`serverAddr = 云IP`）或 Tailscale 对外。原则：单机 Compose 为止，不上 k8s。

### 主站后续迁移路径（如终有一天想自托管）

同一仓库追加一个 workflow：`hugo --minify --gc` 构建后 `rsync` 推到自己服务器的 Nginx 目录，域名解析从 Cloudflare Pages 切到服务器 IP，分钟级完成迁移。
