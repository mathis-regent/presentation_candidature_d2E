import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, bpy
from lib import reset_scene, mesh_np
import materials as M, veg, scene_setup as SS
reset_scene()
kind = sys.argv[1]
t = time.time()
w, l, nl = veg.make_tree('t', 3, kind)
print('tree', time.time() - t, 'leaves', nl, 'wood verts', len(w.data.vertices))
mesh_np('ground', np.array([(-200, -200, 0), (200, -200, 0), (200, 200, 0), (-200, 200, 0)]), [[0, 1, 2, 3]])
SS.setup_world(0.4); SS.setup_sun(4.0)
d = 30 if kind != 'far' else 18
SS.setup_camera((0, -d, 1.7), (0, 0, 1.7), 35, shift_y=0.25)
out = '/tmp/claude-0/-home-user-presentation-candidature-d2E/3dac11c7-155d-5002-b395-715b89835db0/scratchpad/test_tree_%s.png' % kind
SS.render_settings((480, 480), 16, out, passes=False)
t = time.time(); bpy.ops.render.render(write_still=True); print('render', time.time() - t)
