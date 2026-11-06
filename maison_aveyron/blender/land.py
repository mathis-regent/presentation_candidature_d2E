"""Terrain: garden platform, gentle slope, valley, rolling hills, Causse plateau."""
import math
import numpy as np
import bpy
from lib import mesh_np, coll, NT, new_material, srgb


class Perlin:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.p = np.concatenate([rng.permutation(256)] * 2)
        a = rng.uniform(0, 2 * np.pi, 256)
        self.g = np.stack([np.cos(a), np.sin(a)], 1)

    def __call__(self, x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        xi = np.floor(x).astype(np.int64)
        yi = np.floor(y).astype(np.int64)
        xf, yf = x - xi, y - yi
        xi &= 255
        yi &= 255

        def g(ix, iy, dx, dy):
            h = self.p[self.p[ix] + iy]
            gg = self.g[h]
            return gg[..., 0] * dx + gg[..., 1] * dy

        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
        x1 = (xi + 1) & 255
        y1 = (yi + 1) & 255
        n00 = g(xi, yi, xf, yf)
        n10 = g(x1, yi, xf - 1, yf)
        n01 = g(xi, y1, xf, yf - 1)
        n11 = g(x1, y1, xf - 1, yf - 1)
        a = n00 + u * (n10 - n00)
        b = n01 + u * (n11 - n01)
        return (a + v * (b - a)) * 1.4


_P = [Perlin(s) for s in range(8)]


def fbm(x, y, octaves=4, seed=0, lac=2.03, gain=0.5):
    tot = np.zeros(np.broadcast(x, y).shape)
    amp, f = 1.0, 1.0
    norm = 0.0
    for o in range(octaves):
        tot += amp * _P[(seed + o) % 8](x * f + 17.3 * o, y * f - 9.1 * o)
        norm += amp
        amp *= gain
        f *= lac
    return tot / norm


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


TH = math.radians(-16.0)          # valley lies towards the east-south-east


def rot_coords(x, y):
    c, s = math.cos(TH), math.sin(TH)
    return x * c + y * s, -x * s + y * c


def height(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    re, rl = rot_coords(x, y)
    re2 = re + 160 * np.sin(rl / 650.0) + 90 * fbm(rl / 800.0, 3.7, 2, seed=1)
    h = -5.0 * sstep(26, 95, re2)                        # gentle garden slope
    h += -125.0 * sstep(75, 560, re2)                    # down into the valley
    h += 205.0 * sstep(700, 1550, re2)                   # far side of the valley
    esc = re2 + 380 * fbm(rl / 2200.0, 0.3, 3, seed=2)
    h += 250.0 * sstep(2350, 2650, esc) * (0.85 + 0.15 * fbm(rl / 900.0, 1.1, 2, seed=3))  # Causse escarpment
    h += 0.16 * np.logaddexp(0, (-rl - 26) / 6.0) * 6.0   # rises behind (south of) the house
    h += 0.07 * np.logaddexp(0, (-re - 34) / 6.0) * 6.0   # rises to the west
    r = np.hypot(x, y)
    h += sstep(14, 70, r) * 0.25 * fbm(x / 26.0, y / 26.0, 3, seed=4)
    h += sstep(60, 500, r) * 9.0 * fbm(x / 160.0, y / 160.0, 4, seed=5)
    h += sstep(700, 2200, r) * 55.0 * fbm(x / 800.0, y / 800.0, 5, seed=6)
    # flatten the garden platform around the house
    de = np.hypot((x + 8.0) / 44.0, (y - 8.0) / 34.0)
    flat = 1.0 - sstep(0.85, 1.25, de)
    h = h * (1 - flat) + flat * 0.06 * fbm(x / 9.0, y / 9.0, 2, seed=7)
    return h


def field_info(x, y):
    """Pasture parcel tone (0..1), hedge proximity (m) for the bocage pattern."""
    a = math.radians(28.0)
    u = x * math.cos(a) + y * math.sin(a) + 25 * fbm(x / 300.0, y / 300.0, 2, seed=3)
    v = -x * math.sin(a) + y * math.cos(a) + 25 * fbm(x / 310.0, y / 290.0, 2, seed=5)
    cw, ch = 150.0, 95.0
    iu, iv = np.floor(u / cw), np.floor(v / ch)
    # parcels shifted per row so they don't form a perfect grid
    u2 = u + (np.sin(iv * 12.9898) * 43758.5453 % 1.0) * cw
    iu = np.floor(u2 / cw)
    tone = (np.sin(iu * 12.9898 + iv * 78.233) * 43758.5453) % 1.0
    du = np.minimum(u2 - iu * cw, (iu + 1) * cw - u2)
    dv = np.minimum(v - iv * ch, (iv + 1) * ch - v)
    return tone, np.minimum(du, dv)


def forest_mask(x, y, h=None):
    if h is None:
        h = height(x, y)
    n = fbm(x / 420.0, y / 420.0, 4, seed=2)
    f = sstep(0.05, 0.25, n)
    re, rl = rot_coords(x, y)
    f = np.maximum(f, sstep(-40, -90, rl) * sstep(-20, -60, re + 0 * rl) * 0.0)
    # woods on the steep valley sides
    steep = sstep(160, 350, re) * (1 - sstep(700, 900, re))
    f = np.maximum(f, steep * sstep(-0.15, 0.15, fbm(x / 260.0, y / 260.0, 3, seed=6)))
    # wooded hill behind the house (south-west)
    f = np.maximum(f, sstep(-35, -70, rl) * sstep(0.0, 0.2, fbm(x / 120.0, y / 120.0, 3, seed=1) + 0.25))
    # plateau: dry grassland with scattered trees
    f *= 1 - 0.75 * sstep(150, 230, h)
    r = np.hypot(x, y)
    f *= sstep(45, 90, r)
    return np.clip(f, 0, 1)


def grid_axis(n, a, b, c0):
    t = np.linspace(-1, 1, 2 * n + 1)
    return c0 + a * np.sinh(b * t)


def build_terrain(rng, n=330):
    col = coll('land')
    xs = grid_axis(n, 25.6, 6.84, 0.0)
    ys = grid_axis(n, 25.6, 6.84, 0.0)
    X, Y = np.meshgrid(xs, ys)
    Z = height(X, Y)
    nx, ny = len(xs), len(ys)
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(nx * ny).reshape(ny, nx)
    F = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    tone, hd = field_info(X.ravel(), Y.ravel())
    fm = forest_mask(X.ravel(), Y.ravel(), Z.ravel())
    ob = mesh_np('terrain', V, F, mats=[terrain_material()], collection=col, smooth=True,
                 point_attrs={'forest': fm, 'tone': tone, 'hedge': hd})
    return ob


def terrain_material():
    m, s = new_material('terrain')
    P = s.geo('Position')
    N = s.geo('Normal')
    z = s.sep(P)[2]
    slope = s.m('SUBTRACT', 1.0, s.sep(N)[2])
    forest = s.attr('forest')
    tone = s.attr('tone')
    hedge = s.attr('hedge')
    dist = s.vm('LENGTH', s.vm('MULTIPLY', P, (1.0, 1.0, 0.0)))
    # pasture tones: fresh greens, a few hay / ochre parcels
    past = s.ramp(tone, [(0.0, srgb(92, 118, 46)), (0.25, srgb(110, 130, 52)), (0.45, srgb(84, 112, 44)),
                         (0.62, srgb(124, 136, 60)), (0.78, srgb(148, 140, 74)), (0.9, srgb(102, 124, 50)),
                         (1.0, srgb(170, 150, 90))], 'CONSTANT')
    n1 = s.noise(P, 0.02, detail=6.0, rough=0.6)
    n2 = s.noise(P, 0.2, detail=5.0, rough=0.6)
    past = s.hsv(past, v=s.maprange(n1, 0.3, 0.7, 0.8, 1.15))
    past = s.mix(s.m('MULTIPLY', s.maprange(n2, 0.55, 0.75), 0.4), past, srgb(150, 146, 84))
    # meadow/lawn near the house
    near_g = s.mix(s.maprange(s.noise(P, 0.5, detail=6.0), 0.3, 0.7), srgb(70, 98, 34), srgb(104, 122, 44))
    near_g = s.mix(s.m('MULTIPLY', s.maprange(s.noise(P, 3.0, detail=4.0), 0.6, 0.75), 0.5), near_g, srgb(120, 110, 60))
    col = s.mix(s.maprange(dist, 80.0, 220.0), near_g, past)
    # plateau (Causse): dry pale grass with rock outcrops
    causse = s.mix(s.maprange(s.noise(P, 0.01, detail=6.0), 0.3, 0.7), srgb(150, 146, 98), srgb(124, 128, 78))
    col = s.mix(s.maprange(z, 170.0, 230.0), col, causse)
    # hedges (only where the mesh is fine enough to matter)
    hedge_m = s.m('MULTIPLY', s.maprange(hedge, 5.0, 1.5), s.maprange(dist, 60.0, 120.0))
    col = s.mix(hedge_m, col, srgb(40, 56, 22))
    # forest canopy (texture stand-in beyond the instanced trees)
    fco = s.voronoi(P, 0.12, 'F1', '3D', out='Distance')
    canopy = s.mix(s.maprange(fco, 0.0, 0.9), srgb(58, 80, 28), srgb(22, 34, 12))
    canopy = s.hsv(canopy, v=s.maprange(s.noise(P, 0.004, detail=4.0), 0.3, 0.7, 0.8, 1.2))
    fmask = s.maprange(forest, 0.35, 0.6)
    col = s.mix(fmask, col, canopy)
    # cliffs on the escarpment
    rock = s.mix(s.maprange(s.noise(s.vm('MULTIPLY', P, (0.05, 0.05, 0.3)), 1.0, detail=6.0), 0.3, 0.7),
                 srgb(150, 140, 120), srgb(200, 190, 170))
    rmask = s.m('MULTIPLY', s.maprange(slope, 0.3, 0.45), s.maprange(z, 90.0, 140.0))
    col = s.mix(rmask, col, rock)
    bmp = s.m('ADD', s.m('MULTIPLY', s.m('SUBTRACT', 1.0, fco), fmask), s.m('MULTIPLY', s.noise(P, 1.5, detail=4.0), 0.2))
    nrm = s.bump(bmp, strength=0.6, distance=1.5)
    s.out_material(s.principled(base=col, rough=0.95, normal=nrm, spec=0.2))
    return m
