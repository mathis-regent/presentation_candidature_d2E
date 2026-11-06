"""Detailed interior of the ground-floor living space, positioned from the plan.

Open space (plan): kitchen with L worktop + island, dining table by the glass bay,
séjour with L sofa, fireplace (cheminée) and TV, quarter-turn stair (D -> A) in the corner,
doors to the shoe/coat closet and the garage, WC box.
"""
import math
import numpy as np
import bpy
from lib import MeshBuilder, BOX, CBOX, mesh_np, coll, rot_z
import materials as M
import veg
from house import PX, PYg, PYu, HL, HD, T, FFL0, FFL1, ZE

XI0, XI1, YI0, YI1 = -HL + T, HL - T, -HD + T, HD - T
XW = PX(897) + 0.05          # east face of the séjour/buanderie partition (fireplace wall)
XE = PX(1245) - 0.05         # west face of the séjour/garage partition
YWC = PYg(465)               # south face of the WC box
XWC = PX(990) + 0.05         # east face of the WC box (kitchen run A wall)
ZB = 3.0                     # underside of ceiling boards
ZJ = ZB - 0.11               # joist bottom
ZBM = ZJ - 0.27              # beam bottom
# quarter-turn stair in the SE corner (D at the garage wall, A at the top near the entrance)
ST_W = 0.82
ST_X1 = XE                   # east wall
ST_YS = YI0                  # south wall
ST_RUN = 0.26
ST_N = 17
ST_RISE = (FFL1 - FFL0) / ST_N
VOID = [(ST_X1 - 10 * ST_RUN - ST_W - 0.02, ST_X1, ST_YS, ST_YS + ST_W),   # south run
        (ST_X1 - ST_W, ST_X1, ST_YS + ST_W, ST_YS + ST_W + 4 * ST_RUN + 0.05)]  # east run


def box(mb, x0, x1, y0, y1, z0, z1, mat=0, attr=None, tpl=None, rng=None):
    mb.add_box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2),
               mat=mat, fattr=(rng.random() if (attr is None and rng is not None) else (attr or 0.0)), template=tpl)


def lathe(mb, prof, cx, cy, z0=0.0, n=28, mat=0, attr=0.0):
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    V = []
    for (r, z) in prof:
        r = max(r, 1e-4)
        V.append(np.column_stack([cx + r * np.cos(ang), cy + r * np.sin(ang), np.full(n, z0 + z)]))
    V = np.concatenate(V)
    F = []
    for i in range(len(prof) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            F.append([a, b, b + n, a + n])
    mb.add(V, F, mat, attr)


def rect_minus(rect, holes):
    """Split rect (x0,x1,y0,y1) into pieces not covered by axis-aligned holes."""
    xs = sorted(set([rect[0], rect[1]] + [v for h in holes for v in h[:2] if rect[0] < v < rect[1]]))
    ys = sorted(set([rect[2], rect[3]] + [v for h in holes for v in h[2:] if rect[2] < v < rect[3]]))
    out = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if not any(h[0] < cx < h[1] and h[2] < cy < h[3] for h in holes):
                out.append((xs[i], xs[i + 1], ys[j], ys[j + 1]))
    return out


# ----------------------------------------------------------------------------
def structure(col, rng):
    """Floors, ceilings with oak beams, partitions with doors, upper floor."""
    mb = MeshBuilder()  # 0 plaster 1 floor stone 2 beam-y 3 joist-x 4 boards-x 5 oak door 6 black metal 7 oak floor
    # ground floor limestone flags (opus: rows of random lengths)
    box(mb, XI0, XI1, YI0, YI1, FFL0 - 0.12, FFL0 - 0.03, 0)
    y = YI0
    while y < YI1 - 0.01:
        rw = min(rng.choice([0.4, 0.5, 0.6]), YI1 - y)
        x = XI0 - rng.uniform(0, 0.4)
        while x < XI1:
            L = rng.choice([0.4, 0.5, 0.6, 0.8])
            xa, xb = max(x, XI0), min(x + L, XI1)
            if xb - xa > 0.05:
                box(mb, xa + 0.003, xb - 0.003, y + 0.003, y + rw - 0.003, FFL0 - 0.03, FFL0 + rng.uniform(-0.0015, 0.0), 1, rng=rng)
            x += L
        y += rw
    # ceiling boards + upper floor slab with the stair void
    for (x0, x1, y0, y1) in rect_minus((XI0, XI1, YI0, YI1), VOID):
        box(mb, x0, x1, y0, y1, ZB, ZB + 0.03, 0)
        box(mb, x0, x1, y0, y1, ZB + 0.03, FFL1 - 0.02, 0)
        box(mb, x0, x1, y0, y1, FFL1 - 0.02, FFL1, 7, rng=rng)
    # main beams (along Y) and joists (along X)
    beams = [-1.25, 1.0, 3.6, 6.6]
    for bx in beams:
        y0 = YI0
        if bx > VOID[1][0] - 0.15:
            y0 = VOID[1][3]
        box(mb, bx - 0.125, bx + 0.125, y0, YI1, ZBM, ZJ, 2, rng=rng)
    box(mb, VOID[1][0] - 0.1, XE, VOID[1][3], VOID[1][3] + 0.22, ZBM + 0.05, ZJ, 2, rng=rng)    # trimmer
    box(mb, VOID[0][0] - 0.2, VOID[1][0], VOID[0][3], VOID[0][3] + 0.2, ZBM + 0.05, ZJ, 2, rng=rng)
    yj = YI0 + 0.25
    while yj < YI1 - 0.1:
        segs = [(XI0, XI1)]
        for (x0, x1, y0, y1) in VOID:
            if y0 - 0.05 < yj < y1 + 0.05:
                segs = [(a, min(b, x0)) if a < x0 else (max(a, x1), b) for (a, b) in segs]
        for (a, b) in segs:
            if b - a > 0.2:
                box(mb, a, b, yj - 0.04, yj + 0.04, ZJ, ZB, 3, rng=rng)
        yj += 0.42

    zt = ZB  # partitions run up to the boards

    def wall_x(x, y0, y1, z0=FFL0 - 0.03, z1=zt, doors=()):
        y0, y1 = min(y0, y1), max(y0, y1)
        cuts = sorted(doors)
        ya = y0
        for (d0, d1) in cuts:
            box(mb, x - 0.05, x + 0.05, ya, d0, z0, z1, 0)
            box(mb, x - 0.05, x + 0.05, d0, d1, FFL0 + 2.15, z1, 0)
            # door leaf (closed, oak) + frame + handle on both faces
            for sx in (-1, 1):
                box(mb, x + sx * 0.05, x + sx * 0.065, d0 - 0.07, d0, FFL0, FFL0 + 2.22, 0)
                box(mb, x + sx * 0.05, x + sx * 0.065, d1, d1 + 0.07, FFL0, FFL0 + 2.22, 0)
                box(mb, x + sx * 0.05, x + sx * 0.065, d0 - 0.07, d1 + 0.07, FFL0 + 2.15, FFL0 + 2.22, 0)
                box(mb, x + sx * 0.03, x + sx * 0.035, d0 + 0.01, d1 - 0.01, FFL0 + 0.005, FFL0 + 2.145, 5, rng=rng)
                box(mb, x + sx * 0.035, x + sx * 0.08, d1 - 0.1, d1 - 0.07, FFL0 + 1.02, FFL0 + 1.05, 6)
            ya = d1
        box(mb, x - 0.05, x + 0.05, ya, y1, z0, z1, 0)

    def wall_y(y, x0, x1, z0=FFL0 - 0.03, z1=zt, doors=()):
        x0, x1 = min(x0, x1), max(x0, x1)
        xa = x0
        for (d0, d1) in sorted(doors):
            box(mb, xa, d0, y - 0.05, y + 0.05, z0, z1, 0)
            box(mb, d0, d1, y - 0.05, y + 0.05, FFL0 + 2.15, z1, 0)
            for sy in (-1, 1):
                box(mb, d0 - 0.07, d0, y + sy * 0.05, y + sy * 0.065, FFL0, FFL0 + 2.22, 0)
                box(mb, d1, d1 + 0.07, y + sy * 0.05, y + sy * 0.065, FFL0, FFL0 + 2.22, 0)
                box(mb, d0 - 0.07, d1 + 0.07, y + sy * 0.05, y + sy * 0.065, FFL0 + 2.15, FFL0 + 2.22, 0)
                box(mb, d0 + 0.01, d1 - 0.01, y + sy * 0.03, y + sy * 0.035, FFL0 + 0.005, FFL0 + 2.145, 5, rng=rng)
                box(mb, d1 - 0.1, d1 - 0.07, y + sy * 0.035, y + sy * 0.08, FFL0 + 1.02, FFL0 + 1.05, 6)
            xa = d1
        box(mb, xa, x1, y - 0.05, y + 0.05, z0, z1, 0)

    # ground floor partitions (plan)
    wall_x(PX(757), YI1, PYg(470))
    wall_y(PYg(470), XI0, PX(897))
    wall_x(PX(897), YI1, YWC)                                   # WC west / SDB
    wall_x(PX(990), YI1, YWC)                                   # WC east (kitchen run A)
    wall_y(YWC, PX(897), PX(990), doors=[(PX(925), PX(955))])   # WC door (arc on the plan)
    wall_x(PX(897), PYg(497), YI0)                              # fireplace wall
    wall_x(PX(715), PYg(497), YI0)
    wall_y(PYg(497), PX(715), PX(897))
    wall_x(PX(1245), YI1, YI0, doors=[(PYg(498), PYg(482)), (PYg(580), PYg(547))])  # closet + garage doors
    wall_y(PYg(458), PX(1245), XI1)
    wall_y(PYg(517), PX(1245), XI1)
    # first floor partitions
    u0, u1 = FFL1, ZE - 0.26
    wall_x(PX(720), YI1, PYu(835), u0, u1)
    wall_x(PX(897), YI1, PYu(835), u0, u1)
    wall_y(PYu(835), XI0, PX(897), u0, u1)
    wall_y(PYu(870), XI0, PX(988), u0, u1)
    wall_x(PX(720), PYu(870), YI0, u0, u1)
    wall_x(PX(902), PYu(870), YI0, u0, u1)
    wall_x(PX(988), PYu(870), YI0, u0, u1)
    wall_x(PX(1077), YI1, YI0, u0, u1)
    wall_x(PX(1260), YI1, YI0, u0, u1)
    box(mb, XI0, XI1, YI0, YI1, ZE - 0.26, ZE - 0.2, 0)        # upper ceiling
    return mb.build('int_structure', [M.get('plaster'), M.get('floor_stone'), M.get('oak_beam_y'),
                                      M.get('oak_beam_x'), M.get('oak_beam_x'), M.get('oak_v'),
                                      M.get('black_metal'), M.get('floor')], col)


# ----------------------------------------------------------------------------
def stairs(col, rng):
    mb = MeshBuilder()  # 0 plaster 1 oak tread 2 black steel
    steps = []
    # D: start at the garage wall going south (east run, 4 treads), 3 winders, then west (10 treads) to A
    x0e = ST_X1 - ST_W
    for k in range(4):
        ytop = VOID[1][3] - k * ST_RUN
        steps.append(('E', (x0e, ST_X1, ytop - ST_RUN, ytop)))
    for k in range(3):
        steps.append(('W', k))
    for k in range(10):
        xr = ST_X1 - ST_W - k * ST_RUN
        steps.append(('S', (xr - ST_RUN, xr, ST_YS, ST_YS + ST_W)))
    corner = (ST_X1 - ST_W, ST_X1, ST_YS, ST_YS + ST_W)
    for i, (kind, g) in enumerate(steps):
        ztop = FFL0 + (i + 1) * ST_RISE
        if kind == 'W':
            # winders: corner square split into 3 triangular-ish treads (approximated by boxes)
            cx0, cx1, cy0, cy1 = corner
            parts = [(cx0, cx1, cy0 + ST_W * 0.55, cy1), (cx0 + ST_W * 0.45, cx1, cy0, cy1), (cx0, cx1, cy0, cy1)]
            g = parts[g]
        x0, x1, y0, y1 = g
        box(mb, x0, x1, y0, y1, FFL0 - 0.03, ztop - 0.045, 0)
        ox = 0.03 if kind == 'S' else 0.0
        oy = 0.03 if kind == 'E' else 0.0
        box(mb, x0 - ox, x1, y0 - oy, y1, ztop - 0.045, ztop, 1, rng=rng)
    # black steel handrail on the open side
    pts = []
    for i, (kind, g) in enumerate(steps):
        ztop = FFL0 + (i + 1) * ST_RISE
        if kind == 'E':
            pts.append((g[0] - 0.02, (g[2] + g[3]) / 2, ztop))
        elif kind == 'S':
            pts.append(((g[0] + g[1]) / 2, g[3] + 0.02, ztop))
    for (x, y, z) in pts[::2]:
        box(mb, x - 0.012, x + 0.012, y - 0.012, y + 0.012, z, z + 0.92, 2)
    for a, b in zip(pts[:-1], pts[1:]):
        if abs(a[0] - b[0]) > 0.5 and abs(a[1] - b[1]) > 0.5:
            continue
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        z = (a[2] + b[2]) / 2 + 0.92
        box(mb, x0 - 0.015, x1 + 0.015, y0 - 0.015, y1 + 0.015, z - 0.02 - abs(b[2] - a[2]) / 2, z + 0.02 + abs(b[2] - a[2]) / 2, 2)
    return mb.build('int_stairs', [M.get('plaster'), M.get('oak_x'), M.get('black_metal')], col)


# ----------------------------------------------------------------------------
def kitchen(col, rng):
    mb = MeshBuilder()  # 0 cabinet 1 worktop 2 brass 3 dark plinth 4 steel 5 black glass 6 oak 7 ceramic white 8 ceramic earth 9 glass
    top0, top1 = FFL0 + 0.87, FFL0 + 0.91
    dep = 0.62
    # run A: along the WC box east face, facing +X
    xa0, xa1 = XWC, XWC + dep
    ya0, ya1 = YWC, YI1
    box(mb, xa0, xa1, ya0, ya0 + 0.62, FFL0, FFL0 + 2.25, 0)                 # tall column (fridge/oven)
    for z0, z1 in ((FFL0 + 0.1, FFL0 + 1.3), (FFL0 + 1.3, FFL0 + 2.25)):
        box(mb, xa1, xa1 + 0.005, ya0 + 0.003, ya0 + 0.617, z0 + 0.003, z1 - 0.003, 0)
        box(mb, xa1 + 0.005, xa1 + 0.03, ya0 + 0.55, ya0 + 0.565, z0 + 0.15, z0 + 0.55, 2)
    box(mb, xa0, xa1 - 0.06, ya0 + 0.62, ya1, FFL0, FFL0 + 0.1, 3)
    box(mb, xa0, xa1, ya0 + 0.62, ya1 - dep, FFL0 + 0.1, top0, 0)
    y = ya0 + 0.62
    while y < ya1 - dep - 0.05:
        w = min(0.6, ya1 - dep - y)
        for (z0, z1) in ((FFL0 + 0.1, FFL0 + 0.38), (FFL0 + 0.38, FFL0 + 0.62), (FFL0 + 0.62, top0)):
            box(mb, xa1, xa1 + 0.004, y + 0.0015, y + w - 0.0015, z0 + 0.0015, z1 - 0.0015, 0)
            box(mb, xa1 + 0.004, xa1 + 0.025, y + w / 2 - 0.08, y + w / 2 + 0.08, z1 - 0.06, z1 - 0.048, 2)
        y += w
    # run B: along the garden wall, facing -Y
    yb0, yb1 = YI1 - dep, YI1
    xb0, xb1 = XWC, 3.45
    box(mb, xb0, xb1, yb0 + 0.06, yb1, FFL0, FFL0 + 0.1, 3)
    box(mb, xb0, xb1, yb0, yb1, FFL0 + 0.1, top0, 0)
    x = xa1
    while x < xb1 - 0.05:
        w = min(0.6, xb1 - x)
        for (z0, z1) in ((FFL0 + 0.1, FFL0 + 0.48), (FFL0 + 0.48, top0)):
            box(mb, x + 0.0015, x + w - 0.0015, yb0 - 0.004, yb0, z0 + 0.0015, z1 - 0.0015, 0)
            box(mb, x + w / 2 - 0.08, x + w / 2 + 0.08, yb0 - 0.025, yb0 - 0.004, z1 - 0.06, z1 - 0.048, 2)
        x += w
    # worktops
    box(mb, xa0, xa1 + 0.02, ya0 + 0.62, yb1, top0, top1, 1)
    box(mb, xa0, xb1 + 0.02, yb0 - 0.02, yb1, top0, top1, 1)
    box(mb, xa0, xa0 + 0.015, ya0 + 0.62, yb1, top1, top1 + 0.12, 1)       # upstand
    # sink under the kitchen window + brass tap
    sx = PX(1045)
    box(mb, sx - 0.36, sx + 0.36, yb0 + 0.1, yb1 - 0.1, top1 - 0.002, top1 + 0.0005, 4)
    box(mb, sx - 0.33, sx + 0.33, yb0 + 0.13, yb1 - 0.13, top1 - 0.2, top1, 3)
    tap = [(sx, yb1 - 0.07, top1), (sx, yb1 - 0.07, top1 + 0.3), (sx, yb1 - 0.1, top1 + 0.36),
           (sx, yb1 - 0.22, top1 + 0.36), (sx, yb1 - 0.25, top1 + 0.3)]
    for a, b in zip(tap[:-1], tap[1:]):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        z0, z1 = sorted((a[2], b[2]))
        box(mb, x0 - 0.012, x1 + 0.012, y0 - 0.012, y1 + 0.012, z0 - 0.012, z1 + 0.012, 2)
    # open oak shelves on the WC wall with ceramics
    for zz in (FFL0 + 1.45, FFL0 + 1.85):
        box(mb, xa0, xa0 + 0.26, ya0 + 0.9, yb0 - 0.05, zz - 0.035, zz, 6, rng=rng)
        yy = ya0 + 1.0
        while yy < yb0 - 0.25:
            kind = rng.integers(0, 3)
            if kind == 0:   # stack of plates
                for k in range(rng.integers(3, 7)):
                    lathe(mb, [(0.0, 0.0), (0.11, 0.004), (0.13, 0.018)], xa0 + 0.14, yy + 0.13, zz + k * 0.018, mat=7)
                yy += 0.3
            elif kind == 1:  # bowls
                for k in range(2):
                    lathe(mb, [(0.0, 0.0), (0.04, 0.0), (0.075, 0.04), (0.085, 0.07)], xa0 + 0.14, yy + 0.09 + k * 0.17, zz, mat=8)
                yy += 0.36
            else:            # jar
                lathe(mb, [(0.0, 0.0), (0.06, 0.0), (0.065, 0.02), (0.065, 0.2), (0.05, 0.22), (0.045, 0.24)],
                      xa0 + 0.14, yy + 0.08, zz, mat=9)
                yy += 0.2
    # island (work side faces the run B), seating overhang towards the séjour
    ix0, ix1, iy0, iy1 = 2.05, 3.45, 1.65, 2.75
    box(mb, ix0 + 0.06, ix1 - 0.06, iy0 + 0.06, iy1 - 0.06, FFL0, FFL0 + 0.1, 3)
    box(mb, ix0, ix1, iy0, iy1, FFL0 + 0.1, top0, 6, rng=rng)
    x = ix0
    while x < ix1 - 0.05:
        w = min(0.7, ix1 - x)
        box(mb, x + 0.0015, x + w - 0.0015, iy1, iy1 + 0.004, FFL0 + 0.1015, top0 - 0.0015, 0)
        box(mb, x + w / 2 - 0.09, x + w / 2 + 0.09, iy1 + 0.004, iy1 + 0.025, top0 - 0.08, top0 - 0.068, 2)
        x += w
    box(mb, ix0 - 0.03, ix1 + 0.03, iy0 - 0.3, iy1 + 0.03, top0, top1 + 0.01, 1)
    box(mb, 2.45, 3.05, 2.2, 2.62, top1 + 0.01, top1 + 0.016, 5)          # induction hob
    return mb.build('int_kitchen', [M.get('cabinet'), M.get('worktop'), M.get('brass'), M.get('dark_wood'),
                                    M.get('steel'), M.get('screen'), M.get('oak_x'), M.get('ceramic_white'),
                                    M.get('ceramic_earth'), M.get('glass')], col)


def chair(mb, x, y, yaw, rng, mat=0):
    """Spindle-back wooden chair, local front = -Y before rotation."""
    R = rot_z(yaw)
    parts = []
    sh = FFL0 + 0.45
    parts.append(((0, 0, sh - 0.02), (0.22, 0.21, 0.02)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            hh = (sh - 0.04 - FFL0) / 2
            parts.append(((sx * 0.19, sy * 0.18, FFL0 + hh), (0.016, 0.016, hh)))
        parts.append(((sx * 0.19, 0.19, sh + 0.22), (0.016, 0.016, 0.24)))
    parts.append(((0, 0.19, sh + 0.45), (0.22, 0.02, 0.03)))
    for k in range(-2, 3):
        parts.append(((k * 0.065, 0.19, sh + 0.21), (0.008, 0.008, 0.22)))
    parts.append(((0, 0.0, FFL0 + 0.16), (0.18, 0.008, 0.008)))
    for (c, h) in parts:
        c = np.array(c)
        cc = R @ np.array([c[0], c[1], 0.0])
        mb.add_box((x + cc[0], y + cc[1], c[2]), h, R=R, mat=mat, fattr=rng.random())


def dining(col, rng):
    mb = MeshBuilder()  # 0 black chair 1 oak table 2 ceramic 3 black metal 4 lamp glow 5 terracotta 6 leather 7 rattan
    tx0, tx1, ty0, ty1 = PX(1165), PX(1207), PYg(455), PYg(377)
    top = FFL0 + 0.76
    box(mb, tx0, tx1, ty0, ty1, top - 0.05, top, 1, tpl=CBOX, attr=0.3)
    for yy in (ty0 + 0.3, ty1 - 0.3):
        box(mb, (tx0 + tx1) / 2 - 0.4, (tx0 + tx1) / 2 + 0.4, yy - 0.05, yy + 0.05, top - 0.12, top - 0.05, 1, attr=0.5)
        box(mb, (tx0 + tx1) / 2 - 0.06, (tx0 + tx1) / 2 + 0.06, yy - 0.05, yy + 0.05, FFL0 + 0.05, top - 0.12, 1, attr=0.6)
        box(mb, (tx0 + tx1) / 2 - 0.42, (tx0 + tx1) / 2 + 0.42, yy - 0.06, yy + 0.06, FFL0, FFL0 + 0.06, 1, attr=0.7)
    box(mb, (tx0 + tx1) / 2 - 0.03, (tx0 + tx1) / 2 + 0.03, ty0 + 0.3, ty1 - 0.3, FFL0 + 0.25, FFL0 + 0.32, 1, attr=0.8)
    for k in range(3):
        yy = ty0 + (ty1 - ty0) * (k + 0.5) / 3
        chair(mb, tx0 - 0.28, yy + rng.normal(0, 0.03), -math.pi / 2 + rng.normal(0, 0.05), rng)
        chair(mb, tx1 + 0.28, yy + rng.normal(0, 0.03), math.pi / 2 + rng.normal(0, 0.05), rng)
    chair(mb, (tx0 + tx1) / 2, ty0 - 0.3, math.pi, rng)
    # vase with olive branches + bowl on the table
    cx = (tx0 + tx1) / 2
    lathe(mb, [(0.0, 0.0), (0.07, 0.0), (0.1, 0.08), (0.08, 0.22), (0.045, 0.27), (0.05, 0.3)], cx, ty1 - 0.6, top, mat=2)
    lathe(mb, [(0.0, 0.0), (0.08, 0.0), (0.16, 0.06), (0.18, 0.09)], cx, ty0 + 0.7, top, mat=5)
    # pendants above table and island
    for (px, py) in ((cx, ty0 + 0.6), (cx, ty1 - 0.6), (2.45, 2.2), (3.05, 2.2)):
        zb = FFL0 + 1.95 if py > 3.0 or px > 4 else FFL0 + 1.85
        lathe(mb, [(0.2, 0.0), (0.19, 0.06), (0.12, 0.17), (0.04, 0.22), (0.02, 0.24)], px, py, zb, mat=3)
        lathe(mb, [(0.185, 0.003), (0.175, 0.06), (0.11, 0.16), (0.035, 0.205)], px, py, zb, mat=4)
        box(mb, px - 0.004, px + 0.004, py - 0.004, py + 0.004, zb + 0.24, ZJ, 3)
    # island stools (leather seat, black frame)
    for sx in (2.4, 3.1):
        sy = 1.25
        lathe(mb, [(0.0, FFL0 + 0.62), (0.17, FFL0 + 0.62), (0.18, FFL0 + 0.66), (0.0, FFL0 + 0.67)], sx, sy, 0, mat=6)
        for a in range(4):
            ang = a * math.pi / 2 + math.pi / 4
            px, py = sx + 0.14 * math.cos(ang), sy + 0.14 * math.sin(ang)
            box(mb, px - 0.012, px + 0.012, py - 0.012, py + 0.012, FFL0, FFL0 + 0.62, 3)
        box(mb, sx - 0.15, sx + 0.15, sy - 0.006, sy + 0.006, FFL0 + 0.25, FFL0 + 0.27, 3)
    # fruit bowl on the island
    lathe(mb, [(0.0, 0.0), (0.1, 0.0), (0.18, 0.07), (0.2, 0.1)], 2.75, 1.85, FFL0 + 0.92, mat=2)
    for k in range(5):
        a = k * 1.3
        mb.add_box((2.75 + 0.08 * math.cos(a), 1.85 + 0.08 * math.sin(a), FFL0 + 0.97), (0.04, 0.04, 0.04),
                   mat=5, fattr=rng.random(), template=CBOX)
    return mb.build('int_dining', [M.get('black_paint'), M.get('oak_y'), M.get('ceramic_white'), M.get('black_metal'),
                                   M.get('lamp'), M.get('ceramic_earth'), M.get('leather'), M.get('rattan')], col)


def living(col, rng):
    mb = MeshBuilder()  # 0 linen 1 cushions 2 rug 3 oak 4 stone(worktop) 5 screen 6 dressed stone 7 soot 8 plaster 9 books 10 ceramic 11 bark 12 black metal 13 shade glow
    f0 = FFL0
    # L sofa, back to the kitchen, facing the TV on the south wall
    sx0, sx1, sy1, sy0 = -1.8, 0.5, -1.5, -2.45
    box(mb, sx0 + 0.1, sx1 - 0.1, sy0, sy1 - 0.1, f0 + 0.05, f0 + 0.38, 0, tpl=CBOX)
    box(mb, sx1 - 0.95, sx1 - 0.1, -3.3 + 0.004, sy0 + 0.05, f0 + 0.05, f0 + 0.379, 0, tpl=CBOX)
    box(mb, sx0 + 0.19, sx1 - 0.19, sy1 - 0.24, sy1 + 0.008, f0 + 0.05, f0 + 0.78, 0, tpl=CBOX)        # back
    box(mb, sx0 - 0.008, sx0 + 0.2, sy0 - 0.008, sy1 + 0.008, f0 + 0.05, f0 + 0.62, 0, tpl=CBOX)      # arm
    box(mb, sx1 - 0.2, sx1 + 0.008, -3.3 - 0.008, sy1 + 0.008, f0 + 0.05, f0 + 0.62, 0, tpl=CBOX)    # arm (chaise side)
    for k in range(3):                                                           # seat cushions
        a = sx0 + 0.2 + k * (sx1 - 0.2 - sx0 - 0.2) / 3
        b = a + (sx1 - 0.2 - sx0 - 0.2) / 3
        box(mb, a + 0.005, b - 0.005, sy0 + 0.02, sy1 - 0.24, f0 + 0.38, f0 + 0.5, 0, tpl=CBOX)
        box(mb, a + 0.01, b - 0.01, sy1 - 0.42, sy1 - 0.22, f0 + 0.5, f0 + 0.95, 0, tpl=CBOX)
    box(mb, sx1 - 0.95 + 0.01, sx1 - 0.21, -3.28, sy0 + 0.02, f0 + 0.38, f0 + 0.5, 0, tpl=CBOX)
    for (cx, cy, rz, a) in ((-1.45, sy1 - 0.45, 0.2, 0.1), (-1.1, sy1 - 0.46, -0.15, 0.5), (0.1, sy1 - 0.45, 0.1, 0.9)):
        mb.add_box((cx, cy, f0 + 0.72), (0.22, 0.07, 0.2), R=rot_z(rz), mat=1, fattr=a, template=CBOX)
    # rug, coffee table
    box(mb, -2.1, 0.75, -4.0, -1.85, f0, f0 + 0.012, 2)
    lathe(mb, [(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.5, 0.3), (0.5, 0.36), (0.0, 0.36)], -0.75, -3.25, f0 + 0.012, mat=4, n=40)
    for k in range(3):
        box(mb, -0.95, -0.65, -3.35 + k * 0.004, -3.13 - k * 0.004, f0 + 0.372 + k * 0.03, f0 + 0.372 + (k + 1) * 0.03, 9, rng=rng)
    lathe(mb, [(0.0, 0.0), (0.05, 0.0), (0.09, 0.05), (0.1, 0.07)], -0.45, -3.2, f0 + 0.372, mat=10)
    # TV + oak media console on the south wall (plan: TV)
    box(mb, PX(930), PX(1010), YI0, YI0 + 0.42, f0, f0 + 0.48, 3, rng=rng)
    box(mb, (PX(930) + PX(1010)) / 2 - 0.72, (PX(930) + PX(1010)) / 2 + 0.72, YI0 + 0.02, YI0 + 0.05, f0 + 1.0, f0 + 1.82, 5)
    lathe(mb, [(0.0, 0.0), (0.06, 0.0), (0.09, 0.12), (0.05, 0.3), (0.04, 0.36)], PX(1000) - 0.1, YI0 + 0.22, f0 + 0.48, mat=10)
    # fireplace (cheminée) on the séjour west wall
    fy0, fy1 = -4.15, -2.6
    fx1 = XW + 0.58
    op0, op1 = -3.85, -2.9
    box(mb, XW, fx1, fy0, op0, f0, f0 + 1.12, 6, rng=rng)
    box(mb, XW, fx1, op1, fy1, f0, f0 + 1.12, 6, rng=rng)
    box(mb, XW, XW + 0.08, op0, op1, f0, f0 + 1.12, 7)
    box(mb, XW, fx1 - 0.08, op0, op1, f0 + 0.95, f0 + 1.12, 7)
    box(mb, XW - 0.01, fx1 + 0.06, fy0 - 0.04, fy1 + 0.04, f0 + 1.12, f0 + 1.38, 3, rng=rng)   # oak mantel beam
    box(mb, XW, fx1 - 0.12, fy0 + 0.1, fy1 - 0.1, f0 + 1.38, ZJ, 8)                       # plastered hood
    box(mb, fx1, fx1 + 0.45, fy0 + 0.05, fy1 - 0.05, f0, f0 + 0.05, 6, rng=rng)            # hearth
    for k, (ly, lz) in enumerate(((-3.55, 0.08), (-3.2, 0.08), (-3.38, 0.2))):
        mb.add_box((XW + 0.3, ly, f0 + lz), (0.22, 0.07, 0.07), R=rot_z(math.pi / 2 + 0.15 * (k - 1)) @ np.eye(3),
                   mat=11, fattr=rng.random(), template=CBOX)
    for (yy) in (-3.6, -3.1):
        box(mb, XW + 0.12, XW + 0.5, yy - 0.015, yy + 0.015, f0, f0 + 0.03, 12)
    # candle sticks / jug on the mantel
    lathe(mb, [(0.0, 0.0), (0.05, 0.0), (0.07, 0.1), (0.05, 0.18), (0.06, 0.24)], XW + 0.3, fy1 + 0.25, f0 + 1.38, mat=10)
    # built-in oak bookshelves between the fireplace and the corridor
    bx0, bx1, by0, by1 = XW, XW + 0.3, -2.4, -0.05
    box(mb, bx0, bx1, by0 - 0.03, by0, f0, f0 + 2.4, 3, rng=rng)
    box(mb, bx0, bx1, by1, by1 + 0.03, f0, f0 + 2.4, 3, rng=rng)
    shelves = [f0, f0 + 0.42, f0 + 0.8, f0 + 1.18, f0 + 1.56, f0 + 1.94, f0 + 2.37]
    for zz in shelves:
        box(mb, bx0, bx1, by0, by1, zz, zz + 0.03, 3, rng=rng)
    for zz in shelves[:-1]:
        y = by0 + 0.02
        while y < by1 - 0.05:
            r = rng.random()
            if r < 0.08:
                y += rng.uniform(0.08, 0.2)
                continue
            if r < 0.15:   # horizontal stack
                n = rng.integers(3, 7)
                ww = rng.uniform(0.18, 0.26)
                for k in range(n):
                    box(mb, bx0 + 0.04, bx0 + 0.27, y, y + ww, zz + 0.03 + k * 0.035, zz + 0.03 + (k + 1) * 0.035 - 0.002, 9, rng=rng)
                y += ww + 0.02
                continue
            t = rng.uniform(0.018, 0.05)
            h = rng.uniform(0.2, 0.33)
            d = rng.uniform(0.15, 0.24)
            box(mb, bx0 + 0.27 - d, bx0 + 0.27, y, y + t, zz + 0.03, zz + 0.03 + h, 9, rng=rng)
            y += t + 0.002
    # floor lamp by the sofa (linen drum shade, glowing)
    lx, ly = -1.92, -1.2
    for a in range(3):
        ang = a * 2 * math.pi / 3
        mb.add_box((lx + 0.12 * math.cos(ang), ly + 0.12 * math.sin(ang), f0 + 0.75), (0.01, 0.01, 0.78),
                   R=np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) , mat=12)
    lathe(mb, [(0.22, f0 + 1.45), (0.22, f0 + 1.75)], lx, ly, 0, mat=13, n=32)
    return mb.build('int_living', [M.get('linen'), M.get('cushion'), M.get('rug'), M.get('oak_y'), M.get('worktop'),
                                   M.get('screen'), M.get('dressed'), M.get('soot'), M.get('plaster'), M.get('books'),
                                   M.get('ceramic_white'), M.get('bark'), M.get('black_metal'), M.get('shade_glow')], col)


def plants(col, rng):
    # olive tree in a large terracotta pot, in the sunny corner by the glass bay
    veg.TREE_PARAMS['olive'] = dict(trunk=0.9, r0=0.06, levels=3, nchild=[5, 5, 6], cang=[(25, 50), (30, 55), (30, 60)],
                                    blen=[0.9, 0.75, 0.45, 0.22], wob=[0.25, 0.25, 0.3, 0.3], up=[0.0, 0.1, 0.08, 0.1],
                                    crad=[0.5, 0.55, 0.6], start=[0.7, 0.2, 0.2], leaf=(0.07, 0.016), clusters=10.0,
                                    per_cluster=14, cl_r=0.07, seg=[0.15, 0.15, 0.1, 0.08], mat='leaf_olive')
    w, l, _ = veg.make_tree('olivier', 4, 'olive', collection=col)
    px, py = XE - 0.4, YI1 - 0.42
    veg.place((w, l), (px, py, FFL0 + 0.5), 0.3, 1.0)
    mb = MeshBuilder()
    lathe(mb, [(0.0, 0.0), (0.2, 0.0), (0.27, 0.45), (0.3, 0.5), (0.28, 0.5), (0.0, 0.46)], px, py, FFL0, mat=0)
    mb.build('olive_pot', [M.get('ceramic_earth')], col)


def lights(col):
    def point(name, loc, energy, radius=0.04, color=(1.0, 0.68, 0.40)):
        ld = bpy.data.lights.new(name, 'POINT')
        ld.energy = energy
        ld.shadow_soft_size = radius
        ld.color = color
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        col.objects.link(ob)

    def portal(name, loc, w, h, rot):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = w, h
        try:
            ld.cycles.is_portal = True
        except Exception:
            ld.is_portal = True
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        ob.rotation_euler = rot
        col.objects.link(ob)

    tx = (PX(1165) + PX(1207)) / 2
    for (px, py, zb) in ((tx, PYg(455) + 0.6, FFL0 + 1.95), (tx, PYg(377) - 0.6, FFL0 + 1.95),
                         (2.45, 2.2, FFL0 + 1.85), (3.05, 2.2, FFL0 + 1.85)):
        point('pend_%.1f_%.1f' % (px, py), (px, py, zb + 0.08), 22.0)
    point('floorlamp', (-1.92, -1.2, FFL0 + 1.6), 14.0, 0.1)
    # portals on the séjour openings (garden side)
    for (u, z, w, h) in ((PX(1170), FFL0, 2.40, 2.45), (PX(1045), 1.22, 1.10, 1.13)):
        portal('portal_%.1f' % u, (u, YI1 - 0.01, z + h / 2), w, h, (-math.pi / 2, 0, 0))


def build(rng):
    col = coll('interior')
    structure(col, rng)
    stairs(col, rng)
    kitchen(col, rng)
    dining(col, rng)
    living(col, rng)
    plants(col, rng)
    lights(col)
    return col
