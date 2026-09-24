---
title: "Qt 把 slots 定义成了宏：一次 C2059「语法错误: [」排查实录"
date: 2026-09-07T16:40:00+08:00
slug: qt-slots-empty-macro-trap
draft: true
tags: ["Qt", "C++", "预处理", "踩坑"]
---

给 Qt 项目写了一个纯数据结构的头文件——一个卡片视图模型，里面有个结构体长这样：

```cpp
struct Port
{
    PortKind kind = PortKind::Empty;
    Electrode::ElectrodeDetail device;
    NeedleSlot slots[Electrode::Needle::SLOTS_PER_PORT];   // 下标 = 插口号 0..7
    QVector<Electrode::ElectrodeDetail> raw;
};
```

`PortSchemeViewModel.h`，不含任何 QObject，不 connect 任何信号，就是个普通聚合体。编译，MSVC 甩出来两条：

```text
PortSchemeViewModel.h:36: error C2059: 语法错误:"["
PortCardWidget.cpp:157: error C2039: "QFrame": 不是 "PortVm::Port" 的成员
```

第一条指着 `slots[8]` 的方括号——一个数组声明，语法错误？第二条更离谱，说 `QFrame` 不是 `PortVm::Port` 的成员——`QFrame` 是 Qt 的类，跟我的结构体八竿子打不着，而且报错位置在另一个文件里。

先说结论，再说排查过程：

- Qt 在**没有**定义 `QT_NO_KEYWORDS` 时，`qobjectdefs.h` 里有一组"伪关键字"宏：`#define slots`（空）、`#define signals public`、`#define emit`（空）。它们是给 `public slots:` / `signals:` 这套信号槽语法用的。
- 所以 `slots` **效果上等于保留字**：任何地方拿它当标识符，预处理阶段都会被替换成空，`NeedleSlot slots[8]` 变成 `NeedleSlot [8]`，C2059 就来了。
- 但它比真保留字阴险三层：报错位置偏移、与包含顺序相关、还会派生指鹿为马的连锁误报。下面逐条拆。
- 修复两条路：改名（成本最小，本文选的）；或全工程 `QT_NO_KEYWORDS` + `Q_SLOTS`/`Q_SIGNALS`/`Q_EMIT`（适合新项目开工就开）。

## 机制：moc 和编译器看的不是同一份代码

要理解这组宏为什么存在，得先知道 Qt 的信号槽是两个工具配合的结果。

**moc（Meta-Object Compiler，元对象编译器）**在真正的 C++ 编译之前跑，扫描所有含 `Q_OBJECT` 的头文件，认出 `signals:`、`slots:`、`Q_INVOKABLE` 这些标记，生成 `moc_xxx.cpp` 胶水代码（信号的本质、metaObject 表、qt_metacall 等）。moc 是个**文本扫描器**，它认的这些"关键字"是自己发明的，C++ 语言里根本不存在。

问题来了：moc 认得，编译器不认。`private slots: void foo();` 这行如果原样交给 C++ 编译器，`slots` 是个不存在的 token，直接语法错误。Qt 的解法是——既然编译器不需要这几个词，就**让预处理把它们删掉**。`qobjectdefs.h` 里（Qt 5）：

```cpp
#ifndef QT_NO_KEYWORDS
#  define slots
#  define signals public
#  define emit
#endif
```

展开效果：

```cpp
private slots:  void foo();   // 你写的
private:        void foo();   // 编译器看到的
signals:        void bar();   // 你写的
public:         void bar();   // 编译器看到的
emit clicked();              // 你写的
clicked();                   // 编译器看到的
```

三个宏各司其职：`slots` 展开为**空**，保留前面 `private`/`protected`/`public` 的访问性（所以三种 access 的槽都合法）；`signals` 展开为 **`public`**——注意它不是空宏，因为 Qt 规定信号必须是 public 的，得顺手把访问性改掉；`emit` 展开为空，纯语义糖，告诉你"这是发信号"。

这套设计让信号槽语法读起来像原生 C++ 扩展，代价是：**`signals`、`slots`、`emit` 这三个词从宏生效那一刻起，就不能再当标识符用了**。宏不做任何检查，遇到就换，换完就走。

## 为什么比真保留字阴险三层

### 第一层：报错位置与病因隔着一层皮

拿真保留字当变量名，比如 `int class = 1;`，编译器当场报"不能用关键字"，错误就在那一行，看一眼就懂。

空宏不一样。它不报"slots 是关键字"，它**把你的标识符无声删除**，然后把语法错误的现场留给下游 token。`NeedleSlot slots[8]` 变成 `NeedleSlot [8]`，编译器看到的孤立方括号才是"案发现场"，报出来的 C2059 指着 `[`。你盯着自己写的源码看一百遍也看不出问题——因为出错的不是你写的那份代码，是预处理之后的那份。

### 第二层：宏生效与否取决于包含顺序

预处理是**按编译单元（TU）、按文本顺序**展开的。`#define slots` 只存在于包含 `qobjectdefs.h` 之后的文本里。于是同一个头文件会有截然不同的命运：

```cpp
// a.cpp —— 编不过
#include <QFrame>        // 间接包含 qobjectdefs.h，#define slots 已生效
#include "portvm.h"      // NeedleSlot [8]; → C2059

// b.cpp —— 能过
#include "portvm.h"      // 此刻 slots 还是普通标识符，声明完全合法
#include <QFrame>        // 晚了，portvm.h 已经解析完了
```

我踩的坑正是这个形状：`PortSchemeViewModel.h` 本身干干净净，但包含它的 `PortCardWidget.h` 头几行就 include 了 `QFrame` 系头文件。**报错文件是受害者，案发现场在别人的包含顺序里**。如果碰巧有个 cpp 先包含它再包含 Qt 头，那个 TU 还能编过——"同一个头文件有的编译单元炸、有的不炸"，这种半随机表现极其误导排查。

给"会被别人包含的纯数据头文件"起成员名时，尤其要想到这一层：你控制不了别人以什么顺序包含你。

### 第三层：连锁误报指鹿为马

结构体在坏成员处解析崩溃后，编译器并不会停下来，而是做**错误恢复**：把后续 token 流按另一种语法结构硬拼。于是产生一批与真实病因无关、甚至方向完全错误的二级报错——我的例子里就是那条 `C2039: "QFrame" 不是 "PortVm::Port" 的成员`：编译器错误恢复后尝试在坏掉的 `Port` 作用域里解析 `QFrame`，然后一本正经地告诉你这个 Qt 全局类不是我的结构体的成员。如果先追着 C2039 查 `QFrame` 的包含关系，就完全跑偏了。

**多条报错一起出现时，优先看最靠前、最"不讲道理"的那条语法错误**——后面的经常只是崩坏的余波。

## 最小复现

三分钟就能在任意 Qt 工程里复现（Qt 5/MSVC，MinGW 同理）：

```cpp
// portvm.h —— 纯数据结构
#pragma once
struct Port {
    int slots[8];
};
```

```cpp
// main.cpp
#include <QWidget>
#include "portvm.h"

int main() { Port p; (void)p; }
```

编译报 `C2059: 语法错误:"["`。把 `#include <QWidget>` 挪到 `#include "portvm.h"` 下面，或者把成员改名成 `slots2`，立刻通过。两个变量各动一下，因果链就锁死了。

## 排查手法：确认是宏在捣鬼

遇到"标识符平平无奇却报语法错误"的场面，怀疑宏的验证手段按成本排序：

1. **改名试探（最快）**。把可疑标识符随便改成别的名字，编过 = 实锤宏冲突。这一步三十秒。
2. **看预处理输出**。让编译器把它真正看到的东西吐给你：
   - MSVC：`cl /P main.cpp` 生成 `main.i`，搜 `NeedleSlot` 看那一行变成了什么；
   - GCC/MinGW：`g++ -E main.cpp | grep -n "NeedleSlot"`。
   预处理文件里 `NeedleSlot [8];` 白纸黑字，没有比这更硬的证据。
3. **全局搜 `#define`**。Windows/Qt 生态里干这种事的宏不止一个（见下文清单）。

## 修复方案对比

### 方案 A：改名（推荐，本文所用）

成本最小、零风险。`slots` 改成什么见仁见智，我的命名还走了两步：先改成 `needles`，后来觉得有歧义——数组是"8 个插口位"、下标是插口号，叫 needles 像个可以任意长度的"针列表"——最终定为 `needleSlots`，并在头文件留注释说明为什么不能叫 `slots`，防止后人改回去：

```cpp
// 不叫 slots：qobjectdefs.h 把 `slots` 定义成空宏（signals/slots 机制，
// 效果上等于保留字），本头文件会被任何含 QObject 头的 TU 包含，
// 拿 slots 当成员名必然 C2059
NeedleSlot needleSlots[Electrode::Needle::SLOTS_PER_PORT];
```

### 方案 B：QT_NO_KEYWORDS（新项目开工就开）

qmake 工程在 `.pro` 里加：

```pro
DEFINES += QT_NO_KEYWORDS
```

这三个宏从此不存在，标识符彻底自由，且永远不会再有人踩。代价：全工程所有 `slots:`、`signals:`、`emit` 必须改写成等价的大写版本 `Q_SLOTS:`、`Q_SIGNALS:`、`Q_EMIT`（这三组**任何时候都可用**，与该宏开关无关）。存量代码满篇关键字写法的话，替换面太大还要动第三方代码，不值得为一个成员名翻修全仓库。

顺带一提，**不能局部解决**。比如想在某个 cpp 里 `#define QT_NO_KEYWORDS` 再包含 Qt 头——没用：出问题的头文件会被很多 TU 包含，只要有一个 TU 的包含顺序不巧，照样炸。宏是全局文本机制，没有局部免疫力。

### 方案 C：调整包含顺序

让数据头先于 Qt 头被包含，理论上能让该 TU 编过。但上一节说过，这依赖"所有人永远以正确顺序包含你"，本质是把炸弹留给下一个包含者。只算应急手段，不算修复。

## 避坑清单

**Qt 伪保留字（关键词语法开启时）：`signals`、`slots`、`emit`。** 命名时绕开这三个词。想彻底免疫，可以养成直接用大写版本的习惯——`Q_SIGNALS:`、`Q_SLOTS:`、`Q_EMIT` 语义完全相同，永远可用，还多一层"这是 Qt 机制不是普通函数调用"的提示。

**这个生态里同类的宏还不少**，症状全是"报错不讲道理"：

| 宏 | 来源 | 症状 / 解法 |
|---|---|---|
| `slots` / `signals` / `emit` | Qt `qobjectdefs.h` | 本文主角；`QT_NO_KEYWORDS` 或绕开命名 |
| `min` / `max` | Windows `windows.h` | `std::min(a, b)` 编不过（C2059 或巨长模板报错）；`NOMINMAX` 预定义 |
| `interface` | Windows SDK | 当类名/变量名用会莫名替换；`#define interface struct` 的老兼容宏 |
| `near` / `far` | 老 Windows 头 | DOS 时代段地址残留，偶尔在老代码里咬人 |

共同规律：**用宏模拟语言特性的库，都附赠了一批事实保留字**，只是没人给它们发保留字证书。

## 写在最后

这次排查最值得留的不是修好了一个编译错误，而是它揭穿的一个错觉：**你写的源码和编译器编译的代码，中间隔着一个按文本规则行事、不做任何语义检查的预处理器**。编译器报的行号、错误位置，只对展开后的那份文本负责；`slots` 这种被无声抹掉的 token，在报错信息里连名字都不会出现。

所以遇到"报错完全不讲道理"时，第一个该问的问题不是"我这行哪里错了"，而是"**编译器看到的这一行，跟我写的是同一行吗**"。改个名试一下、或者直接看预处理输出——把中间那层迷雾撕开，很多"玄学"编译错误当场就变成了一行白纸黑字。

至于 Qt 这套设计本身：用三个宏换来一套贴近原生语法的信号槽，在 moc 诞生的年代是聪明的权衡，代价则平摊到了此后三十年每个把成员命名为 `slots` 的人头上——包括我。
