---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
date: "{{ .Date }}"
slug: "{{ .File.ContentBaseName }}"
draft: true
tags: []
---
<!--
写作提示（发布前删除本块）：
- AI 初稿一律 draft: true，草稿不会构建上线；发布是人工动作：
  审核通过后改 draft: false、加 reviewed: true、date 改为实际时间
- 需同步博客园时再加 syndicate: cnblogs（与 draft: true 互斥）
- 正文从 ## 开始，# 留给标题
- 图片放 static/images/<slug>/，用 ![alt](/images/<slug>/x.png) 标准语法，勿用 {{< figure >}} 短代码
- 发布后不改文件名和 slug
完整规范见 AGENTS.md
-->
