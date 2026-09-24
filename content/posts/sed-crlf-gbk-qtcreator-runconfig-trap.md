---
title: "构建成功却找不到 exe：一次 .pro 重写引发的 CRLF、GBK 吞行与 Qt Creator 运行配置三重故障"
date: 2026-09-09T23:10:00+08:00
slug: sed-crlf-gbk-qtcreator-runconfig-trap
draft: true
tags: ["Qt", "Windows", "Git", "编码", "踩坑"]
---

编译和链接都成功，Qt Creator 点运行却报错：

```text
启动程序失败，路径或者权限错误?
The process failed to start. Either the invoked program
"...\build-...\release\vEEGRefactor.exe" is missing,
or you may have insufficient permissions to invoke the program.
```

`vEEGRefactor.exe` 确实不存在，构建目录里只有 `vEEG.exe`。按因果顺序拆三层：为什么找错名字、名字为什么没解析对、哪条修法有效。

## 为什么找的是 vEEGRefactor.exe

```make
QMAKE_TARGET_PRODUCT = "vEEG"
TARGET = $${QMAKE_TARGET_PRODUCT}
```

qmake 生成的 Makefile 里 `TARGET` 正确，产物就是 `vEEG.exe`，构建侧没问题。

问题在 Creator 侧。`.pro.user` 的 RunConfiguration 里没有「可执行文件」字段——exe 路径是每次会话由 Creator 自己的 pro 求值器读 `.pro` 动态算出的。这个求值器与命令行 qmake 是两套独立解析：

- 求值成功 → `vEEG.exe`；
- `TARGET` 求值为空 → 回退默认规则：`.pro` 基础名 + `.exe` = `vEEGRefactor.exe`。

这次是后者。

**为什么以前没出过事**：旧 `.pro.user` 里存着一个路径写死的运行配置，不经过 TARGET 求值。事故当天它被重写，运行配置改为动态派生，地雷才暴露。也因此「删 `.pro.user` 重建」无效——重建走的还是同一个求值器。

## 为什么 TARGET 那一行失效

`TARGET = $${QMAKE_TARGET_PRODUCT}` 在 Creator 求值器眼里已经消失了。前提是 `.pro` 处于 LF + 无 BOM 状态，来源两种：

- **编辑器误操作**：Creator 编辑器自带编码、换行符选择器，改完顺手保存，diff 里看不出来；
- **命令行直写**：Git Bash 下 `sed -i` 整文件重写，CRLF 剥成 LF：

```bash
sed -i '/ChannelManageComponents\/SchemeMigrator/d' vEEGRefactor.pro
```

吞行机制：中文 Windows 系统代码页是 GBK，Creator 对无 BOM 的 `.pro` 按 GBK 解码。若某行末尾是奇数个 UTF-8 字节——`#生成文件名` 的「名」= `E5 90 8D`，尾字节 `8D` 落单——解码器把紧随的换行符 `0A` 当配对字节吃掉，下一行并入注释、消失。被吞的正是 TARGET 赋值行。

CRLF 安全：行尾 `0D 0A`，被吃的是 `0D`，`0A` 幸存。所以问题不在 EOL 本身，在 GBK 解码吞换行；文件剥成 LF 后才暴露。

qmake.exe 解码路径不同，Makefile 恒正确、Creator 恒错误，只看 Makefile 发现不了问题。

## 对照实验

| 实验 | 结果 | 结论 |
|---|---|---|
| `#生成文件名` 坏 / `#生成文件` 好 / `#名` 坏 | 复现稳定 | 症状跟行尾字节走，锁定编码层 |
| 同文件 LF 坏 / CRLF 好 | 复现稳定 | 锁定换行符被吃 |
| 奇尾行与 TARGET 之间插两行注释 | 恢复 | 被吞的是「牺牲行」，TARGET 幸存——但不可靠，见下 |

## BOM 救不了 .pro

有 BOM，Creator 按 UTF-8 解码，不吞行——对 Creator 侧成立。但 `.pro` 有两个消费方：

| 消费方 | 无 BOM + 奇尾行 | 加 BOM |
|---|---|---|
| Creator 求值器（无 BOM 按 GBK 解） | LF 下吞行 | 按 UTF-8 解，不吞 |
| qmake 5.12 | 正常 | **整个文件拒载** |

实测：

```text
:-1: error: Cannot read D:/.../vEEGRefactor.pro: Unexpected UTF-8 BOM
```

qmake 5.12 对带 BOM 的 `.pro` 直接拒收。BOM 修好 Creator 的同时弄死构建。

BOM 对 `.cpp/.h` 无害有效（MSVC/GCC/Clang 都认），那边没有拒载 BOM 的消费方。

## 偶数字节不可靠，ASCII 行尾可靠

GBK 解码是从行首开始的双字节配对走查，相位由行内全部字节决定，不尊重 UTF-8 字符边界——ASCII 字节在相位错位时会被当作尾字节吃掉。「行尾偶数字节」推不出「走查停在边界」。实测一行以 10 字节（偶数）多字节序列结尾，照样落单：

```text
bytes tail: e5 bf 85 e9 9c 80 ef bc 89 e3 80 82
LONE LEAD at byte 55 (0x82) -> 仍吞换行
```

ASCII 行尾则可证明安全：行尾是 ASCII 字节时，走查必然停在字符边界（它要么被前一首字节配对吃掉，要么独立走完），`0A` 不可能被配对。归纳可得：每行行尾都是 ASCII（或完整成对）时，LF/CRLF 双形态均安全。

最终修复：中文结尾的行行尾补一个 ASCII `.`（如 `#生成文件名.`），全文件 17 行，落单行尾归零。

## git 为什么全程沉默

`core.autocrlf=true` 下 blob 恒为 LF，工作区检出为 CRLF。「变成 LF」与以往 add 无区别，`git status` 对纯 EOL 差异始终 clean。地雷基因（LF + 奇尾注释）一直在库里，靠 smudge 检出的 CRLF 压着；只有编辑器或 shell 直写才产生 LF 工作区形态。字节级验证：

```bash
tr -dc '\r' < vEEGRefactor.pro | wc -c        # 工作区：0，CR 全没了
git show <commit>:vEEGRefactor.pro | tr -dc '\r' | wc -c   # blob：0，恒为 LF
```

注意 MSYS 下 `grep -c $'\r'` 这类管道命令会因自身转换失真——排查中因此得出过「历史 blob 是 CRLF」的错误测量。只有 `tr -dc '\r' | wc -c` 和 `od -c` 可信。

## 弯路

- 删 `.pro.user` 重建：无效，重建必经同一求值器；
- TARGET 改字面量：当时「立刻好了」，实为编辑触发重读的时机巧合——单次 A/B 不是因果证明；
- 怀疑透明加密软件：机器上有惯犯（Esafenet），但 `.pro` 不在其作用范围；
- 坏测量（grep 管道失真）导致按错误结论「归一化」好文件，亲手造出 LF 形态。

## 修复

```bash
git checkout -- vEEGRefactor.pro    # 经 smudge 通道恢复 CRLF
```

终态：无 BOM + 中文结尾行行尾补 `.`。行尾 LF/CRLF 皆可，句点已消掉形态敏感性。Creator 侧若配置已乱：删 `.pro.user`，重开工程执行一次 qmake。

另一坑：磁盘修完文件，IDE 里的旧缓冲一个 Ctrl+S 就能把修复抹掉（还按编辑器当前行尾设置写盘）。外部改文件后先关标签页或走「重新载入」。

## 预防

- 禁止 `sed -i`、`echo >`、`>` 等 shell 直写改受控文本文件；MSYS sed 重写剥 CRLF，git 对此无感；
- 禁止以任何理由「归一化」已有文件行尾，编辑保持现有 EOL 与编码；
- 禁止 `git cat-file >` / `git show >` 恢复文件（绕过 smudge），一律 `git checkout --`；
- `.pro` 中文注释：**禁止 BOM**（qmake 5.12 拒载），**别信凑偶数**，行尾补一个 ASCII 字符；
- 报「找不到 {项目名}.exe」「无法在套件下解析项目」时，先看 `.pro` 的 EOL 和行尾字节。

## 后日谈

写了个体检脚本（`docs/tools/check_bom_crlf.py`）扫 534 个 `.cpp/.h`：UTF-8 解码失败 0；带 BOM 77 / 无 BOM 457（纯作者编辑器习惯差异）；**含奇尾行的文件 129 个**，全靠 CRLF 检出形态压着没炸，任何一个被写成 LF 就重演一次。4 个「LF + 中文注释」现役危险文件已用 `rm` + `git checkout --` 重检出处置。

顺带：`.pro` 里的 `QMAKE_CXXFLAGS += /utf-8` 管的是 cl.exe 编译 cpp/h（源码解码 + 窄字符串字面量编码），与「qmake/Creator 解析 `.pro` 本身」是两条链路，互不替代——这次事故它在场也帮不上。教训与规则已写进仓库 `AGENTS.md`。

## 小结

三层叠加，缺一不可：

1. **EOL 层**：`.pro` 被重写成 LF；
2. **编码层**：无 BOM 的 UTF-8 按 GBK 解码，奇尾中文注释行吞掉 TARGET；
3. **IDE 层**：运行配置动态求值 `TARGET`，失败回退 `.pro` 文件名 + `.exe`。

掩体是旧 `.pro.user` 里路径写死的运行配置，压了地雷一年。两个工具说法矛盾时（git 全程 clean、Makefile 恒对），先确认它们看的不是同一份数据；三个候选修法里两个是推理成立、实测翻车——编码问题上，想当然和实测的距离比多数领域都远。
