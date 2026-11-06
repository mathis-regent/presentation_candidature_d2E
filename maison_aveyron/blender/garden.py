"""Terrace + pergola, dry-stone walls, gravel court & driveway."""
import math
import numpy as np
import bpy
from lib import MeshBuilder, BOX, CBOX, mesh_np, coll, rot_z, rot_axis
import materials as M
import land
from house import PX, HL, HD, OPENINGS

BAY_X = PX(1170)
TERR = (BAY_X - 2.6, BAY_X + 2.6, HD, HD + 4.4)   # x0, x1, y0, y1
TERR_Z = 0.13

# Gravel court in front of the garage gable, wrapping the NE corner; then the drive
COURT = [(8.4, 4.7), (8.4, 12.0), (17.0, 13.0), (23.5, 9.0), (23.0, -9.5), (12.5, -9.5), (12.5, 4.7)]
DRIVE = [(21.5, 7.5), (28.0, 12.0), (38.0, 15.5), (52.0, 16.5), (68.0, 13.5), (86.0, 7.0), (108.0, -2.0), (135.0, -10.0)]
DRIVE_W = 3.4
WALLS = [
    [(-30.0, 31.5), (-12.0, 33.5), (2.0, 32.0), (12.0, 28.5), (18.5, 22.0), (21.0, 16.5)],   # garden edge
]


def _poly_contains(poly, x, y):
    poly = np.asarray(poly)
    inside = np.zeros(np.shape(x), bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1)
        inside ^= cond
    return inside


def _resample(poly, step):
    poly = np.asarray(poly, float)
    out = [poly[0]]
    for a, b in zip(poly[:-1], poly[1:]):
        L = np.linalg.norm(b - a)
        n = max(1, int(L / step))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def _smooth(poly, it=3):
    p = np.asarray(poly, float)
    for _ in range(it):  # Chaikin
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        q.append(p[-1])
        p = np.array(q)
    return p


def dist_to_polyline(poly, x, y):
    poly = np.asarray(poly, float)
    d = np.full(np.shape(x), 1e9)
    for a, b in zip(poly[:-1], poly[1:]):
        ab = b - a
        t = np.clip(((x - a[0]) * ab[0] + (y - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        px, py = a[0] + t * ab[0], a[1] + t * ab[1]
        d = np.minimum(d, np.hypot(x - px, y - py))
    return d


DRIVE_S = None


def drive_line():
    global DRIVE_S
    if DRIVE_S is None:
        DRIVE_S = _smooth(DRIVE, 3)
    return DRIVE_S


# stepping-stone path across the lawn towards the terrace
PATH = [(-22.5, 21.0), (-17.0, 16.8), (-10.0, 12.6), (-4.0, 9.8), (TERR[0] - 1.0, (TERR[2] + TERR[3]) / 2 + 0.6)]
_path_stones = []


def path_stones(rng=None):
    if not _path_stones:
        rng = rng or np.random.default_rng(5)
        line = _resample(_smooth(PATH, 3), 0.05)
        seg = np.linalg.norm(np.diff(line, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)])
        s = 0.4
        while s < cum[-1] - 0.3:
            k = np.searchsorted(cum, s) - 1
            p = line[k]
            t = line[k + 1] - line[k]
            t /= np.linalg.norm(t)
            nrm = np.array([-t[1], t[0]])
            c = p + nrm * rng.normal(0, 0.06)
            r = rng.uniform(0.3, 0.4)
            _path_stones.append((c, r, math.atan2(t[1], t[0]) + rng.normal(0, 0.25), rng.random()))
            s += rng.uniform(0.74, 0.9)
    return _path_stones


def no_grass_mask(x, y):
    """True where grass must not grow (house, terrace, gravel, walls)."""
    m = (np.abs(x) < HL + 0.45) & (np.abs(y) < HD + 0.45)
    m |= (x > TERR[0] - 1.0) & (x < TERR[1] + 0.1) & (y > TERR[2]) & (y < TERR[3] + 0.1)
    m |= _poly_contains(COURT, x, y)
    m |= dist_to_polyline(drive_line(), x, y) < DRIVE_W / 2
    for w in WALLS:
        m |= dist_to_polyline(_smooth(w, 2), x, y) < 0.35
    for (c, r, a, _) in path_stones():
        m |= np.hypot(x - c[0], y - c[1]) < r * 0.95
    return m


def build_path(col, rng):
    V, F, A = [], [], []
    nv = 0
    for (c, r, a, rr) in path_stones():
        n = 9
        ang = np.sort(rng.uniform(0, 2 * math.pi, n))
        rad = r * rng.uniform(0.75, 1.05, n)
        ex, ey = 1.0, rng.uniform(0.65, 0.85)
        pts = np.stack([np.cos(ang) * rad * ex, np.sin(ang) * rad * ey], 1)
        ca, sa = math.cos(a), math.sin(a)
        pts = pts @ np.array([[ca, sa], [-sa, ca]]) + c
        gz = land.height(pts[:, 0], pts[:, 1])
        ztop = gz.max() + 0.025
        top = np.column_stack([pts, np.full(n, ztop)])
        bot = np.column_stack([pts, gz - 0.06])
        V += [top, bot]
        F.append(list(range(nv, nv + n)))
        F.append(list(range(nv + 2 * n - 1, nv + n - 1, -1)))
        for k in range(n):
            k2 = (k + 1) % n
            F.append([nv + k, nv + n + k, nv + n + k2, nv + k2][::-1])
        A += [rr] * (n + 2)
        nv += 2 * n
    return mesh_np('path_stones', np.concatenate(V), F, mats=[M.get('flagstone')], collection=col,
                   face_attrs={'rnd': np.array(A)})


# ----------------------------------------------------------------------------
def build_terrace(col, rng):
    mb = MeshBuilder()
    x0, x1, y0, y1 = TERR
    # base slab (mortar bed) and border
    mb.add_box(((x0 + x1) / 2, (y0 + y1) / 2, TERR_Z / 2 - 0.1), ((x1 - x0) / 2 + 0.05, (y1 - y0) / 2 + 0.05, TERR_Z / 2 + 0.1 - 0.035), mat=1)
    y = y0 + 0.01
    while y < y1 - 0.05:
        rw = min(rng.uniform(0.38, 0.62), y1 - y)
        x = x0 + 0.01 - rng.uniform(0, 0.3)
        while x < x1 - 0.02:
            L = rng.uniform(0.45, 0.95)
            xa, xb = max(x, x0 + 0.01), min(x + L, x1 - 0.01)
            if xb - xa > 0.08:
                mb.add_box(((xa + xb) / 2, y + rw / 2, TERR_Z - 0.03 + rng.uniform(-0.004, 0.004)),
                           ((xb - xa) / 2 - 0.006, rw / 2 - 0.006, 0.03), mat=0, fattr=rng.random(), template=CBOX)
            x += L
        y += rw
    return mb.build('terrace', [M.get('flagstone'), M.get('gravel')], col)


def build_pergola(col, rng):
    oakv, oakx, oaky = M.get('oak_v'), M.get('oak_x'), M.get('oak_y')
    mb = MeshBuilder()  # 0 posts 1 beams-x 2 rafters-y
    x0, x1, y0, y1 = TERR
    px0, px1 = x0 + 0.25, x1 - 0.25
    py = y1 - 0.35
    ztop = 3.05
    for xx in (px0, px1):
        mb.add_box((xx, py, TERR_Z + (ztop - TERR_Z) / 2), (0.085, 0.085, (ztop - TERR_Z) / 2), mat=0, fattr=rng.random())
        mb.add_box((xx, py, TERR_Z + 0.06), (0.13, 0.13, 0.06), mat=0, fattr=rng.random())   # stone/oak foot
        # knee braces
        for sgn in (-1, 1):
            c = np.array([xx + sgn * 0.32, py, ztop - 0.32])
            R = rot_axis((0, 1, 0), sgn * math.radians(45))
            mb.add_box(c, (0.05, 0.04, 0.44), R=R, mat=0, fattr=rng.random())
    mb.add_box(((px0 + px1) / 2, py, ztop + 0.1), ((px1 - px0) / 2 + 0.45, 0.075, 0.1), mat=1, fattr=rng.random())
    mb.add_box(((px0 + px1) / 2, HD + 0.06, ztop + 0.1), ((px1 - px0) / 2 + 0.3, 0.06, 0.1), mat=1, fattr=rng.random())
    n = int((px1 - px0 + 0.6) / 0.55) + 1
    for k in range(n):
        xx = px0 - 0.3 + k * (px1 - px0 + 0.6) / (n - 1)
        mb.add_box((xx, (HD + py + 0.45) / 2, ztop + 0.29), (0.04, (py + 0.45 - HD) / 2, 0.09), mat=2, fattr=rng.random())
    ob = mb.build('pergola', [oakv, oakx, oaky], col)
    # climbing vine: trunk up the left post + foliage over the rafters
    leaves = []
    nl = 9000
    for _ in range(nl):
        u = rng.random()
        if u < 0.82:
            x = rng.uniform(px0 - 0.4, px1 + 0.4)
            y = rng.uniform(HD + 0.3, py + 0.5)
            dens = 0.5 + 0.5 * math.sin(x * 1.3 + 0.7) * math.cos(y * 1.1)
            if rng.random() > 0.35 + 0.65 * (1 - abs(x - px0) / (px1 - px0 + 1)) * (0.6 + 0.4 * dens):
                continue
            z = ztop + 0.36 + rng.normal(0.08, 0.07)
        elif u < 0.93:
            x = rng.uniform(px0 - 0.5, px1 + 0.3)
            y = py + rng.normal(0, 0.12)
            z = ztop + 0.2 - abs(rng.normal(0, 0.45))
        else:
            x = px0 + rng.normal(0, 0.12)
            y = py + rng.normal(0, 0.12)
            z = rng.uniform(1.0, ztop + 0.2)
        leaves.append((x, y, z))
    L = np.array(leaves)
    n = len(L)
    axis = rng.normal(0, 1, (n, 3))
    axis[:, 2] -= 0.3
    axis /= np.linalg.norm(axis, axis=1)[:, None]
    nrm = rng.normal(0, 1, (n, 3))
    nrm[:, 2] += 1.5
    nrm -= axis * np.sum(nrm * axis, 1)[:, None]
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    side = np.cross(axis, nrm)
    s = rng.uniform(0.11, 0.17, (n, 1))
    V = np.stack([L - side * s * 0.45, L + axis * s * 0.5, L + side * s * 0.45, L - axis * s * 0.55], 1).reshape(-1, 3)
    mesh_np('vine', V, np.arange(n * 4).reshape(n, 4), mats=[M.get('vine')], collection=col,
            face_attrs={'rnd': rng.random(n)})
    # vine trunk (twisted)
    pts = []
    for k in range(30):
        t = k / 29
        pts.append((px0 + 0.12 + 0.04 * math.sin(t * 9), py - 0.1 + 0.04 * math.cos(t * 7), TERR_Z + t * (ztop + 0.15 - TERR_Z)))
    _tube('vine_trunk', pts, 0.035, M.get('bark'), col)
    return ob


def _tube(name, pts, r, mat, col, ns=6):
    pts = np.array(pts, float)
    V, F = [], []
    ang = np.linspace(0, 2 * math.pi, ns, endpoint=False)
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t /= np.linalg.norm(t)
        u = np.cross(t, (1, 0, 0))
        u /= np.linalg.norm(u)
        w = np.cross(t, u)
        V.append(p + r * (np.outer(np.cos(ang), u) + np.outer(np.sin(ang), w)))
    for i in range(len(pts) - 1):
        for j in range(ns):
            a, b = i * ns + j, i * ns + (j + 1) % ns
            F.append([a, b, b + ns, a + ns])
    return mesh_np(name, np.concatenate(V), F, mats=[mat], collection=col, smooth=True)


def build_furniture(col, rng):
    mb = MeshBuilder()  # 0 oak 1 terracotta 2 boxwood
    x0, x1, y0, y1 = TERR
    cx, cy = (x0 + x1) / 2 + 0.2, (y0 + y1) / 2 + 0.35
    top = TERR_Z + 0.76
    mb.add_box((cx, cy, top - 0.03), (1.05, 0.48, 0.03), mat=0, fattr=0.3)
    for sx in (-1, 1):
        mb.add_box((cx + sx * 0.85, cy, TERR_Z + 0.36), (0.05, 0.38, 0.36), mat=0, fattr=0.4)
        for sy in (-1, 1):
            pass
    for sy in (-1, 1):
        by = cy + sy * 0.78
        mb.add_box((cx, by, TERR_Z + 0.44), (0.95, 0.17, 0.025), mat=0, fattr=0.5)
        for sx in (-1, 1):
            mb.add_box((cx + sx * 0.78, by, TERR_Z + 0.21), (0.04, 0.14, 0.21), mat=0, fattr=0.6)
    for (xx, yy) in ((BAY_X - 1.75, HD + 0.45), (BAY_X + 1.75, HD + 0.45)):
        mb.add_box((xx, yy, TERR_Z + 0.25), (0.24, 0.24, 0.25), mat=1, fattr=rng.random(), template=CBOX)
    ob = mb.build('terrace_furniture', [M.get('oak_x'), terracotta(), M.get('dark_wood')], col)
    # boxwood balls in the pots
    for (xx, yy) in ((BAY_X - 1.75, HD + 0.45), (BAY_X + 1.75, HD + 0.45)):
        shrub_ball('buis', (xx, yy, TERR_Z + 0.9), 0.42, rng, col)
    # lavender border along the west edge of the terrace (towards the lawn)
    for k in range(6):
        yy = y0 + 0.5 + k * (y1 - y0 - 0.7) / 5 + rng.uniform(-0.1, 0.1)
        xx = x0 - 0.55 + rng.uniform(-0.08, 0.08)
        r = rng.uniform(0.32, 0.42)
        lav = shrub_ball('lavande', (xx, yy, r * 0.55), r, rng, col, n=1800, mat='lavender', leaf=0.09)
        lav.scale = (1.0, 1.0, 0.75)
    return ob


def shrub_ball(name, c, r, rng, col, n=2500, mat='leaf_oak', leaf=0.07):
    c = np.array(c)
    d = rng.normal(0, 1, (n, 3))
    d /= np.linalg.norm(d, axis=1)[:, None]
    P = c + d * r * (0.85 + 0.15 * rng.random((n, 1)))
    nrm = d + rng.normal(0, 0.5, (n, 3))
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    ax = np.cross(nrm, rng.normal(0, 1, (n, 3)))
    ax /= np.linalg.norm(ax, axis=1)[:, None]
    sd = np.cross(ax, nrm)
    V = np.stack([P - sd * leaf * 0.3, P + ax * leaf * 0.5, P + sd * leaf * 0.3, P - ax * leaf * 0.5], 1).reshape(-1, 3)
    return mesh_np(name, V, np.arange(n * 4).reshape(n, 4), mats=[M.get(mat)], collection=col,
                   face_attrs={'rnd': rng.random(n) * 0.6})


_tc = None


def terracotta():
    global _tc
    if _tc is None:
        from lib import new_material, srgb
        m, s = new_material('terracotta')
        P = s.geo('Position')
        col = s.mix(s.noise(P, 8.0, detail=4.0), srgb(170, 96, 62), srgb(140, 80, 54))
        s.out_material(s.principled(base=col, rough=0.85))
        _tc = m
    return _tc


# ----------------------------------------------------------------------------
def _ribbon(name, line, width, mat, col, zoff=0.03, step=0.6, edge_noise=0.25, rng=None):
    line = _resample(line, step)
    t = np.gradient(line, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    ncols = 9
    V = []
    for i, p in enumerate(line):
        for j in range(ncols):
            f = j / (ncols - 1) - 0.5
            w = width * f
            if j in (0, ncols - 1) and rng is not None:
                w += np.sign(f) * rng.uniform(0, edge_noise)
            x, y = p + nrm[i] * w
            V.append((x, y, 0))
    V = np.array(V)
    V[:, 2] = land.height(V[:, 0], V[:, 1]) + zoff
    F = []
    for i in range(len(line) - 1):
        for j in range(ncols - 1):
            a = i * ncols + j
            F.append([a, a + 1, a + ncols + 1, a + ncols])
    return mesh_np(name, V, F, mats=[mat], collection=col, smooth=True)


def build_gravel(col, rng):
    gravel = M.get('gravel')
    # court: triangulate with a fine grid clipped to polygon
    xs = np.arange(8.0, 24.5, 0.5)
    ys = np.arange(-10.0, 13.5, 0.5)
    X, Y = np.meshgrid(xs, ys)
    Vx = np.stack([X.ravel(), Y.ravel()], 1)
    Z = land.height(Vx[:, 0], Vx[:, 1]) + 0.025
    V = np.column_stack([Vx, Z])
    nx = len(xs)
    F = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            cx, cy = xs[i] + 0.25, ys[j] + 0.25
            if _poly_contains(COURT, np.array(cx), np.array(cy)) and not (abs(cx) < HL and abs(cy) < HD):
                a = j * nx + i
                F.append([a, a + 1, a + nx + 1, a + nx])
    mesh_np('court', V, F, mats=[gravel], collection=col, smooth=True)
    _ribbon('drive', drive_line(), DRIVE_W, gravel, col, 0.03, rng=rng)
    # drip-edge gravel strip along the visible walls
    strip = [(-HL - 0.45, HD + 0.45), (TERR[0], HD + 0.45)]
    _ribbon('strip_n', strip, 0.9, gravel, col, 0.02, step=0.5)
    _ribbon('strip_w', [(-HL - 0.45, HD + 0.45), (-HL - 0.45, -HD - 0.45)], 0.9, gravel, col, 0.02, step=0.5)


def build_drystone(col, rng):
    mb = MeshBuilder()
    for w in WALLS:
        line = _resample(_smooth(w, 2), 0.25)
        seg = np.diff(line, axis=0)
        L = np.linalg.norm(seg, axis=1)
        cum = np.concatenate([[0], np.cumsum(L)])
        total = cum[-1]

        def at(s):
            k = min(np.searchsorted(cum, s) - 1, len(L) - 1)
            k = max(k, 0)
            f = (s - cum[k]) / L[k]
            p = line[k] + seg[k] * f
            t = seg[k] / L[k]
            return p, t

        Hw, Tw = 0.78, 0.55
        for side in (-1, 1):
            z = 0.0
            while z < Hw - 0.1:
                hh = rng.uniform(0.07, 0.15)
                s = rng.uniform(0, 0.2)
                while s < total:
                    sl = rng.uniform(0.18, 0.45)
                    p, t = at(min(s + sl / 2, total - 1e-3))
                    nrm = np.array([-t[1], t[0]])
                    batter = (z / Hw) * 0.06
                    dd = rng.uniform(0.12, 0.2)
                    c2 = p + nrm * side * (Tw / 2 - batter - dd / 2 + rng.uniform(-0.015, 0.015))
                    gz = land.height(np.array([p[0]]), np.array([p[1]]))[0]
                    yaw = math.atan2(t[1], t[0]) + rng.normal(0, 0.06)
                    R = rot_z(yaw) @ rot_axis((1, 0, 0), rng.normal(0, 0.04)) @ rot_axis((0, 1, 0), rng.normal(0, 0.05))
                    mb.add_box((c2[0], c2[1], gz - 0.05 + z + hh / 2), (sl / 2 - 0.008, dd / 2, hh / 2 - 0.006),
                               R=R, fattr=rng.random(), template=CBOX)
                    s += sl
                z += hh
        # coping: stones set on edge
        s = 0.0
        while s < total:
            sl = rng.uniform(0.07, 0.16)
            p, t = at(min(s + sl / 2, total - 1e-3))
            gz = land.height(np.array([p[0]]), np.array([p[1]]))[0]
            hh = rng.uniform(0.18, 0.3)
            yaw = math.atan2(t[1], t[0])
            R = rot_z(yaw) @ rot_axis((1, 0, 0), rng.normal(0, 0.05)) @ rot_axis((0, 1, 0), rng.normal(0, 0.12))
            mb.add_box((p[0], p[1], gz - 0.05 + Hw + hh / 2 - 0.04), (sl / 2 - 0.006, Tw / 2 - 0.04, hh / 2),
                       R=R, fattr=rng.random(), template=CBOX)
            s += sl
        # fill core (dark, hidden)
    return mb.build('drystone_walls', [M.get('drystone')], col)


def build(rng):
    col = coll('garden')
    build_terrace(col, rng)
    build_pergola(col, rng)
    build_furniture(col, rng)
    build_gravel(col, rng)
    build_drystone(col, rng)
    build_path(col, rng)
    return col
