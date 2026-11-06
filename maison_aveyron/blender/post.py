"""Post-process: sky clouds, aerial haze, valley mist (height fog), AgX tone map, finishing.

usage: python post.py render.exr out.png [key=value ...]
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import OpenEXR
from land import fbm, sstep

src, dst = sys.argv[1], sys.argv[2]
opt = dict(a.split('=') for a in sys.argv[3:])
P = {k: float(v) for k, v in dict(
    haze=1 / 11000.0, haze_h=1500.0, mist=0.010, mist_z=-40.0, mist_h=16.0, clouds=1.0,
    cloud_alt=2600.0, exposure=0.0, warm=1.0, vignette=0.22, grain=0.012, look=1, mist_bright=1.2).items()}
P.update({k: float(v) for k, v in opt.items()})

meta = json.load(open(os.path.splitext(src)[0] + '.json'))
f = OpenEXR.File(src)
ch = {}
for part in f.parts:
    for k, c in part.channels.items():
        ch[k.replace('ViewLayer.', '')] = c.pixels.astype(np.float64)
comb = ch['Combined']
rgb, A = comb[..., :3], comb[..., 3]
env = ch['Environment'][..., :3]
Pos = np.stack([ch['Position.X'], ch['Position.Y'], ch['Position.Z']], -1)
H, W = A.shape

# ---- camera rays
C = np.array(meta['cam'])
yaw, lens = meta['yaw'], meta['lens']
sw, sh_ = meta['sensor']
jj, ii = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
xs = (jj / W - 0.5) * sw
ys = (0.5 - ii / H) * (sw * H / W) + meta['shift_y'] * sw
fwd = np.array([math.cos(yaw), math.sin(yaw), 0.0])
right = np.array([math.sin(yaw), -math.cos(yaw), 0.0])
up = np.array([0, 0, 1.0])
pitch = meta.get('pitch', 0.0)
fwd2 = fwd * math.cos(pitch) + up * math.sin(pitch)
up2 = -fwd * math.sin(pitch) + up * math.cos(pitch)
D = fwd2 * lens + right * xs[..., None] + up2 * ys[..., None]
D /= np.linalg.norm(D, axis=-1, keepdims=True)
sun = np.array(meta['sun'])
sun_col = np.array(meta['sun_color'])

# ---- sky behind geometry
cov_bg = np.clip(1 - A, 0, 1)
sky = np.where(cov_bg[..., None] > 1e-3, env / np.maximum(cov_bg, 1e-3)[..., None], 0.0)
skymask = cov_bg > 0.5
el = D[..., 2]
band = skymask & (el > 0.06) & (el < 0.14)
sky_h = np.median(sky[band], axis=0) if band.sum() > 50 else np.array([0.5, 0.55, 0.65])
band2 = skymask & (el > 0.25)
sky_z = np.median(sky[band2], axis=0) if band2.sum() > 50 else sky_h * 0.6
lum = lambda c: 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
print('sky horizon', sky_h, 'zenith', sky_z, 'band px', band.sum(), 'sky px', skymask.sum())
_g = A > 0.99
_v = Pos[_g] - C
_v /= np.linalg.norm(_v, axis=-1, keepdims=True)
print('ray check: median angle err (deg)', np.degrees(np.median(np.arccos(np.clip(np.sum(_v * D[_g], -1), -1, 1)))))

# ---- clouds (perspective-correct layer, lit by the low sun from behind the camera)
if P['clouds'] > 0:
    ok = el > 0.004
    t = np.where(ok, P['cloud_alt'] / np.maximum(el, 1e-4), 0)
    X = C[0] + D[..., 0] * t
    Y = C[1] + D[..., 1] * t
    phi = math.radians(25.0)
    u = (X * math.cos(phi) + Y * math.sin(phi)) / 5200.0
    v = (-X * math.sin(phi) + Y * math.cos(phi)) / 1700.0
    sel = ok & (cov_bg > 0)
    n = np.zeros_like(el)
    n[sel] = fbm(u[sel], v[sel], 6, seed=3) + 0.35 * fbm(u[sel] * 3.3, v[sel] * 3.3, 4, seed=5)
    big = np.zeros_like(el)
    big[sel] = fbm(X[sel] / 16000.0, Y[sel] / 16000.0, 2, seed=1)
    cov = sstep(0.12, 0.55, n) * sstep(-0.15, 0.3, big)
    fade = np.exp(-t / 38000.0) * sstep(0.004, 0.03, el)
    alpha = np.clip(cov * fade * 0.9 * P['clouds'], 0, 1)
    thick = sstep(0.3, 0.9, n)
    base_l = lum(sky_h)
    lit = sun_col / lum(sun_col) * base_l * 1.35
    shade = sky_z * 0.85 + np.array([0.02, 0.0, 0.03]) * base_l
    ccol = lit[None, None, :] * (1 - 0.55 * thick[..., None]) + shade[None, None, :] * (0.55 * thick[..., None])
    sky = sky * (1 - alpha[..., None]) + ccol * alpha[..., None]

# ---- height fog (aerial haze + valley mist), analytic integral along each ray
def fog_tau(L, dz, z0, sigma0, zref, Hs):
    """Integral of sigma0*exp(-(z - zref)/H) along a ray from height z0 with slope dz for length L."""
    base = sigma0 * np.exp(-(z0 - zref) / Hs)
    k = dz * L / Hs
    small = np.abs(k) < 1e-4
    frac = np.where(small, 1 - k / 2, -np.expm1(-k) / np.where(small, 1, k))
    return base * L * frac

geo = A > 1e-3
Pg = np.where(geo[..., None], Pos / np.maximum(A, 1e-3)[..., None], 0)
V = Pg - C
L = np.linalg.norm(V, axis=-1)
L = np.where(geo, L, 60000.0)
dz = D[..., 2]
tau_h = fog_tau(L, dz, C[2], P['haze'], 0.0, P['haze_h'])
# mist only for rays that dip into the valley; modulate by patchy noise at the end point
endx = C[0] + D[..., 0] * np.minimum(L, 8000)
endy = C[1] + D[..., 1] * np.minimum(L, 8000)
patch = np.clip(0.35 + 1.6 * fbm(endx / 300.0, endy / 300.0, 4, seed=6), 0.0, 1.6)
tau_m = fog_tau(L, dz, C[2], P['mist'], P['mist_z'], P['mist_h']) * patch * geo
T_h = np.exp(-tau_h)
T_m = np.exp(-tau_m)
cosg = np.clip(D @ sun, -1, 1)
g = 0.55
hg = (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * cosg) ** 1.5)
haze_col = sky_h[None, None, :] * 1.0 + (sun_col / lum(sun_col) * lum(sky_h))[None, None, :] * (0.25 + 3.0 * hg[..., None]) * P['warm']
mist_col = (np.array([1.0, 0.88, 0.76]) * lum(sky_h) * P['mist_bright'])[None, None, :]

col_geo = rgb * T_h[..., None] + A[..., None] * haze_col * (1 - T_h[..., None])
col_geo = col_geo * T_m[..., None] + A[..., None] * mist_col * (1 - T_m[..., None])
sky_f = sky * T_h[..., None] + haze_col * (1 - T_h[..., None])
out = col_geo + cov_bg[..., None] * sky_f
out *= 2 ** P['exposure']
print('tau_h range', np.percentile(tau_h[geo], [5, 50, 95]), 'mist', np.percentile(tau_m[geo], [50, 95, 99.5]))

# ---- tone map with Blender's AgX
import bpy
sc = bpy.context.scene
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = ['AgX - Base Contrast', 'AgX - Medium High Contrast', 'AgX - Punchy'][int(P['look'])]
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '8'
img = bpy.data.images.new('post', W, H, alpha=False, float_buffer=True)
px = np.ones((H, W, 4), np.float32)
px[..., :3] = out[::-1]
img.pixels.foreach_set(px.ravel())
img.update()
tmp = os.path.splitext(dst)[0] + '_tm.png'
img.save_render(tmp, scene=sc)

# ---- finishing: vignette, subtle grain
from PIL import Image
im = np.asarray(Image.open(tmp).convert('RGB')).astype(np.float64) / 255.0
im = im[..., :3]
r2 = ((jj / W - 0.5) ** 2 + ((ii / H - 0.5) * H / W) ** 2) / 0.36
vig = 1 - P['vignette'] * np.clip(r2, 0, 1.5) ** 1.5
im = im * vig[..., None]
rng = np.random.default_rng(0)
im += rng.normal(0, P['grain'], im.shape[:2])[..., None] * (0.6 + 0.4 * im)
im = np.clip(im, 0, 1)
Image.fromarray((im * 255 + 0.5).astype(np.uint8)).save(dst)
os.remove(tmp)
print('saved', dst)
