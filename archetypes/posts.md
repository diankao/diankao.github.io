---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
date: "{{ .Date }}"
slug: "{{ .File.ContentBaseName }}"
draft: false
tags: []
syndicate: cnblogs
---
<!--
写作提示（发布前删除本块）：
- 正文从 ## 开始，# 留给标题
- 图片放 static/images/<slug>/，用 ![alt](/images/<slug>/x.png) 标准语法，勿用 {{< figure >}} 短代码
- 仅主站发布：删除上方 syndicate 行
- 发布后不改文件名和 slug
完整规范见 AGENTS.md
-->
