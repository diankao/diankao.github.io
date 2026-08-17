# content 撰写规范

本仓库博客文章的唯一写作依据。目标：任何人（包括未来的自己和 AI）照此文档就能产出一篇结构合规、URL 稳定、可自动同步博客园的文章。

## 1. 目录结构

```
content/
├── posts/              # 所有文章。扁平结构，不建子目录
│   └── my-post.md      # 一文一文件，文件名即身份
└── about.md            # （可选）关于页，front matter 用 layout: page
static/
└── images/<slug>/      # 文章配图按 slug 分目录存放
```

## 2. 新建文章

```bash
hugo new content posts/<kebab-case-slug>.md
```

原型模板（`archetypes/posts.md`）会自动生成合规的 front matter，只需改写 `title`、填 `tags`、写正文。

## 3. 文件名与 slug（最重要的规则）

- 文件名：**全小写英文 + 连字符**（kebab-case），如 `docker-network-basics.md`。禁止中文文件名。
- `slug` 必须与文件名（去扩展名）一致；原型已自动如此，不要手改。
- **发布后永不修改文件名和 slug**。它同时是：
  1. 主站 URL：`/posts/<slug>/`；
  2. 博客园同步去重的键（`.cnblogs-map.json` 按 slug 记录远端文章 ID）。
- 改名 = 新文章。想重写旧话题就新开一篇，旧文可加指向新文的链接。

## 4. Front matter 字段表

| 字段 | 必填 | 说明 |
|------|------|------|
| `title` | ✅ | 中文标题，站内 h1 与同步文章标题 |
| `date` | ✅ | 原型自动生成，不改 |
| `slug` | ✅ | 见第 3 节，原型自动生成 |
| `draft` | ✅ | 默认 `false`；写作中临时改 `true` 可在本地 `-D` 预览且不构建上线 |
| `tags` | ✅ | 1~3 个，复用已有标签优先，新增须打算长期使用 |
| `syndicate` | ➖ | `cnblogs` = 自动同步博客园；**省略 = 仅主站**（私人向、未定稿、纯备忘的文章省略） |
| `description` | ➖ | SEO 摘要；不填则列表页自动截取正文首段 |
| 其他 | ❌ | 不使用 `url`、`weight`、`categories`、`lastmod` 等字段 |

注意：`draft: true` 与 `syndicate: cnblogs` 不得同时出现——push 即同步，草稿绝不能带同步标记。

## 5. 正文书写规范

- **标题层级从 `##` 开始**：`#` 已被文章 title 占用，正文最高层级是 `##`。
- **图片**：存放 `static/images/<slug>/`，正文用标准 Markdown 语法 `![alt](/images/<slug>/x.png)`。
  - 必须用标准语法而非 Hugo 短代码（`{{< figure >}}` 等）——同步脚本会剔除短代码，博客园端将看不到图。
- **代码块**必须标注语言（``` 后跟 `python`/`bash`/`go` 等）。
- 外链用标准 `[文字](url)` 语法，同步后依然有效。
- 中文排版：中英文、中文与数字之间加空格（如「使用 Docker 部署」）；全角标点。
- 需要同步的文章不使用 Hugo 专属特性（短代码、`ref`/`relref`、页面内嵌模板）。

## 6. 发布与修订流程

```bash
hugo new content posts/<slug>.md   # 1. 建稿
# 2. 写正文，hugo server -D 本地预览
git add . && git commit && git push # 3. push 即全部完成：
                                    #    主站约 1 分钟后更新；
                                    #    带 syndicate 标记的文章同时自动同步博客园
```

- **修订**：直接改文件 push。博客园侧按 slug 映射走编辑更新，不会重复发文。
- **下架**：把 `draft` 改回 `true` 并 push（主站即隐藏）。⚠️ 博客园侧**不会**自动撤稿，需手动到博客园后台删除该文，并删除 `.cnblogs-map.json` 中对应条目。
- 配图删除时同步清理 `static/images/<slug>/` 目录，不留孤儿文件。

## 7. 同步行为明细（供写作时心里有数）

| 主站动作 | 博客园动作 |
|----------|-----------|
| 新文章带 `syndicate: cnblogs` | 自动发布全文，文末追加「本文首发于 主站链接」 |
| 修改已同步文章后 push | 自动编辑更新对应对文章 |
| 新/改文章无 `syndicate` | 不动 |
| 改 `draft: true` 下架 | 不动（需手动处理，见第 6 节） |

## 8. 可选页面配方

- **归档页**：`hugo new content archives.md`，front matter 写 `title: 归档` + `layout: archives`（PaperMod 自动渲染全站时间线）。
- **关于页**：`hugo new content about.md`，正常写 front matter 和正文，首页社交链接处可互链。
