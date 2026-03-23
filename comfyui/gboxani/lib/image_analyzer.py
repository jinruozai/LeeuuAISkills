#!/usr/bin/env python3
"""
2.5D 菱形地图格图片分析器。

找到物体在图片中的实际菱形占地, 自动计算占地尺寸,
绘制 NxM 菱形网格, 并给出与标准 128x64 格子的缩放比。

贴合类型:
  edge   — 物体底部边缘贴合菱形下两条边 (建筑、树等)
  center — 物体脚部在菱形格中心位置 (角色)
"""

from PIL import Image, ImageDraw
import numpy as np
import sys
import os

CELL_W = 128  # 标准格子宽度
CELL_H = 64   # 标准格子高度
ALPHA_THRESHOLD = 30


# ───────────────────────── 位置检测 ─────────────────────────

def _find_bottom_vertex_edge(alpha):
    """
    edge 贴合: 找底部顶点。

    双候选策略:
    1) 滑动窗口密度检测 → 保守候选 (跳过零散装饰, 但可能错过细特征)
    2) 低阈值 count>=8 → 激进候选 (捕捉细特征如树根, 但可能包含装饰)
    3) V 形宽度匹配选择: 如果激进候选的内容贴合 V 形, 选它 (树根);
       否则选保守候选 (建筑)。
    """
    ys, xs = np.where(alpha > ALPHA_THRESHOLD)
    if len(ys) == 0:
        return None

    c1_all = 2 * ys - xs
    c2_all = 2 * ys + xs

    # 保守候选: 滑动窗口
    c1_con = _find_edge_c_sliding(c1_all)
    c2_con = _find_edge_c_sliding(c2_all)

    # 激进候选: 低阈值
    c1_agg = _max_c_with_min_count(c1_all, 8)
    c2_agg = _max_c_with_min_count(c2_all, 8)

    if c1_con is None or c2_con is None:
        if c1_agg is None or c2_agg is None:
            return None
        return (c2_agg - c1_agg) / 2.0, (c1_agg + c2_agg) / 4.0

    bx_con = (c2_con - c1_con) / 2.0
    by_con = (c1_con + c2_con) / 4.0

    if c1_agg is None or c2_agg is None:
        return bx_con, by_con

    bx_agg = (c2_agg - c1_agg) / 2.0
    by_agg = (c1_agg + c2_agg) / 4.0

    # 如果两者几乎一样, 用保守的
    if abs(by_agg - by_con) < 10:
        return bx_con, by_con

    # 用 V 形宽度匹配判断: 激进候选的内容是否贴合 V 形
    ratio = _v_width_ratio(alpha, bx_agg, by_agg)
    if ratio > 0.85:
        return bx_agg, by_agg  # 内容贴合 V 形 (如树根)
    else:
        return bx_con, by_con  # 选保守的 (如建筑, 跳过云)


def _find_edge_c_sliding(c_values, window_half=15):
    """滑动窗口密度检测, 找到物体主体边缘的 c 值。"""
    c_unique, c_counts = np.unique(c_values, return_counts=True)
    if len(c_unique) == 0:
        return None

    median_count = float(np.median(c_counts))
    density_threshold = max(30, median_count * 0.2)

    c_min, c_max = int(c_unique.min()), int(c_unique.max())
    hist = np.zeros(c_max - c_min + 1, dtype=np.int32)
    for c, cnt in zip(c_unique, c_counts):
        hist[int(c) - c_min] = cnt

    for i in range(len(hist) - 1, -1, -1):
        lo = max(0, i - window_half)
        hi = min(len(hist) - 1, i + window_half)
        if hist[lo:hi + 1].mean() >= density_threshold:
            return c_min + i

    mask = c_counts >= 20
    return int(c_unique[mask].max()) if mask.any() else None


def _max_c_with_min_count(c_values, min_count=8):
    """找最大的 c 值, 要求该 c 上至少有 min_count 个像素。"""
    c_unique, c_counts = np.unique(c_values, return_counts=True)
    mask = c_counts >= min_count
    if not mask.any():
        return None
    return int(c_unique[mask].max())


def _v_width_ratio(alpha, bx, by, dy_lo=15, dy_hi=38):
    """
    计算 V 形区域的内容宽度匹配度。

    在 dy_lo..dy_hi (较小的 dy) 范围内采样, 返回 max(content_width / V_width)。
    较小 dy 下: 树根宽度贴合 V 形 (ratio≈1), 云远窄于 V 形 (ratio<0.7)。
    """
    h, w = alpha.shape
    max_ratio = 0.0
    for dy in range(dy_lo, dy_hi, 3):
        y = int(by - dy)
        if y < 0 or y >= h:
            continue
        nz = np.where(alpha[y, :] > ALPHA_THRESHOLD)[0]
        if len(nz) < 3:
            continue
        content_w = float(nz[-1] - nz[0])
        v_width = 4.0 * dy
        ratio = content_w / v_width
        if ratio > max_ratio:
            max_ratio = ratio
    return max_ratio



def _find_feet_position(alpha):
    """center 贴合: 找到角色脚部位置 (中心区域底部)。"""
    ys, xs = np.where(alpha > ALPHA_THRESHOLD)
    if len(ys) == 0:
        return None

    x_min, x_max = int(xs.min()), int(xs.max())
    cx = (x_min + x_max) / 2.0
    content_w = x_max - x_min
    margin = content_w * 0.2

    center_mask = (xs >= cx - margin) & (xs <= cx + margin)
    if not center_mask.any():
        center_mask = np.ones_like(xs, dtype=bool)

    c_ys = ys[center_mask]
    c_xs = xs[center_mask]
    bottom_y = float(c_ys.max())
    feet_x = float(c_xs[c_ys >= bottom_y - 10].mean())
    return feet_x, bottom_y


# ───────────────────── 自然格子尺寸计算 ─────────────────────

def _find_natural_cell_size_center(alpha, cx, cy, nx, ny):
    """
    center 贴合: 在角色脚部区域找最大连续对称宽度, 推算自然格子尺寸。

    从中心向两侧连续延伸 (允许小间隙), 忽略分离的道具 (灯笼、飘带等)。
    取 min(左延伸, 右延伸)*2 作为对称宽度。
    菱形最大宽度 = (nx+ny)*cell_w/2, 由此反推 cell_w。
    """
    h = alpha.shape[0]

    ys_all, _ = np.where(alpha > ALPHA_THRESHOLD)
    if len(ys_all) == 0:
        return CELL_W
    y_top = int(ys_all.min())
    char_height = cy - y_top
    scan_height = max(50, int(char_height * 0.25))

    max_sym_w = 0.0

    for y in range(max(0, int(cy) - scan_height), min(h, int(cy) + 20)):
        nz = np.where(alpha[y, :] > ALPHA_THRESHOLD)[0]
        if len(nz) < 5:
            continue
        # 用 5th/95th 百分位, 过滤最外面的道具 (灯笼、飘带尖端)
        p5 = float(np.percentile(nz, 5))
        p95 = float(np.percentile(nz, 95))
        r = max(0.0, p95 - cx)
        l = max(0.0, cx - p5)
        sym_w = 2.0 * min(l, r)
        if sym_w > max_sym_w:
            max_sym_w = sym_w

    if max_sym_w < 20:
        return CELL_W

    cell_w = 2.0 * max_sym_w / (nx + ny)
    return max(cell_w, 50.0)


def _find_natural_cell_size_edge(alpha, bx, by, nx, ny):
    """
    edge 贴合: 推算自然格子尺寸。

    方法1 (比值法): 在标准菱形范围内扫描, 计算实际宽度与理论宽度的比值中位数。
    方法2 (高度法): 从底部向上扫描, 找到内容宽度突然翻倍的过渡点
                   (如树干→树冠), 用过渡高度反推 cell_w。
    取两者较大值。
    """
    h = alpha.shape[0]
    hh_std = CELL_H // 2
    total_h = (nx + ny) * hh_std
    scan_h = int(total_h * 1.5)

    ratios = []
    # 记录每个 dy 的内容宽度, 用于高度法
    dy_widths = []

    for dy in range(5, scan_h):
        y = int(by - dy)
        if y < 0 or y >= h:
            continue
        nz = np.where(alpha[y, :] > ALPHA_THRESHOLD)[0]
        if len(nz) < 5:
            continue
        actual_w = nz[-1] - nz[0]
        dy_widths.append((dy, actual_w))

        # 标准范围内: 计算比值
        if dy < total_h:
            lower_limit = min(nx, ny) * hh_std
            if dy <= lower_limit:
                theory_w = 4 * dy
            elif dy <= max(nx, ny) * hh_std:
                theory_w = 4 * lower_limit
            else:
                theory_w = 4 * (total_h - dy)
            if theory_w > 20:
                ratios.append(actual_w / theory_w)

    # 方法1: 比值法
    ratio_based = CELL_W
    if ratios:
        ratio_based = max(CELL_W * float(np.median(ratios)), CELL_W * 0.5)

    # 方法2: 高度法 — 找内容宽度突变点 (宽度在 30dy 内翻倍)
    height_based = 0.0
    look_ahead = 30
    for i, (dy, w) in enumerate(dy_widths):
        if w < 50:
            continue
        # 找 look_ahead 像素之后的宽度
        for j in range(i + 1, len(dy_widths)):
            dy2, w2 = dy_widths[j]
            if dy2 - dy >= look_ahead:
                if w2 > w * 2.0:
                    # 找到突变: 过渡点在 dy2 附近
                    transition_dy = dy2
                    # cell_h = transition_dy * 2 / (nx + ny)
                    # cell_w = 2 * cell_h
                    height_based = transition_dy * 4.0 / (nx + ny)
                break

    return max(ratio_based, height_based)


# ───────────────────────── 菱形几何 ─────────────────────────

def diamond_vertices(bx, by, nx, ny, cell_w, cell_h):
    """根据底部顶点和格子尺寸, 计算菱形四个顶点。"""
    hw = cell_w / 2.0
    hh = cell_h / 2.0
    bottom = (bx, by)
    left = (bx - nx * hw, by - nx * hh)
    top = (bx + (ny - nx) * hw, by - (nx + ny) * hh)
    right = (bx + ny * hw, by - ny * hh)
    return top, right, bottom, left


def diamond_center(bx, by, nx, ny, cell_w, cell_h):
    hw = cell_w / 2.0
    hh = cell_h / 2.0
    return bx + (ny - nx) * hw / 2.0, by - (nx + ny) * hh / 2.0


def grid_corner(left, i, j, cell_w, cell_h):
    hw = cell_w / 2.0
    hh = cell_h / 2.0
    return (left[0] + (i + j) * hw, left[1] + (i - j) * hh)


# ───────────────────────── 可视化 ─────────────────────────

def draw_result(img, bx, by, nx, ny, cell_w, cell_h, fit_type='edge'):
    """绘制菱形网格、扫描线和标记点 (仅线条, 无填充)。"""
    result = img.copy()
    w, h = result.size
    draw = ImageDraw.Draw(result, 'RGBA')

    top, right, bottom, left = diamond_vertices(bx, by, nx, ny, cell_w, cell_h)

    # 穿过底部顶点的两条扫描线 (绿色)
    extent = max(w, h)
    for slope in [0.5, -0.5]:
        pts = [(bx + dx, by + slope * dx)
               for dx in range(-extent, extent)
               if 0 <= bx + dx < w and 0 <= by + slope * dx < h]
        if len(pts) >= 2:
            draw.line(pts, fill=(0, 200, 0, 180), width=1)

    # 内部网格线
    for j in range(1, ny):
        draw.line([grid_corner(left, 0, j, cell_w, cell_h),
                   grid_corner(left, nx, j, cell_w, cell_h)],
                  fill=(255, 50, 50, 180), width=1)
    for i in range(1, nx):
        draw.line([grid_corner(left, i, 0, cell_w, cell_h),
                   grid_corner(left, i, ny, cell_w, cell_h)],
                  fill=(255, 50, 50, 180), width=1)

    # 外边框 (粗红线)
    for p1, p2 in [(top, right), (right, bottom), (bottom, left), (left, top)]:
        draw.line([p1, p2], fill=(255, 0, 0, 255), width=2)

    # 底部顶点 (黄色)
    r = 8
    draw.ellipse([bx - r, by - r, bx + r, by + r],
                 fill=(255, 255, 0, 255), outline=(255, 0, 0, 255), width=2)
    try:
        draw.text((bx + 12, by - 8), f"({bx:.0f},{by:.0f})",
                  fill=(255, 255, 0, 255))
    except Exception:
        pass

    # center 贴合: 标记中心点 (青色)
    if fit_type == 'center':
        cx, cy = diamond_center(bx, by, nx, ny, cell_w, cell_h)
        rc = 6
        draw.ellipse([cx - rc, cy - rc, cx + rc, cy + rc],
                     fill=(0, 255, 255, 255), outline=(0, 0, 200, 255), width=2)
        try:
            draw.text((cx + 10, cy - 12), f"center({cx:.0f},{cy:.0f})",
                      fill=(0, 255, 255, 255))
        except Exception:
            pass

    return result


# ───────────────────────── 主入口 ─────────────────────────

def analyze_image(image_path, nx, ny, fit_type='edge', output_path=None):
    """
    分析等轴测图片, 找到物体的自然菱形占地。

    Args:
        image_path: 输入图片路径 (RGBA)
        nx, ny: 占地格数
        fit_type: 'edge' 或 'center'
        output_path: 输出路径

    Returns:
        dict with bottom_vertex, natural_cell_w/h, scale, output_path
    """
    img = Image.open(image_path).convert('RGBA')
    alpha = np.array(img)[:, :, 3]
    h, w = alpha.shape

    print(f"图片: {os.path.basename(image_path)}  {w}x{h}")
    print(f"占地: {nx}x{ny}  贴合: {fit_type}")

    if fit_type == 'edge':
        result = _find_bottom_vertex_edge(alpha)
        if result is None:
            print("错误: 未找到物体边缘!")
            return None
        bx, by = result
        print(f"底部顶点: ({bx:.1f}, {by:.1f})")

        nat_cw = _find_natural_cell_size_edge(alpha, bx, by, nx, ny)

    elif fit_type == 'center':
        result = _find_feet_position(alpha)
        if result is None:
            print("错误: 未找到物体!")
            return None
        feet_x, feet_y = result
        print(f"脚部位置: ({feet_x:.1f}, {feet_y:.1f})")

        nat_cw = _find_natural_cell_size_center(alpha, feet_x, feet_y, nx, ny)

        nat_ch = nat_cw / 2.0
        hw = nat_cw / 2.0
        hh = nat_ch / 2.0
        bx = feet_x - (ny - nx) * hw / 2.0
        by = feet_y + (nx + ny) * hh / 2.0
    else:
        raise ValueError(f"未知贴合类型: {fit_type}")

    nat_ch = nat_cw / 2.0
    scale = CELL_W / nat_cw

    print(f"自然格子尺寸: {nat_cw:.1f}x{nat_ch:.1f}")
    print(f"缩放到标准 {CELL_W}x{CELL_H}: {scale:.3f}")

    top, right, bottom, left = diamond_vertices(bx, by, nx, ny, nat_cw, nat_ch)
    cx, cy = diamond_center(bx, by, nx, ny, nat_cw, nat_ch)
    print(f"菱形: 上({top[0]:.0f},{top[1]:.0f}) 右({right[0]:.0f},{right[1]:.0f}) "
          f"下({bottom[0]:.0f},{bottom[1]:.0f}) 左({left[0]:.0f},{left[1]:.0f})")

    result_img = draw_result(img, bx, by, nx, ny, nat_cw, nat_ch, fit_type)

    if output_path is None:
        base = os.path.splitext(os.path.basename(image_path))[0]
        out_dir = os.path.join(os.path.dirname(image_path), "analyzed")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{base}_analyzed.png")
    result_img.save(output_path)
    print(f"已保存: {output_path}")

    return {
        'bottom_vertex': (bx, by),
        'center': (cx, cy),
        'vertices': {'top': top, 'right': right, 'bottom': bottom, 'left': left},
        'natural_cell': (nat_cw, nat_ch),
        'scale': scale,
        'output_path': output_path,
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"用法: python {sys.argv[0]} <图片> <NxM> [edge|center]")
        sys.exit(1)

    image_path = sys.argv[1]
    nx, ny = map(int, sys.argv[2].split('x'))
    fit_type = sys.argv[3] if len(sys.argv) > 3 else 'edge'
    analyze_image(image_path, nx, ny, fit_type)
