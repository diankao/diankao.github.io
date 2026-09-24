---
title: "Qt 清空布局的双重 delete：QLayout 本身就是 QLayoutItem，一次开窗闪退排查实录"
date: 2026-09-07T17:30:00+08:00
slug: qt-qlayout-takeat-double-delete
draft: true
tags: ["Qt", "C++", "内存管理", "踩坑"]
---

给通道管理窗口写了个卡片控件：一张卡一个 `QFrame`，头行固定，body 区域按数据形态（空卡 / 薄膜 / 工装 / 针八插口 / 兜底）整块重建。重建的前提是先清空——于是我写了一个教科书式的 `clearLayout`，然后编译通过，一切正常，**一打开窗口就闪退**，崩溃栈直指这个函数：

```cpp
void PortCardWidget::clearLayout(QLayout *lay)
{
    while (QLayoutItem *it = lay->takeAt(0)) {
        if (QLayout *sub = it->layout()) {
            clearLayout(sub);
            delete sub;
        }
        if (QWidget *w = it->widget()) w->deleteLater();
        delete it;
    }
}
```

看起来人畜无害：取项、有子布局就递归清理、有控件就 deleteLater、最后删掉布局项本身。如果你也觉得这段代码没问题，欢迎先往下读，坑就藏在第四行那个 `it->layout()` 里。

先说结论，再说拆解：

- **`QLayout` 继承自 `QLayoutItem`**。子布局不是"被包在布局项里"，它自己**就是**一个布局项。
- 所以 `lay->takeAt(i)` 把子布局取出来时，返回的 `QLayoutItem*` 和那个子布局**是同一个对象**——`it->layout()` 的实现是 `return this;`。
- 于是 `sub == it`。先 `delete sub` 再 `delete it`，等于对同一块内存 free 两次。而且中间那句 `it->widget()` 是对已释放对象调虚函数，在 `delete sub` 之后的那一行就已经是 use-after-free 了，双重 delete 只是补刀。
- 触发时机是"同一张卡第二次 `setPort`"：构造函数先用空数据建了一遍卡身，外部初始化完数据又刷一遍，第二轮 `clearLayout` 清理第一轮留下的子布局——命中，开窗即崩。

## 背景：为什么需要 clearLayout

Qt 没有提供"一键清空布局"的官方 API。`QLayout` 能 `addWidget` / `addLayout` 地往里加，却没有 `clear()` / `removeAll()`。动态 UI 的常见形态——"内容区按数据整块重画"——只能自己写轮子：

```cpp
void PortCardWidget::setPort(const PortVm::Port &port)
{
    port_ = port;
    rebuildBody();       // 清空 bodyLayout，再按 kind 重建
}
```

重建的代码大致长这样（空卡分支）：

```cpp
QPushButton *add = new QPushButton("＋  添加电极", bodyWidget);
QVBoxLayout *c = new QVBoxLayout;          // 注意：无 parent 的子布局
c->addStretch();
c->addWidget(add, 0, Qt::AlignCenter);
c->addStretch();
bodyLayout->addLayout(c);                  // 从此归 bodyLayout 管
```

控件有 `bodyWidget` 当 parent，子布局没有 parent、直接 `addLayout` 挂进来——这都符合 Qt 规矩。问题只出在清空那一步。

## 机制：QLayoutItem 的三种身份，其中一种"自己就是自己"

`QLayoutItem` 是 Qt 布局系统里"布局项"的抽象基类。往布局里加的任何东西，最终都以 `QLayoutItem` 的面目被管理，具体有三种实现：

```text
QLayoutItem（抽象）
├── QWidgetItem      —— 包着一个 QWidget（addWidget 进来的）
├── QSpacerItem     —— 弹簧（addStretch / addSpacing 进来的）
└── QLayout         —— 子布局（addLayout 进来的）★ 注意：是"继承"，不是"被包裹"
```

前两种是"包装器"：`QWidgetItem` 对象和它包的 `QWidget` 是两个对象。第三种是**自指**：`QLayout` 直接继承 `QLayoutItem`，一个子布局对象身兼两职。Qt 5 源码里写得明明白白（`qlayout.h`）：

```cpp
class Q_WIDGETS_EXPORT QLayout : public QObject, public QLayoutItem
{
    ...
    QLayout *layout() override { return this; }   // ← 自指
    QWidget *widget() override { return nullptr; }
    ...
};
```

基类 `QLayoutItem` 提供三个多态"探测"函数，默认全返回空：

```cpp
virtual QWidget *widget()       { return nullptr; }
virtual QLayout *layout()       { return nullptr; }
virtual QSpacerItem *spacerItem() { return nullptr; }
```

`QWidgetItem` 覆写 `widget()` 返回被包的控件；`QLayout` 覆写 `layout()` 返回 **`this`**。这套设计的本意是让你用"问一圈"的方式分辨取出来的项是什么类型——但它有个致命的语义陷阱：**对子布局项，`it->layout() == it`**。

## 逐行拆解崩溃现场

回到事故代码，把 `sub == it` 代进去走一遍：

```cpp
while (QLayoutItem *it = lay->takeAt(0)) {   // it 就是子布局对象本身
    if (QLayout *sub = it->layout()) {       // layout() 返回 this → sub == it
        clearLayout(sub);                    // 递归清空子布局的孩子们（这步没错）
        delete sub;                          // ★ 子布局对象在这死了
    }
    if (QWidget *w = it->widget()) ...       // ★ it 已悬空：虚调用读已释放内存
    delete it;                               // ★ 对同一块内存第二次 delete
}
```

三连击：`delete sub` 释放了对象；紧接着 `it->widget()` 是通过悬垂指针调虚函数——光这一步就是未定义行为；最后 `delete it` 再 free 一次同一地址。MSVC 的 Debug 堆一般会在这条链上当场断言（`_BLOCK_TYPE_IS_VALID(pHead->nBlockUse)` 之类）或者直接访问违例闪退，崩溃点落在 `clearLayout` 内部——与用户看到的现场一致。Release 下则看运气：内存还没被复用时可能"静默成功"，被复用时崩在八竿子打不着的地方——这类"时崩时不崩"正是双重释放的标志性表现。

## 为什么一开窗就崩：两次 setPort 的时序

这个坑不需要用户操作，窗口构造阶段自己就踩上了：

```text
PortCardWidget 构造
 ├─ buildUi()                    // 建骨架：头行 + bodyWidget + bodyLayout
 └─ setPort(空 Port)             // 第一次 rebuildBody
     └─ clearLayout(空布局)      // 循环不执行，无事发生
     └─ 建空卡分支               // bodyLayout 里挂进一个子布局 c ★

外层 ChannelSchemeDetailWidget 构造收尾
 └─ rebuildPorts() → refreshCards()
     └─ setPort(真实数据)        // 第二次 rebuildBody
         └─ clearLayout(bodyLayout)
             └─ takeAt(0) 取出 c → item == c → 双重 delete → 崩
```

每张卡都走这条时序，一张都跑不掉。所以症状极其稳定：**一打开通道管理窗口就闪退**，不用点任何东西。

## 修复：子布局分支删一次就走

```cpp
void PortCardWidget::clearLayout(QLayout *lay)
{
    // 注意：QLayout 继承自 QLayoutItem——子布局被 takeAt 取出时返回的
    // item 就是那个 QLayout 对象本身（it->layout() 返回 this），
    // 只能删一次；sub == it 再删必双重 free
    while (QLayoutItem *it = lay->takeAt(0)) {
        if (QLayout *sub = it->layout()) {
            clearLayout(sub);
            delete sub;              // sub == it，删这一次就够
            continue;
        }
        if (QWidget *w = it->widget()) w->deleteLater();
        delete it;                   // 普通控件项 / 弹簧项
    }
}
```

要点就一个：**子布局分支 `delete sub` 之后必须 `continue`**，不能再落到下面的 `delete it`。也可以写成 `delete it` 并把递归目标写成 `it->layout()`，反正删的是同一个指针、只能删一次。

顺手把易错点说全：

- **普通控件项**（`QWidgetItem`）：item 和 widget 是两个对象。删 item 不删控件，所以控件要单独 `deleteLater()`（或直接 `delete`）。
- **弹簧项**（`QSpacerItem`）：没有控件、没有子布局，`delete it` 即可。
- `takeAt` 的所有权契约：取出的 item 归调用者所有，**必须由你删**。漏删是泄漏，多删是崩溃，Qt 不会替你兜底。

## 最小复现

二十行，任意 Qt5/Qt6 工程（Widgets）都能复现：

```cpp
#include <QtWidgets>

// 错误版：子布局分支双重 delete
static void badClear(QLayout *lay)
{
    while (QLayoutItem *it = lay->takeAt(0)) {
        if (QLayout *sub = it->layout()) {
            badClear(sub);
            delete sub;                 // sub == it，已释放
        }
        if (it->widget()) {}            // 悬垂虚调用
        delete it;                      // 第二次 delete → 崩
    }
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    QVBoxLayout *body = new QVBoxLayout;
    QVBoxLayout *sub  = new QVBoxLayout;   // 无 parent 子布局
    sub->addWidget(new QPushButton("hi"));
    body->addLayout(sub);                  // 子布局入列
    body->addWidget(new QLabel("x"));

    QWidget w; w.setLayout(body); w.show();
    badClear(body);                        // Debug 下当场断言/闪退

    return app.exec();
}
```

把 `badClear` 换成上面修复版（`continue` 那版），稳如泰山。两版各跑一次，因果链锁死。

## 顺手一提：更粗但更稳的替代

如果 body 内容本来就是"整块换血"，其实可以不清布局，**把整个 bodyWidget 连根拔了重造**：

```cpp
void PortCardWidget::rebuildBody()
{
    if (bodyWidget) { bodyWidget->deleteLater(); }   // 整棵子树（布局+控件）一起走
    bodyWidget = new QWidget(this);
    bodyLayout = new QVBoxLayout(bodyWidget);
    rootLayout->addWidget(bodyWidget);               // rootLayout 是卡的根布局
    // …按 kind 往 bodyWidget 里建内容
}
```

控件销毁会连带销毁它的子控件和装在它身上的布局（Qt 的父子对象树），没有手工遍历就没有双重 delete 的机会。代价是每次重建整棵子树（本来就要全重建，无所谓）以及 `deleteLater` 的旧树在下一轮事件循环前还挂在树上（不 show 不影响观感）。**手工 `clearLayout` 适合"布局不动只换孩子"的场景，整块换血就别恋战。**

## 避坑清单

- 写任何 `takeAt` 循环之前，默念一遍：**`QLayout` 继承 `QLayoutItem`，子布局项和子布局是同一个对象**。`it->layout()` 非空 ⇒ `it` 自己就是个布局 ⇒ 删它一次、然后 `continue`。
- 崩在自写 clearLayout / delete 相关函数的，先查双重释放，再查悬垂访问——尤其崩溃点漂移、时崩时不崩的，八成是堆被写坏之后的延迟症状。
- `takeAt` 出来的 item 归你所有，三条出路：删掉、挂回别的布局、自己接管生命周期。没有第四条"装看不见"。
- 排查这类问题时 Debug 版比 Release 有用得多：MSVC Debug 堆 / glibc `MALLOC_CHECK_` / AddressSanitizer 都能把"第二次 free"钉死在第一现场，而不是等随机崩。
- 同一个项目同一天还踩过另一个 Qt 隐形契约——`slots` 被 `qobjectdefs.h` 定义成空宏（[上一篇](/posts/qt-slots-empty-macro-trap/)）。一个卡片控件改造，编译期一个坑、运行期一个坑，Qt 的"方便"背后全是不写在报错信息里的约定。

## 写在最后

这个 bug 最值得记的点：**错误代码读起来完全顺理成章**。"取项 → 是子布局就递归清 → 删子布局 → 是控件就延迟删 → 删项"，每一步都像最佳实践，连注释都不需要。它错在一条不显眼的继承关系上——`QLayout` 既是布局又是布局项——而这条关系决定了 `delete sub` 和 `delete it` 删的是同一个东西。

C++ 的所有权没有语言级保障，框架的所有权契约只能靠读文档和源码。写"资源管理轮子"之前，值得花两分钟翻一下相关类的继承图：**凡是"A 继承了它的管理器接口"的自指设计，都要问一句——我手里这个指针，和我要删的那个对象，是不是同一个？** 这次答案是"是"，下次未必，但问题值得每次都问。
