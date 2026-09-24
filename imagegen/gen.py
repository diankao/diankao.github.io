"""为《两份盲文图形专利的成色》生成算法演示图（按专利步骤重演，非专利附图）。

输出到 static/images/braille-graphics-patents/，本目录整体被 gitignore。
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent.parent / "static" / "images" / "braille-graphics-patents"
OUT.mkdir(parents=True, exist_ok=True)

DOT = "#1a1a1a"
GRID = "#d9d9d9"
ACCENT = "#c0392b"


def save(fig, name):
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path)


# ---------------------------------------------------------------- 图一：贝塞尔曲线落格
def fig_bezier_grid():
    P = np.array([[1, 2], [5, 9], [9, 0], [14, 8]], float)  # P0..P3，专利称“拐点”

    def bezier(t):
        t = t[:, None]
        return ((1 - t) ** 3) * P[0] + 3 * t * (1 - t) ** 2 * P[1] \
            + 3 * t ** 2 * (1 - t) * P[2] + t ** 3 * P[3]

    ts = np.linspace(0, 1, 1001)  # 专利：t 步进 0.001
    pts = bezier(ts)
    cells = np.unique(np.floor(pts).astype(int), axis=0)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax in axes:
        for k in range(17):
            ax.plot([k, k], [0, 10], color=GRID, lw=0.7, zorder=1)
        for k in range(11):
            ax.plot([0, 16], [k, k], color=GRID, lw=0.7, zorder=1)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-0.5, 16.5)
        ax.set_ylim(-0.5, 10.5)

    ax = axes[0]
    ax.set_title("贝塞尔曲线与 1001 个采样点", fontsize=11)
    ax.plot(pts[:, 0], pts[:, 1], color=ACCENT, lw=1.4, zorder=2)
    ax.plot(*P.T, "--", color="#999", lw=0.9, zorder=2)
    ax.scatter(pts[:, 0], pts[:, 1], s=1.5, color=ACCENT, alpha=0.45, zorder=3)
    ax.scatter(P[:, 0], P[:, 1], s=42, marker="x", color=DOT, zorder=4)
    for i, (x, y) in enumerate(P):
        ax.annotate(f"P{i}", (x, y), textcoords="offset points", xytext=(6, 5), fontsize=9)

    ax = axes[1]
    ax.set_title("落格后的盲文点", fontsize=11)
    ax.plot(pts[:, 0], pts[:, 1], color=ACCENT, lw=0.8, ls=":", zorder=2, alpha=0.7)
    ax.scatter(cells[:, 0] + 0.5, cells[:, 1] + 0.5, s=130, color=DOT, zorder=3)
    save(fig, "01-bezier-grid.png")


# ------------------------------------------------------- 图二：位图块平均 + 固定阈值
def fig_bmp_threshold():
    h, w, n = 96, 144, 6  # n×n 像素块，仿专利 7×7 的例子
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, sigma = w * 0.38, h * 0.55, h * 0.34
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    blob = 1 - np.exp(-d2 / (2 * sigma ** 2))          # 深色团（油墨），边缘平滑过渡
    img = np.clip(np.dstack([blob, blob, blob]) * 255, 0, 255).astype(np.uint8)

    gh, gw = h // n, w // n
    blocks = blob[: gh * n, : gw * n].reshape(gh, n, gw, n).mean(axis=(1, 3))
    thr = 0.55                                          # 固定阈值，无抖动
    keep = blocks < thr
    cells = np.argwhere(keep)

    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.4))
    titles = ["原图：平滑灰度过渡", f"{n}×{n} 像素块平均灰度", "固定阈值后的点阵"]
    datas = [img, blocks]
    for ax, t in zip(axes, titles):
        ax.set_title(t, fontsize=11)
        ax.axis("off")
    for ax, d in zip(axes[:2], datas):
        ax.imshow(d, cmap="gray", vmin=0, vmax=1, aspect="equal")
    axes[2].set_facecolor("white")
    axes[2].scatter(cells[:, 1] + 0.5, cells[:, 0] + 0.5, s=26, color=DOT)
    axes[2].set_xlim(0, gw)
    axes[2].set_ylim(gh, 0)
    axes[2].set_aspect("equal")
    save(fig, "02-bmp-threshold.png")


# --------------------------------------------------- 图三：均匀填充 vs 逐层轮廓填充
def _erode(mask, k):
    m = mask.copy()
    for _ in range(k):
        p = np.pad(m, 1, constant_values=False)
        m = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:] \
            & p[:-2, :-2] & p[:-2, 2:] & p[2:, :-2] & p[2:, 2:]
    return m


def _mask(shape):
    """演示区域：A 圆角矩形 + 圆孔；B 椭圆 + 三角孔。"""
    ss, W, H = 4, 460, 300
    img = Image.new("L", (W * ss, H * ss), 0)
    dr = ImageDraw.Draw(img)
    if shape == "A":
        dr.rounded_rectangle([30 * ss, 40 * ss, 430 * ss, 260 * ss], radius=36 * ss, fill=255)
        dr.ellipse([182 * ss, 102 * ss, 278 * ss, 198 * ss], fill=0)
    else:
        dr.ellipse([36 * ss, 26 * ss, 424 * ss, 274 * ss], fill=255)
        dr.polygon([(230 * ss, 96 * ss), (172 * ss, 208 * ss), (288 * ss, 208 * ss)], fill=0)
    m = np.asarray(img) > 128
    return m[::ss, ::ss]


def fig_fill_compare():
    W, H = 460, 300
    mask = _mask("A")
    hole_c, hole_r = (230.0, 150.0), 48.0
    tip_c, tip_r = (230.0, 150.0), 32.0  # 指尖盖在圆孔上，点环应在指尖圈外
    TIP = "#444444"

    # 均匀撒点：固定点距网格
    pitch, dots_u = 10, []
    for y in range(0, H, pitch):
        for x in range(0, W, pitch):
            if mask[y, x]:
                dots_u.append((x, y))

    # 逐层轮廓填充：取最外轮廓 -> 按最小间距选点 -> 向内腐蚀 -> 循环
    R, dots_l = 9, []
    remaining = mask.copy()
    while remaining.any():
        boundary = remaining & ~_erode(remaining, 1)
        kept = []
        for y, x in np.argwhere(boundary):
            if all((y - ky) ** 2 + (x - kx) ** 2 >= R ** 2 for ky, kx in kept):
                kept.append((y, x))
        dots_l.extend(kept)
        remaining = _erode(remaining, 8)

    zx0, zx1, zy0, zy1 = 162, 298, 82, 218  # 以圆孔为中心的放大窗口

    fig = plt.figure(figsize=(10, 7.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.45, 1])
    ax_top = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    ax_zoom = fig.add_subplot(gs[1, :])

    for ax, dots, title in zip(ax_top, (dots_u, dots_l),
                               ("均匀撒点填充", "逐层轮廓填充")):
        d = np.array(dots)
        ax.set_facecolor("white")
        ax.scatter(d[:, 0], d[:, 1], s=5, color=DOT, linewidths=0)
        ax.add_patch(plt.Circle(tip_c, tip_r, fill=False, ec=TIP, lw=1.5, ls=(0, (4, 3))))
        ax.set_title(title, fontsize=11)
        ax.set_aspect("equal")
        ax.set_xlim(0, W)
        ax.set_ylim(H, 0)
        ax.axis("off")

    # 放大：均匀撒点在指尖范围里的样子（棋盘格锯齿）
    d = np.array(dots_u)
    ax = ax_zoom
    ax.set_facecolor("white")
    ax.add_patch(plt.Circle(hole_c, hole_r, fc="#f3f3f3", ec="none", zorder=0))
    for g in range(170, 291, 10):
        ax.plot([g, g], [zy0, zy1], color=GRID, lw=0.6, zorder=1)
    for g in range(90, 211, 10):
        ax.plot([zx0, zx1], [g, g], color=GRID, lw=0.6, zorder=1)
    zd = d[(d[:, 0] >= zx0) & (d[:, 0] <= zx1)
           & (d[:, 1] >= zy0) & (d[:, 1] <= zy1)]
    ax.scatter(zd[:, 0], zd[:, 1], s=9, color=DOT, linewidths=0, zorder=3)
    ax.add_patch(plt.Circle(hole_c, hole_r, fill=False, ec=ACCENT,
                            lw=1.3, ls=(0, (4, 3)), zorder=2))
    ax.add_patch(plt.Circle(tip_c, tip_r, fill=False, ec=TIP,
                            lw=1.5, ls=(0, (4, 3)), zorder=2))
    ax.set_title("放大：指尖摸到的是多边形", fontsize=11)
    ax.set_aspect("equal")
    ax.set_xlim(zx0, zx1)
    ax.set_ylim(zy1, zy0)
    ax.axis("off")

    ax_top[0].annotate("指尖接触范围", (tip_c[0], 108), ha="center", fontsize=8.5,
                       color=TIP, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    ax_zoom.annotate("指尖", tip_c, ha="center", va="center", fontsize=9,
                     color=TIP, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    ax_zoom.annotate("真实圆轮廓", (hole_c[0], 99), ha="center", va="bottom", fontsize=8.5,
                     color=ACCENT, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    save(fig, "03-fill-compare.png")


if __name__ == "__main__":
    fig_bezier_grid()
    fig_bmp_threshold()
    fig_fill_compare()
