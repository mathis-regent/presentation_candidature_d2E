import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, bpy
from lib import reset_scene
import materials as M, house, land, scene_setup as SS
reset_scene()
rng = np.random.default_rng(7)
house.build(rng)
t = time.time(); land.build_terrain(rng); print('terrain', time.time() - t)
SS.setup_world(1.0); SS.setup_sun(4.0)
cx, cy, tx, ty, sh = [float(a) for a in sys.argv[1:6]]
cz = float(land.height(np.array([cx]), np.array([cy]))[0]) + 1.65
SS.setup_camera((cx, cy, cz), (tx, ty, cz), 24.0, shift_y=sh)
out = os.environ.get('OUT', '/tmp/claude-0/-home-user-presentation-candidature-d2E/3dac11c7-155d-5002-b395-715b89835db0/scratchpad/test_land.png')
SS.render_settings((720, 480), 16, out, passes=False)
t = time.time(); bpy.ops.render.render(write_still=True); print('render', time.time() - t)
