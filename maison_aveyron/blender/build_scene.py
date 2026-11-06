"""Assemble the full scene and render.

usage: python build_scene.py <preset> [out.exr]
presets: preview (fast), final
"""
import sys, os, time, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
from lib import reset_scene, coll, mesh_np
import materials as M
import house, land, garden, veg
import scene_setup as SS

PRESET = sys.argv[1] if len(sys.argv) > 1 else 'preview'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.abspath('render_%s.exr' % PRESET)
CFG = dict(
    preview=dict(res=(900, 600), samples=48, grass=0.25, trees=0.35, noise=0.05),
    mid=dict(res=(1350, 900), samples=128, grass=0.6, trees=0.7, noise=0.03),
    final=dict(res=(2400, 1600), samples=384, grass=1.0, trees=1.0, noise=0.012),
)[PRESET]
CAM = json.loads(os.environ.get('CAM', '{}'))
cam_xy = CAM.get('pos', [-27.0, 21.5])
cam_t = CAM.get('target', [8.0, -2.0])
cam_h = CAM.get('h', 1.65)
cam_shift = CAM.get('shift', 0.06)
cam_lens = CAM.get('lens', 24.0)
FLAGS = os.environ.get('FLAGS', 'house,land,garden,hero,woods,grass').split(',')

t0 = time.time()
reset_scene()
rng = np.random.default_rng(11)


def log(*a):
    print('[%6.1fs]' % (time.time() - t0), *a, flush=True)


cz = float(land.height(np.array([cam_xy[0]]), np.array([cam_xy[1]]))[0]) + cam_h
cam_pos = np.array([cam_xy[0], cam_xy[1], cz])
yaw = math.atan2(cam_t[1] - cam_xy[1], cam_t[0] - cam_xy[0])
hfov = 2 * math.atan(18.0 / cam_lens)

if 'house' in FLAGS:
    house.build(rng)
    log('house')
if 'land' in FLAGS:
    land.build_terrain(rng)
    log('terrain')
if 'garden' in FLAGS:
    garden.build(rng)
    log('garden')

# ---------------------------------------------------------------- hero trees
if 'hero' in FLAGS:
    hc = coll('trees_hero')
    heroes = [
        ('chestnut', 21, (-15.5, -13.0), 1.30, 0.4),
        ('oak', 5, (20.0, -14.0), 1.35, 1.9),
        ('chestnut', 33, (-2.0, -24.0), 1.15, 0.9),
    ]
    for kind, seed, (x, y), sc, rz in heroes:
        z = float(land.height(np.array([x]), np.array([y]))[0])
        w, l, nl = veg.make_tree('%s_%d' % (kind, seed), seed, kind, collection=hc,
                                 leaf_scale=1.0 if CFG['trees'] >= 0.7 else 0.5)
        veg.place((w, l), (x, y, z), rz, sc)
    log('hero trees')

# ---------------------------------------------------------------- woods / hedges (instanced)
if 'woods' in FLAGS:
    src = bpy.data.collections.new('tree_src_mid')
    srcf = bpy.data.collections.new('tree_src_far')
    for i, (kind, seed) in enumerate([('oak', 101), ('chestnut', 102), ('oak', 103)]):
        w, l, _ = veg.make_tree('mid%d' % i, seed, kind, link=False, leaf_scale=0.22)
        par = bpy.data.objects.new('midtree%d' % i, None)
        src.objects.link(par)
        for o in (w, l):
            src.objects.link(o)
            o.parent = par
    for i, seed in enumerate((201, 202, 203)):
        w, l, _ = veg.make_tree('far%d' % i, seed, 'far', link=False)
        par = bpy.data.objects.new('fartree%d' % i, None)
        srcf.objects.link(par)
        for o in (w, l):
            srcf.objects.link(o)
            o.parent = par
    # sample candidate positions in the camera's view sector
    n_cand = int(900000 * CFG['trees'])
    a0, a1 = yaw - hfov / 2 - 0.25, yaw + hfov / 2 + 0.25
    rmin, rmax = 22.0, 3800.0
    r = np.sqrt(rng.uniform(rmin ** 2, rmax ** 2, n_cand))
    a = rng.uniform(a0, a1, n_cand)
    x = cam_pos[0] + r * np.cos(a)
    y = cam_pos[1] + r * np.sin(a)
    h = land.height(x, y)
    fm = land.forest_mask(x, y, h)
    tone, hd = land.field_info(x, y)
    p = 0.55 * fm ** 1.5
    hedge = (hd < 3.0) & (r < 1800) & (fm < 0.5)
    p = np.where(hedge, np.maximum(p, 0.6 * (1 - tone * 0.5)), p)
    p = np.maximum(p, 0.004)                             # isolated field trees
    # density control: real density of candidates is n_cand/area; thin with distance a little
    p *= np.where(r < 300, 1.0, 0.8)
    keep = rng.random(n_cand) < p
    # garden / drive exclusions
    de = np.hypot((x + 8.0) / 44.0, (y - 8.0) / 34.0)
    keep &= de > 1.15
    keep &= garden.dist_to_polyline(garden.drive_line(), x, y) > 4.0
    x, y, h, r, hedge = x[keep], y[keep], h[keep], r[keep], hedge[keep]
    sc = rng.uniform(0.75, 1.3, len(x)) * np.where(hedge, 0.8, 1.0)
    rz = rng.uniform(0, 2 * math.pi, len(x))
    near = r < 320
    wc = coll('woods')
    for nm, sel, srcc in (('woods_mid', near, src), ('woods_far', ~near, srcf)):
        pts = np.column_stack([x[sel], y[sel], h[sel] - 0.2])
        var = rng.integers(0, 3, sel.sum())
        veg.instancer(nm, pts, sc[sel], rz[sel], var, srcc, wc)
    log('woods: %d mid, %d far' % (near.sum(), (~near).sum()))

# ---------------------------------------------------------------- lawn grass
if 'grass' in FLAGS:
    gc = coll('grass')
    na, nr = 160, 120
    aa = np.linspace(yaw - hfov / 2 - 0.12, yaw + hfov / 2 + 0.12, na)
    rr = 1.2 + (np.linspace(0, 1, nr) ** 1.8) * 50.0
    A, R = np.meshgrid(aa, rr)
    X = cam_pos[0] + R * np.cos(A)
    Y = cam_pos[1] + R * np.sin(A)
    Z = land.height(X, Y)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    idx = np.arange(na * nr).reshape(nr, na)
    F = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    Rv = R.ravel()
    w = 1.0 / (1.0 + (Rv / 9.0) ** 2)
    de = np.hypot((X.ravel() + 8.0) / 44.0, (Y.ravel() - 8.0) / 34.0)
    w *= (de < 1.05)
    w *= ~garden.no_grass_mask(X.ravel(), Y.ravel())
    w = np.clip(w, 0, 1)
    gm = veg.grass_material()
    veg.grass('lawn', V, F, w, int(60000 * CFG['grass']), 0.09, gc, gm, children=12, child_radius=0.05,
              root=0.0022, tip=0.0003, rough=0.012, seed=3)
    # longer unmown grass along the dry-stone walls and the house base
    dw = np.minimum.reduce([garden.dist_to_polyline(garden._smooth(wl, 2), X.ravel(), Y.ravel()) for wl in garden.WALLS])
    w2 = np.clip(1.2 - np.abs(dw - 0.7) / 0.6, 0, 1) * (Rv < 60)
    veg.grass('wall_grass', V, F, w2, int(12000 * CFG['grass']), 0.32, gc, gm, children=8, child_radius=0.08,
              root=0.003, tip=0.0003, rough=0.05, seed=5)
    log('grass')

SS.setup_world(float(os.environ.get('SKY', 0.26)))
SS.setup_sun(float(os.environ.get('SUNE', 5.8)))
tz = cz + CAM.get('tilt', 0.0)
SS.setup_camera(tuple(cam_pos), (cam_t[0], cam_t[1], tz), cam_lens, shift_y=cam_shift)
SS.render_settings(CFG['res'], CFG['samples'], OUT, noise=CFG['noise'], passes=OUT.endswith('.exr'))
if os.environ.get('BORDER'):
    b = [float(v) for v in os.environ['BORDER'].split(',')]
    sc = bpy.context.scene
    sc.render.use_border = True
    sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = b
if os.environ.get('SAVE_BLEND'):
    bpy.ops.wm.save_as_mainfile(filepath=os.environ['SAVE_BLEND'])
sv = SS.sun_vector()
with open(os.path.splitext(OUT)[0] + '.json', 'w') as fh:
    json.dump(dict(cam=list(map(float, cam_pos)), yaw=yaw, lens=cam_lens, shift_y=cam_shift, sensor=[36.0, 24.0],
                   res=list(CFG['res']), sun=[sv.x, sv.y, sv.z], sun_color=list(bpy.data.lights['sun'].color),
                   pitch=math.atan2(tz - cz, math.hypot(cam_t[0] - cam_xy[0], cam_t[1] - cam_xy[1]))), fh)
log('rendering', CFG)
bpy.ops.render.render(write_still=True)
log('done ->', OUT)
