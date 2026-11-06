"""The house, modelled from the hand-drawn plan (ground floor + first floor).

Plan pixels -> metres: the outer rectangle (538..1432 px wide, 338..674 px deep)
is mapped to 25.0 m x 9.4 m.  +Y = top edge of the plan = garden side,
+X = right edge of the plan (garage end).
"""
import math
import numpy as np
import bpy
from lib import MeshBuilder, BOX, CBOX, mesh_np, coll
import materials as M

S = 25.0 / 894.0


def PX(px):
    return (px - 985.0) * S


def PYg(py):            # ground-floor plan
    return (506.0 - py) * S


def PYu(py):            # first-floor plan (slightly different sketch scale)
    return (851.0 - py) * (9.4 / 302.0)


HL, HD = 12.5, 4.7       # half length / half depth (outer faces)
T = 0.50                 # stone wall thickness
Z0 = -0.45               # wall foot (below grade)
FFL0, FFL1 = 0.15, 3.15  # finished floor levels
ZE = 6.05                # top of long walls (eaves)
PITCH = math.radians(47.0)
TANA = math.tan(PITCH)
ZR = ZE + HD * TANA      # roof underside apex at the gable
OVH = 0.38               # eave overhang
RAKE = 0.22              # gable overhang
DT = 0.22                # vertical thickness of the roof deck

FACADES = {
    'N': dict(O=(0, HD, 0), T=(1, 0, 0), N=(0, 1, 0), u=(-HL, HL), gable=False),
    'S': dict(O=(0, -HD, 0), T=(1, 0, 0), N=(0, -1, 0), u=(-HL, HL), gable=False),
    'W': dict(O=(-HL, 0, 0), T=(0, 1, 0), N=(-1, 0, 0), u=(-HD, HD), gable=True),
    'E': dict(O=(HL, 0, 0), T=(0, 1, 0), N=(1, 0, 0), u=(-HD, HD), gable=True),
}

# (u-centre, sill z, width, height, kind) -- positions read from the plan
OPENINGS = {
    'N': [  # garden side (top edge of the plan)
        (PX(648), 1.00, 1.10, 1.40, 'win'),    # RDC chambre
        (PX(822), 1.55, 0.60, 0.85, 'small'),  # RDC salle de bain
        (PX(938), 1.72, 0.45, 0.60, 'wc'),     # RDC WC
        (PX(1045), 1.22, 1.10, 1.13, 'win'),   # cuisine (above the L worktop)
        (PX(1170), FFL0, 2.40, 2.45, 'bay'),   # séjour/table: opening drawn on the plan
        (PX(630), 4.00, 1.00, 1.30, 'win'),    # étage chambre 1
        (PX(808), 4.00, 1.00, 1.30, 'win'),    # étage chambre 2
        (PX(987), 3.70, 2.00, 1.65, 'mod'),    # étage salle de jeux
        (PX(1170), 3.95, 2.40, 1.40, 'mod'),   # étage palier / escalier
    ],
    'W': [  # left gable
        (PYg(404), 1.00, 1.00, 1.35, 'win'),   # RDC chambre
        (PYg(575), 1.00, 1.00, 1.35, 'win'),   # RDC bureau
        (PYu(767), 4.00, 1.00, 1.30, 'win'),   # chambre 1
        (PYu(936), 4.00, 1.00, 1.30, 'win'),   # chambre 3
    ],
    'E': [  # right gable: garage
        (PYg(592), 0.0, 2.80, 2.60, 'garage'),
    ],
    'S': [  # entrance side (bottom edge of the plan)
        (PX(1070), FFL0, 1.10, 2.25, 'door'),  # entrée "E"
        (PX(800), 1.40, 0.80, 1.00, 'small'),  # buanderie
        (PX(630), 4.00, 1.00, 1.30, 'win'),    # chambre 3
        (PX(811), 4.45, 0.60, 0.85, 'small'),  # SDB étage
        (PX(945), 4.65, 0.45, 0.60, 'wc'),     # WC étage
        (PX(1168), 3.90, 1.00, 1.30, 'win'),   # escalier
    ],
}


def fpt(f, u, z, d):
    O, Tv, Nv = (np.array(f[k], float) for k in ('O', 'T', 'N'))
    return O + Tv * u + np.array([0, 0, 1.0]) * z - Nv * d


def _orient(f, quad_pts):
    """Return True if quad (p0..p3) must be reversed to face along +normal."""
    p = np.array(quad_pts)
    n = np.cross(p[1] - p[0], p[2] - p[1])
    return np.dot(n, np.array(f['N'], float)) < 0


# ----------------------------------------------------------------------------
def build_walls(col):
    stone, plaster = M.get('stone'), M.get('plaster')
    mb = MeshBuilder()
    for key, f in FACADES.items():
        u0, u1 = f['u']
        holes = [(u - w / 2, u + w / 2, z, z + h) for (u, z, w, h, k) in OPENINGS[key]]
        U = sorted(set([u0, u1] + [h[0] for h in holes] + [h[1] for h in holes]))
        Z = sorted(set([Z0, ZE] + [h[2] for h in holes] + [h[3] for h in holes]))
        for d, mat, flip in ((0.0, 0, False), (T, 1, True)):
            for i in range(len(U) - 1):
                for j in range(len(Z) - 1):
                    uc, zc = (U[i] + U[i + 1]) / 2, (Z[j] + Z[j + 1]) / 2
                    if any(a < uc < b and c < zc < e for (a, b, c, e) in holes):
                        continue
                    q = [fpt(f, U[i], Z[j], d), fpt(f, U[i + 1], Z[j], d),
                         fpt(f, U[i + 1], Z[j + 1], d), fpt(f, U[i], Z[j + 1], d)]
                    rev = _orient(f, q) != flip
                    mb.add(q, [[3, 2, 1, 0]] if rev else [[0, 1, 2, 3]], mat)
            if f['gable']:
                tri = [fpt(f, u0, ZE, d), fpt(f, u1, ZE, d), fpt(f, 0.0, ZR, d)]
                pts = np.array(tri)
                n = np.cross(pts[1] - pts[0], pts[2] - pts[1])
                rev = (np.dot(n, np.array(f['N'], float)) < 0) != flip
                mb.add(tri, [[2, 1, 0]] if rev else [[0, 1, 2]], mat)
        # reveals
        for (a, b, c, e) in holes:
            ring = [(a, c), (b, c), (b, e), (a, e)]
            for k in range(4):
                (ua, za), (ub, zb) = ring[k], ring[(k + 1) % 4]
                q = [fpt(f, ua, za, 0), fpt(f, ub, zb, 0), fpt(f, ub, zb, T), fpt(f, ua, za, T)]
                # reveal normal should point towards the hole centre
                p = np.array(q)
                n = np.cross(p[1] - p[0], p[2] - p[1])
                cen = fpt(f, (a + b) / 2, (c + e) / 2, T / 2)
                face = [0, 1, 2, 3] if np.dot(n, cen - p.mean(0)) > 0 else [3, 2, 1, 0]
                mb.add(q, [face], 0)
    # wall tops of the long walls (hidden under roof, closes the volume)
    for sgn in (1, -1):
        y0, y1 = sgn * HD, sgn * (HD - T)
        mb.add([(-HL, y0, ZE), (HL, y0, ZE), (HL, y1, ZE), (-HL, y1, ZE)], [[0, 1, 2, 3]], 1)
    return mb.build('walls', [stone, plaster], col)


# ----------------------------------------------------------------------------
def build_stonework(col, rng):
    """Quoins, lintels, sills, jambs, eaves cornice, plinth."""
    dressed = M.get('dressed')
    oak = M.get('oak_x')
    mb = MeshBuilder()
    mbo = MeshBuilder()

    def fbox(f, ua, ub, za, zb, da, db, target=mb, attr=None):
        """Axis-aligned (in facade frame) box from u, z, depth ranges."""
        Tv, Nv = np.array(f['T'], float), np.array(f['N'], float)
        c = fpt(f, (ua + ub) / 2, (za + zb) / 2, (da + db) / 2)
        hx = Tv * (ub - ua) / 2
        hz = np.array([0, 0, (zb - za) / 2])
        hn = Nv * (db - da) / 2
        R = np.stack([hx, hn, hz], 1)  # columns
        v = BOX[0] @ R.T + c
        # fix winding: BOX faces assume right-handed (x,y,z); check determinant
        F = BOX[1] if np.linalg.det(R) > 0 else [ff[::-1] for ff in BOX[1]]
        target.add(v, F, 0, rng.random() if attr is None else attr)

    def jambs(f, a, b, c, e, depth=0.012):
        z = c
        alt = rng.integers(0, 2)
        while z < e - 0.05:
            hgt = min(rng.uniform(0.26, 0.36), e - z)
            if e - (z + hgt) < 0.12:
                hgt = e - z
            for side, (x0, sgnw) in enumerate(((a, -1), (b, 1))):
                wlong = 0.30 if (alt + side) % 2 == 0 else 0.19
                ua, ub = (x0 - wlong, x0) if sgnw < 0 else (x0, x0 + wlong)
                fbox(f, ua, ub, z + 0.004, z + hgt - 0.004, -depth, 0.08)
            alt += 1
            z += hgt

    for key, f in FACADES.items():
        for (u, z, w, h, kind) in OPENINGS[key]:
            a, b, c, e = u - w / 2, u + w / 2, z, z + h
            if kind in ('win', 'small', 'door', 'wc'):
                ext = 0.20 if kind != 'wc' else 0.12
                fbox(f, a - ext, b + ext, e, e + (0.30 if kind != 'wc' else 0.18), -0.015, 0.35)  # lintel
                if kind != 'door':
                    fbox(f, a - 0.07, b + 0.07, c - 0.09, c, -0.06, 0.30)  # sill
                else:
                    fbox(f, a - 0.05, b + 0.05, c - 0.15, c, -0.25, 0.30)  # threshold
                jambs(f, a, b, c, e, 0.015)
            elif kind == 'bay':
                fbox(f, a - 0.35, b + 0.35, e, e + 0.30, -0.03, 0.42, target=mbo)  # oak beam lintel
                fbox(f, a - 0.04, b + 0.04, c - 0.12, c, -0.18, 0.30)  # threshold slab
                jambs(f, a, b, c, e, 0.012)
            elif kind == 'mod':
                fbox(f, a - 0.18, b + 0.18, e, e + 0.22, -0.012, 0.10)
                fbox(f, a - 0.18, b + 0.18, c - 0.10, c, -0.04, 0.30)
                fbox(f, a - 0.18, a, c, e, -0.012, 0.10)
                fbox(f, b, b + 0.18, c, e, -0.012, 0.10)
            elif kind == 'garage':
                fbox(f, a - 0.40, b + 0.40, e, e + 0.36, -0.04, 0.45, target=mbo)
                jambs(f, a, b, c + 0.02, e, 0.015)

    # quoins on the 4 vertical corners
    for sx in (-1, 1):
        for sy in (-1, 1):
            z = -0.1
            alt = 0 if sx * sy > 0 else 1
            while z < ZE - 0.1:
                hgt = min(rng.uniform(0.27, 0.36), ZE - z)
                lx, ly = (0.58, 0.30) if alt % 2 == 0 else (0.30, 0.58)
                lx += rng.uniform(-0.05, 0.05)
                ly += rng.uniform(-0.05, 0.05)
                x0, x1 = sorted((sx * (HL + 0.003), sx * (HL - lx)))
                y0, y1 = sorted((sy * (HD + 0.003), sy * (HD - ly)))
                mb.add_box(((x0 + x1) / 2, (y0 + y1) / 2, z + hgt / 2),
                           ((x1 - x0) / 2, (y1 - y0) / 2, hgt / 2 - 0.003), fattr=rng.random())
                z += hgt
                alt += 1
    # eaves cornice on the long walls (two courses)
    for sgn in (1, -1):
        f = FACADES['N' if sgn > 0 else 'S']
        x = -HL - 0.10
        while x < HL + 0.10:
            L = rng.uniform(0.5, 0.9)
            x1 = min(x + L, HL + 0.10)
            fbox(f, x, x1 - 0.006, ZE - 0.16, ZE + 0.02, -0.10, 0.2)
            x = x1
        x = -HL - 0.02
        while x < HL + 0.02:
            L = rng.uniform(0.5, 0.9)
            x1 = min(x + L, HL + 0.02)
            fbox(f, x, x1 - 0.006, ZE - 0.30, ZE - 0.16, -0.05, 0.2)
            x = x1
    a = mb.build('stonework', [dressed], col)
    b = mbo.build('oak_beams', [oak], col)
    return a, b


# ----------------------------------------------------------------------------
def build_joinery(col, rng):
    paint, alu, glass, oakv, oakx = (M.get('frame_paint'), M.get('anthracite'), M.get('glass'),
                                     M.get('oak_v'), M.get('oak_x'))
    mb = MeshBuilder()   # mats: 0 paint 1 alu 2 glass 3 oak(v) 4 oak(x) 5 black metal
    blackm = M.get('black_metal')

    def fbox(f, ua, ub, za, zb, da, db, mat, attr=None):
        Tv, Nv = np.array(f['T'], float), np.array(f['N'], float)
        c = fpt(f, (ua + ub) / 2, (za + zb) / 2, (da + db) / 2)
        R = np.stack([Tv * (ub - ua) / 2, Nv * (db - da) / 2, np.array([0, 0, (zb - za) / 2])], 1)
        v = BOX[0] @ R.T + c
        F = BOX[1] if np.linalg.det(R) > 0 else [ff[::-1] for ff in BOX[1]]
        mb.add(v, F, mat, rng.random() if attr is None else attr)

    def glass_pane(f, ua, ub, za, zb, d):
        q = [fpt(f, ua, za, d), fpt(f, ub, za, d), fpt(f, ub, zb, d), fpt(f, ua, zb, d)]
        mb.add(q, [[0, 1, 2, 3]], 2)

    def casement(f, a, b, c, e, leaves, panes, d=0.16, fw=0.06, mat=0):
        dep = 0.06
        fbox(f, a, b, c, c + fw, d, d + dep, mat)
        fbox(f, a, b, e - fw, e, d, d + dep, mat)
        fbox(f, a, a + fw, c, e, d, d + dep, mat)
        fbox(f, b - fw, b, c, e, d, d + dep, mat)
        lw = (b - a - 2 * fw) / leaves
        for i in range(leaves):
            la, lb = a + fw + i * lw, a + fw + (i + 1) * lw
            sw = 0.045
            fbox(f, la, la + sw, c + fw, e - fw, d - 0.005, d + dep, mat)
            fbox(f, lb - sw, lb, c + fw, e - fw, d - 0.005, d + dep, mat)
            fbox(f, la, lb, c + fw, c + fw + 0.07, d - 0.005, d + dep, mat)
            fbox(f, la, lb, e - fw - sw, e - fw, d - 0.005, d + dep, mat)
            hh = (e - fw - sw - (c + fw + 0.07))
            for k in range(1, panes):
                zz = c + fw + 0.07 + hh * k / panes
                fbox(f, la + sw, lb - sw, zz - 0.012, zz + 0.012, d + 0.005, d + 0.04, mat)
        glass_pane(f, a + fw, b - fw, c + fw, e - fw, d + 0.03)

    def shutters(f, a, b, c, e, n_leaves=2):
        ws = (b - a) / n_leaves
        sides = [(a, -1), (b, 1)] if n_leaves == 2 else [(a, -1)]
        for (x0, sg) in sides:
            nplank = max(2, int(round(ws / 0.13)))
            pw = ws / nplank
            jitter = rng.uniform(-0.01, 0.01)
            for k in range(nplank):
                ua = x0 + sg * (k * pw + 0.0025) + (0 if sg > 0 else -pw + 0.005)
                fbox(f, ua, ua + pw - 0.005, c + 0.01, e - 0.01, -0.055 + jitter, -0.027 + jitter, 3)
            # battens (barres) visible when open
            u_lo, u_hi = (x0 - ws, x0) if sg < 0 else (x0, x0 + ws)
            for zf in (0.13, 0.5, 0.87):
                zc = c + (e - c) * zf
                fbox(f, u_lo + 0.02, u_hi - 0.02, zc - 0.05, zc + 0.05, -0.078 + jitter, -0.055 + jitter, 4)
            # hinge straps
            for zf in (0.13, 0.87):
                zc = c + (e - c) * zf
                fbox(f, u_lo + 0.01, u_hi - 0.01, zc - 0.018, zc + 0.018, -0.083 + jitter, -0.078 + jitter, 5)

    def plank_door(f, a, b, c, e, d=0.20, nplank=None):
        w = b - a
        nplank = nplank or max(3, int(round(w / 0.14)))
        pw = w / nplank
        for k in range(nplank):
            fbox(f, a + k * pw + 0.002, a + (k + 1) * pw - 0.002, c, e - 0.005, d, d + 0.05, 3)

    for key, f in FACADES.items():
        for (u, z, w, h, kind) in OPENINGS[key]:
            a, b, c, e = u - w / 2, u + w / 2, z, z + h
            if kind == 'win':
                casement(f, a, b, c, e, 2, 3)
                shutters(f, a, b, c, e, 2)
            elif kind == 'small':
                casement(f, a, b, c, e, 1, 2)
                shutters(f, a, b, c, e, 1)
            elif kind == 'wc':
                casement(f, a, b, c, e, 1, 1, fw=0.05)
            elif kind == 'bay':
                d = 0.20
                fw = 0.055
                fbox(f, a, b, c, c + fw, d, d + 0.12, 1)
                fbox(f, a, b, e - fw, e, d, d + 0.12, 1)
                fbox(f, a, a + fw, c, e, d, d + 0.12, 1)
                fbox(f, b - fw, b, c, e, d, d + 0.12, 1)
                n = 3
                pw = (b - a - 2 * fw) / n
                for i in range(1, n):
                    x = a + fw + i * pw
                    fbox(f, x - 0.03, x + 0.03, c + fw, e - fw, d + (0.0 if i % 2 else 0.05), d + (0.06 if i % 2 else 0.11), 1)
                glass_pane(f, a + fw, b - fw, c + fw, e - fw, d + 0.04)
            elif kind == 'mod':
                d = 0.20
                fw = 0.05
                fbox(f, a, b, c, c + fw, d, d + 0.08, 1)
                fbox(f, a, b, e - fw, e, d, d + 0.08, 1)
                fbox(f, a, a + fw, c, e, d, d + 0.08, 1)
                fbox(f, b - fw, b, c, e, d, d + 0.08, 1)
                x = (a + b) / 2
                fbox(f, x - 0.025, x + 0.025, c + fw, e - fw, d, d + 0.08, 1)
                glass_pane(f, a + fw, b - fw, c + fw, e - fw, d + 0.04)
            elif kind == 'door':
                plank_door(f, a, b, c, e, 0.22)
                fbox(f, b - 0.20, b - 0.17, c + 1.0, c + 1.08, 0.17, 0.22, 5)
            elif kind == 'garage':
                plank_door(f, a, (a + b) / 2 - 0.005, c, e, 0.18, 8)
                plank_door(f, (a + b) / 2 + 0.005, b, c, e, 0.18, 8)
    return mb.build('joinery', [paint, alu, glass, oakv, oakx, blackm], col)


# ----------------------------------------------------------------------------
def build_roof(col, rng):
    lauze = M.get('lauze')
    ca, sa = math.cos(PITCH), math.sin(PITCH)
    Ye = HD + OVH
    zeave_top = ZE - OVH * TANA + DT
    Ls = Ye / ca
    X0, X1 = -(HL + RAKE), HL + RAKE
    Vs, Fs, As = [], [], []
    nverts = 0
    for sgn in (1, -1):
        E0 = np.array([0.0, sgn * Ye, zeave_top])
        Uv = np.array([0.0, -sgn * ca, sa])
        Nv = np.array([0.0, sgn * sa, ca])
        Xv = np.array([1.0, 0, 0])
        s = -0.03
        row = 0
        while s < Ls - 0.02:
            fr = max(0.0, s / Ls)
            e = 0.205 - 0.095 * fr
            L = e * 2.7
            s_top = Ls + (0.16 if sgn > 0 else 0.0)
            L = min(L, s_top - s)
            if L < 0.08:
                break
            h0 = 0.045 * 2.7 if row > 0 else 0.03
            x = X0 - rng.uniform(0, 0.2)
            while x < X1:
                w = rng.uniform(0.22, 0.46) * (1.25 - 0.45 * fr)
                x1 = min(x + w, X1 + rng.uniform(0.0, 0.03))
                if X1 - x1 < 0.1:
                    x1 = X1 + rng.uniform(0.0, 0.03)
                wd = x1 - x - rng.uniform(0.004, 0.012)
                th = rng.uniform(0.026, 0.05)
                cut = min(0.08, 0.3 * wd) * rng.uniform(0.0, 1.3)
                cut2 = cut * rng.uniform(0.3, 1.6)
                ds = rng.uniform(-0.035, 0.015)
                Lk = L + rng.uniform(-0.02, 0.0)
                cutb = cut * rng.uniform(0.0, 1.2)
                poly = [(-wd / 2 + cutb, 0), (wd / 2 - cut, rng.uniform(-0.01, 0.01)), (wd / 2, cut2), (wd / 2, Lk), (-wd / 2, Lk), (-wd / 2, cutb * rng.uniform(0.4, 1.5))]
                yaw = rng.normal(0, 0.03)
                cy, sy_ = math.cos(yaw), math.sin(yaw)
                tc = x + (x1 - x) / 2
                hj = rng.uniform(-0.004, 0.006)
                tilt = rng.normal(0, 0.008)
                vb, vt = [], []
                for (pt, ps) in poly:
                    rt = pt * cy - (ps - Lk / 2) * sy_
                    rs = pt * sy_ + (ps - Lk / 2) * cy + Lk / 2
                    hu = h0 * (1 - ps / Lk) + hj + tilt * pt
                    base = E0 + Xv * (tc + rt) + Uv * (s + ds + rs)
                    vb.append(base + Nv * hu)
                    vt.append(base + Nv * (hu + th))
                V = np.array(vb + vt)
                F = [[5, 4, 3, 2, 1, 0], [6, 7, 8, 9, 10, 11]]
                for k in range(6):
                    k2 = (k + 1) % 6
                    F.append([k, k2, 6 + k2, 6 + k])
                Vs.append(V)
                for ff in F:
                    Fs.append([i + nverts for i in ff])
                    As.append(rng.random())
                nverts += 12
                x = x1
            s += e
            row += 1
    roof = mesh_np('roof_lauzes', np.concatenate(Vs), Fs, mats=[lauze], collection=col,
                   face_attrs={'rnd': np.array(As)})
    # deck (timber) under the lauzes, visible at eaves / rakes
    oak = M.get('dark_wood')
    zb_e = ZE - OVH * TANA
    Yd = Ye - 0.12
    zb_d = ZE - (Yd - HD) * TANA
    prof = [(-Yd, zb_d), (-Yd, zb_d + DT), (0, ZR + DT), (Yd, zb_d + DT), (Yd, zb_d), (0, ZR)]
    V = [(X0 + 0.12, y, z) for (y, z) in prof] + [(X1 - 0.12, y, z) for (y, z) in prof]
    F = [[0, 1, 2, 3, 4, 5][::-1], [6, 7, 8, 9, 10, 11]]
    for k in range(6):
        k2 = (k + 1) % 6
        F.append([k, k2, 6 + k2, 6 + k])
    mesh_np('roof_deck', np.array(V), F, mats=[oak], collection=col)
    return roof


def build_chimney(col, rng):
    stone, dressed, lauze = M.get('stone'), M.get('dressed'), M.get('lauze')
    cx, cy = PX(899), -0.95          # fireplace is on the séjour west wall; flue rises near ridge
    hx, hy = 0.48, 0.38
    ztop = ZR + DT + 1.15
    mb = MeshBuilder()
    mb.add_box((cx, cy, (ZE + ztop) / 2), (hx, hy, (ztop - ZE) / 2), mat=0)
    mb.add_box((cx, cy, ztop + 0.05), (hx + 0.05, hy + 0.05, 0.05), mat=1, fattr=rng.random())
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add_box((cx + sx * (hx - 0.1), cy + sy * (hy - 0.1), ztop + 0.25), (0.09, 0.09, 0.15), mat=1, fattr=rng.random())
    mb.add_box((cx, cy, ztop + 0.44), (hx + 0.16, hy + 0.16, 0.045), mat=2, fattr=rng.random())
    return mb.build('chimney', [stone, dressed, lauze], col)


# ----------------------------------------------------------------------------
def build_interior(col, rng):
    plaster, floor, fabric, dwood, lamp, oakv = (M.get('plaster'), M.get('floor'), M.get('fabric'),
                                                 M.get('dark_wood'), M.get('lamp'), M.get('oak_v'))
    mb = MeshBuilder()  # 0 plaster 1 floor 2 fabric 3 dark wood 4 lamp 5 oak
    xi0, xi1, yi0, yi1 = -HL + T, HL - T, -HD + T, HD - T
    # slabs
    mb.add_box((0, 0, FFL0 - 0.08), ((xi1 - xi0) / 2 + 0.01, (yi1 - yi0) / 2 + 0.01, 0.08), mat=1)
    mb.add_box((0, 0, FFL1 - 0.15), ((xi1 - xi0) / 2 + 0.01, (yi1 - yi0) / 2 + 0.01, 0.15), mat=0)
    mb.add_box((0, 0, FFL1 + 0.01), ((xi1 - xi0) / 2 + 0.01, (yi1 - yi0) / 2 + 0.01, 0.01), mat=1)
    mb.add_box((0, 0, ZE - 0.2), ((xi1 - xi0) / 2 + 0.01, (yi1 - yi0) / 2 + 0.01, 0.06), mat=0)

    def wall_x(x, y0, y1, z0, z1):
        mb.add_box((x, (y0 + y1) / 2, (z0 + z1) / 2), (0.05, abs(y1 - y0) / 2, (z1 - z0) / 2), mat=0)

    def wall_y(y, x0, x1, z0, z1):
        mb.add_box(((x0 + x1) / 2, y, (z0 + z1) / 2), (abs(x1 - x0) / 2, 0.05, (z1 - z0) / 2), mat=0)

    g0, g1 = FFL0, FFL1 - 0.3
    u0, u1 = FFL1, ZE - 0.26
    # ground floor partitions (from the plan)
    wall_x(PX(757), yi1, PYg(470), g0, g1)          # chambre | SDB
    wall_y(PYg(470), xi0, PX(897), g0, g1)          # chambres | bureau / couloir
    wall_x(PX(897), yi1, PYg(465), g0, g1)          # SDB | WC
    wall_x(PX(990), yi1, PYg(465), g0, g1)          # WC | cuisine
    wall_y(PYg(465), PX(897), PX(990), g0, g1)
    wall_x(PX(897), PYg(497), yi0, g0, g1)          # buanderie | séjour
    wall_x(PX(715), PYg(497), yi0, g0, g1)          # bureau | buanderie
    wall_y(PYg(497), PX(715), PX(897), g0, g1)
    wall_x(PX(1245), yi1, yi0, g0, g1)              # séjour | garage side
    wall_y(PYg(458), PX(1245), xi1, g0, g1)
    wall_y(PYg(517), PX(1245), xi1, g0, g1)
    # first floor partitions
    wall_x(PX(720), yi1, PYu(835), u0, u1)
    wall_x(PX(897), yi1, PYu(835), u0, u1)
    wall_y(PYu(835), xi0, PX(897), u0, u1)
    wall_y(PYu(870), xi0, PX(988), u0, u1)
    wall_x(PX(720), PYu(870), yi0, u0, u1)
    wall_x(PX(902), PYu(870), yi0, u0, u1)
    wall_x(PX(988), PYu(870), yi0, u0, u1)
    wall_x(PX(1077), yi1, yi0, u0, u1)
    wall_x(PX(1260), yi1, yi0, u0, u1)

    # kitchen: L worktop along WC wall and garden wall, island, dining table
    top = FFL0 + 0.9
    mb.add_box(((PX(990) + PX(1035)) / 2, (yi1 + PYg(465)) / 2, FFL0 + 0.45), ((PX(1035) - PX(990)) / 2, (yi1 - PYg(465)) / 2, 0.45), mat=3)
    mb.add_box(((PX(1035) + PX(1098)) / 2, yi1 - 0.31, FFL0 + 0.45), ((PX(1098) - PX(1035)) / 2, 0.31, 0.45), mat=3)
    mb.add_box(((PX(1068) + PX(1105)) / 2, (PYg(400) + PYg(435)) / 2, FFL0 + 0.46), ((PX(1105) - PX(1068)) / 2, (PYg(400) - PYg(435)) / 2, 0.46), mat=5)
    tx0, tx1, ty0, ty1 = PX(1165), PX(1207), PYg(455), PYg(377)
    mb.add_box(((tx0 + tx1) / 2, (ty0 + ty1) / 2, top - 0.15), ((tx1 - tx0) / 2, (ty1 - ty0) / 2, 0.03), mat=5)
    for sx in (0, 1):
        for sy in (0, 1):
            mb.add_box((tx0 + 0.08 + sx * (tx1 - tx0 - 0.16), ty0 + 0.08 + sy * (ty1 - ty0 - 0.16), FFL0 + 0.36),
                       (0.03, 0.03, 0.36), mat=5)
    for side in (-1, 1):
        for k in range(3):
            yy = ty0 + (ty1 - ty0) * (k + 0.5) / 3
            xx = (tx0 + tx1) / 2 + side * ((tx1 - tx0) / 2 + 0.3)
            mb.add_box((xx, yy, FFL0 + 0.45), (0.21, 0.21, 0.02), mat=3)
            mb.add_box((xx + side * 0.2, yy, FFL0 + 0.7), (0.02, 0.21, 0.25), mat=3)
    # pendant lights above table and island
    for yy in (ty0 + 0.5, ty1 - 0.5):
        mb.add_box(((tx0 + tx1) / 2, yy, FFL0 + 1.9), (0.16, 0.16, 0.09), mat=4)
    # sofa (L) and rug in the séjour
    mb.add_box(((PX(905) + PX(1000)) / 2, PYg(575), FFL0 + 0.22), ((PX(1000) - PX(905)) / 2, 0.45, 0.22), mat=2)
    mb.add_box((PX(975), (PYg(575) + PYg(620)) / 2, FFL0 + 0.22), (0.45, (PYg(575) - PYg(620)) / 2, 0.22), mat=2)
    # first floor: play room shelves + bookcase
    mb.add_box((PX(1040), yi1 - 0.2, FFL1 + 0.9), (0.6, 0.18, 0.9), mat=5)
    mb.add_box((PX(940), PYu(800), FFL1 + 0.3), (0.5, 0.4, 0.3), mat=2)
    # beds in the bedrooms (visible as dark shapes)
    mb.add_box((PX(630), PYu(760), FFL1 + 0.25), (0.8, 1.0, 0.25), mat=2)
    mb.add_box((PX(808), PYu(760), FFL1 + 0.25), (0.8, 1.0, 0.25), mat=2)
    mb.add_box((PX(600), PYg(400), FFL0 + 0.25), (1.0, 0.8, 0.25), mat=2)
    return mb.build('interior', [plaster, floor, fabric, dwood, lamp, oakv], col)


def interior_lights(col):
    def area(name, loc, size, energy, color=(1.0, 0.74, 0.48)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size
        ld.energy = energy
        ld.color = color
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        col.objects.link(ob)
        return ob

    def point(name, loc, energy, radius=0.1, color=(1.0, 0.7, 0.42)):
        ld = bpy.data.lights.new(name, 'POINT')
        ld.energy = energy
        ld.shadow_soft_size = radius
        ld.color = color
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        col.objects.link(ob)

    area('L_sejour', (PX(1120), 1.5, FFL1 - 0.35), (3.0, 4.0), 260)
    area('L_cuisine', (PX(1040), 2.8, FFL1 - 0.35), (1.6, 1.6), 120)
    point('L_pend1', (PX(1186), PYg(455) + 0.5, FFL0 + 1.82), 45)
    point('L_pend2', (PX(1186), PYg(377) - 0.5, FFL0 + 1.82), 45)
    area('L_jeux', (PX(987), 2.5, ZE - 0.3), (2.5, 2.5), 140)
    area('L_palier', (PX(1168), 1.5, ZE - 0.3), (2.0, 2.0), 90)
    area('L_ch1', (PX(630), PYu(767), ZE - 0.3), (1.2, 1.2), 40, (1.0, 0.68, 0.4))
    area('L_chRDC', (PX(648), PYg(404), FFL1 - 0.35), (1.2, 1.2), 30, (1.0, 0.68, 0.4))


def build(rng):
    col = coll('house')
    build_walls(col)
    build_stonework(col, rng)
    build_joinery(col, rng)
    build_roof(col, rng)
    build_chimney(col, rng)
    build_interior(col, rng)
    interior_lights(col)
    return col
