import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, bpy
from lib import reset_scene, mesh_np
import materials as M, house, scene_setup as SS
reset_scene()
rng = np.random.default_rng(7)
t = time.time(); house.build(rng); print('house', time.time() - t)
# quick ground
mesh_np('ground', np.array([(-200, -200, 0), (200, -200, 0), (200, 200, 0), (-200, 200, 0)]), [[0, 1, 2, 3]])
SS.setup_world(1.0); SS.setup_sun(4.0)
cam = sys.argv[1] if len(sys.argv) > 1 else 'nw'
if cam == 'nw':
    SS.setup_camera((-19.0, 21.0, 1.65), (2.0, 0.0, 1.65), 24.0, shift_y=0.12)
elif cam == 'close':
    SS.setup_camera((-6.0, 12.0, 2.0), (-12, 4.7, 2.0), 35.0, shift_y=0.0)
elif cam == 'roof':
    SS.setup_camera((-16.0, 14.0, 9.0), (-12, 4.7, 8.0), 50.0)
out = os.environ.get('OUT', '/tmp/claude-0/-home-user-presentation-candidature-d2E/3dac11c7-155d-5002-b395-715b89835db0/scratchpad/test_house.png')
SS.render_settings((720, 480), 24, out, passes=False)
t = time.time(); bpy.ops.render.render(write_still=True); print('render', time.time() - t)
