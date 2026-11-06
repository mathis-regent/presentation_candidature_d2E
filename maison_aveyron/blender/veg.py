"""Procedural trees (oak / chestnut), instanced woods, grass."""
import math
import numpy as np
import bpy
from lib import mesh_np, coll
import materials as M


def _perp(d):
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    p = np.cross(d, a)
    return p / np.linalg.norm(p)


def _rot(v, axis, ang):
    axis = axis / np.linalg.norm(axis)
    return (v * math.cos(ang) + np.cross(axis, v) * math.sin(ang)
            + axis * np.dot(axis, v) * (1 - math.cos(ang)))


TREE_PARAMS = {
    'oak': dict(trunk=3.0, r0=0.85, levels=4, nchild=[6, 6, 6, 6], cang=[(42, 66), (30, 55), (30, 60), (25, 60)],
                blen=[3.0, 8.0, 4.6, 2.3, 0.9], wob=[0.10, 0.2, 0.22, 0.28, 0.3],
                up=[0.0, 0.07, 0.05, 0.05, 0.06], crad=[0.5, 0.55, 0.55, 0.6], start=[0.85, 0.2, 0.15, 0.15],
                leaf=(0.16, 0.085), clusters=4.0, per_cluster=34, cl_r=0.24, seg=[0.5, 0.6, 0.45, 0.35, 0.25],
                mat='leaf_oak'),
    'chestnut': dict(trunk=2.5, r0=0.95, levels=4, nchild=[6, 6, 6, 6], cang=[(28, 52), (30, 55), (30, 60), (25, 60)],
                     blen=[2.5, 7.2, 4.4, 2.2, 0.9], wob=[0.14, 0.18, 0.22, 0.26, 0.3],
                     up=[0.02, 0.1, 0.06, 0.06, 0.07], crad=[0.5, 0.55, 0.55, 0.6], start=[0.8, 0.25, 0.15, 0.15],
                     leaf=(0.22, 0.075), clusters=4.0, per_cluster=26, cl_r=0.26, seg=[0.5, 0.6, 0.45, 0.35, 0.25],
                     mat='leaf_chestnut'),
    'far': dict(trunk=2.4, r0=0.32, levels=3, nchild=[7, 6, 6], cang=[(30, 60), (30, 60), (30, 60)],
                blen=[2.4, 4.0, 2.4, 1.3], wob=[0.12, 0.22, 0.28, 0.3],
                up=[0.02, 0.08, 0.06, 0.08], crad=[0.5, 0.55, 0.6], start=[0.75, 0.2, 0.15],
                leaf=(0.55, 0.42), clusters=3.0, per_cluster=12, cl_r=0.45, seg=[0.8, 1.0, 0.8, 0.6], mat='leaf_far'),
}


def make_tree(name, seed, kind='oak', scale=1.0, collection=None, link=True, leaf_scale=1.0):
    P = TREE_PARAMS[kind]
    rng = np.random.default_rng(seed)
    branches = []
    leaves = []

    def grow(p0, d0, length, r0, level):
        seg = P['seg'][level]
        nseg = max(2, int(math.ceil(length / seg)))
        pts, rads = [p0.copy()], [r0]
        p, d = p0.copy(), d0 / np.linalg.norm(d0)
        for i in range(nseg):
            t = (i + 1) / nseg
            d = d + rng.normal(0, P['wob'][level], 3)
            d[2] += P['up'][level]
            if level >= 3:
                d[2] -= 0.03 * t       # twigs droop a little
            d /= np.linalg.norm(d)
            lim = -0.05 if level <= 2 else -0.35
            if d[2] < lim:
                d[2] = lim
                d /= np.linalg.norm(d)
            p = p + d * length / nseg
            pts.append(p.copy())
            rads.append(r0 * (1 - 0.75 * t) if level < P['levels'] else r0 * (1 - 0.9 * t))
        pts = np.array(pts)
        rads = np.array(rads)
        branches.append((pts, rads, level))
        if level >= P['levels']:
            ncl = max(1, int(round(length * P['clusters'])))
            for c in range(ncl):
                t = 0.25 + 0.75 * (c + rng.uniform(0.3, 1.0)) / ncl
                k = min(int(t * nseg), nseg - 1)
                f = min(1.0, t * nseg - k)
                q = pts[k] * (1 - f) + pts[k + 1] * f
                cen = q + rng.normal(0, P['cl_r'] * 0.4, 3)
                npc = int(P['per_cluster'] * leaf_scale * rng.uniform(0.6, 1.3))
                off = rng.normal(0, 1, (npc, 3))
                off /= np.linalg.norm(off, axis=1)[:, None]
                off *= (rng.random((npc, 1)) ** 0.5) * P['cl_r']
                off[:, 2] *= 0.7
                leaves.extend(list(cen + off))
            return
        nch = P['nchild'][level]
        phase = rng.uniform(0, 2 * math.pi)
        for c in range(nch):
            t = P['start'][level] + (1 - P['start'][level]) * (c + rng.uniform(0.2, 0.8)) / nch
            if level == 0:
                t = P['start'][0] + (1 - P['start'][0]) * rng.uniform(0, 1)
            k = min(int(t * nseg), nseg - 1)
            f = t * nseg - k
            q = pts[k] * (1 - f) + pts[k + 1] * f
            rq = rads[k] * (1 - f) + rads[k + 1] * f
            pd = pts[k + 1] - pts[k]
            pd /= np.linalg.norm(pd)
            ang = math.radians(rng.uniform(*P['cang'][level]))
            az = phase + c * 2.39996 + rng.normal(0, 0.3)
            ax = _rot(_perp(pd), pd, az)
            cd = _rot(pd, ax, ang)
            L = P['blen'][level + 1] * rng.uniform(0.75, 1.2) * (1.0 - 0.35 * (t - 0.5) if level > 0 else 1.0)
            grow(q, cd, L * scale, max(0.012, rq * P['crad'][level] * rng.uniform(0.85, 1.1)), level + 1)
        # trunk/limb continues into a leader for the next level
        if level < P['levels'] - 1 and level > 0:
            grow(pts[-1], pts[-1] - pts[-2], P['blen'][level + 1] * 0.7 * scale, rads[-1] * 1.4 + 0.01, level + 1)

    tdir = np.array([rng.normal(0, 0.05), rng.normal(0, 0.05), 1.0])
    grow(np.array([0, 0, -0.4]), tdir, (P['trunk'] + 0.4) * scale, P['r0'] * scale, 0)

    # ---- branch tubes ----
    V, F = [], []
    nv = 0
    for pts, rads, level in branches:
        ns = [12, 8, 6, 4, 3][min(level, 4)]
        if kind == 'far':
            ns = [6, 4, 3, 3][min(level, 3)]
        n = len(pts)
        ang = np.linspace(0, 2 * math.pi, ns, endpoint=False)
        tvec = pts[1] - pts[0]
        tvec /= np.linalg.norm(tvec)
        u = _perp(tvec)
        for i in range(n):
            if i > 0:
                tn = pts[i] - pts[i - 1]
                tn /= np.linalg.norm(tn)
                u = u - tn * np.dot(u, tn)
                u /= np.linalg.norm(u)
                tvec = tn
            w = np.cross(tvec, u)
            r = rads[i]
            if level == 0 and i <= 1:
                r *= 1.45 if i == 0 else 1.15     # trunk flare
            ring = pts[i] + r * (np.outer(np.cos(ang), u) + np.outer(np.sin(ang), w))
            if level == 0:
                ring += np.outer(np.cos(ang * 3 + seed), u) * r * 0.08
            V.append(ring)
        for i in range(n - 1):
            for j in range(ns):
                a = nv + i * ns + j
                b = nv + i * ns + (j + 1) % ns
                F.append([a, b, b + ns, a + ns])
        nv += n * ns
    V = np.concatenate(V)
    wood = mesh_np(name + '_wood', V, F, mats=[M.get('bark')], collection=collection, smooth=True, link=link)

    # ---- leaves (diamond quads) ----
    L = np.array(leaves)
    nl = len(L)
    lw, lh = P['leaf']
    lw, lh = lw * scale ** 0.3, lh * scale ** 0.3
    axis = rng.normal(0, 1, (nl, 3))
    axis[:, 2] -= 0.6
    axis /= np.linalg.norm(axis, axis=1)[:, None]
    nrm = rng.normal(0, 1, (nl, 3))
    nrm[:, 2] += 1.2
    nrm -= axis * np.sum(nrm * axis, 1)[:, None]
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    side = np.cross(axis, nrm)
    sz = rng.uniform(0.75, 1.25, nl)[:, None]
    p0 = L
    p1 = L + axis * lw * sz * 0.45 + side * lh * sz * 0.5
    p2 = L + axis * lw * sz
    p3 = L + axis * lw * sz * 0.45 - side * lh * sz * 0.5
    VL = np.stack([p0, p1, p2, p3], 1).reshape(-1, 3)
    FL = np.arange(nl * 4).reshape(nl, 4)
    leaf = mesh_np(name + '_leaves', VL, FL, mats=[M.get(P['mat'])], collection=collection, link=link,
                   face_attrs={'rnd': rng.random(nl)})
    return wood, leaf, nl


def place(obs, loc, rotz=0.0, s=1.0):
    for ob in obs:
        ob.location = loc
        ob.rotation_euler = (0, 0, rotz)
        ob.scale = (s, s, s)


# ----------------------------------------------------------------------------
def instancer(name, points, scales, rotz, variant, src_collection, collection):
    """Geometry-nodes instancing of a collection's children on points."""
    me_pts = mesh_np(name + '_pts', points, [], link=False,
                     point_attrs={'scale': scales, 'rotz': rotz, 'var': variant.astype(np.float32)})
    ob = bpy.data.objects.new(name, me_pts.data)
    collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput')
    go = N.new('NodeGroupOutput')
    ci = N.new('GeometryNodeCollectionInfo')
    ci.inputs['Collection'].default_value = src_collection
    ci.inputs['Separate Children'].default_value = True
    ci.inputs['Reset Children'].default_value = True
    ci.transform_space = 'ORIGINAL'
    iop = N.new('GeometryNodeInstanceOnPoints')
    a_s = N.new('GeometryNodeInputNamedAttribute')
    a_s.data_type = 'FLOAT'
    a_s.inputs['Name'].default_value = 'scale'
    a_r = N.new('GeometryNodeInputNamedAttribute')
    a_r.data_type = 'FLOAT'
    a_r.inputs['Name'].default_value = 'rotz'
    a_v = N.new('GeometryNodeInputNamedAttribute')
    a_v.data_type = 'FLOAT'
    a_v.inputs['Name'].default_value = 'var'
    comb = N.new('ShaderNodeCombineXYZ')
    Lk.new(a_r.outputs['Attribute'], comb.inputs['Z'])
    e2r = N.new('FunctionNodeEulerToRotation') if hasattr(bpy.types, 'FunctionNodeEulerToRotation') else None
    Lk.new(gi.outputs[0], iop.inputs['Points'])
    Lk.new(ci.outputs[0], iop.inputs['Instance'])
    iop.inputs['Pick Instance'].default_value = True
    Lk.new(a_v.outputs['Attribute'], iop.inputs['Instance Index'])
    if e2r is not None:
        Lk.new(comb.outputs[0], e2r.inputs[0])
        Lk.new(e2r.outputs[0], iop.inputs['Rotation'])
    else:
        Lk.new(comb.outputs[0], iop.inputs['Rotation'])
    Lk.new(a_s.outputs['Attribute'], iop.inputs['Scale'])
    Lk.new(iop.outputs[0], go.inputs[0])
    mod = ob.modifiers.new('inst', 'NODES')
    mod.node_group = ng
    return ob


# ----------------------------------------------------------------------------
def grass_material():
    from lib import new_material, srgb
    m, s = new_material('grass')
    hi = s.node('ShaderNodeHairInfo')
    rnd = hi.outputs['Random']
    icpt = hi.outputs['Intercept']
    base = s.ramp(rnd, [(0.0, srgb(64, 90, 26)), (0.35, srgb(82, 106, 32)), (0.6, srgb(98, 116, 38)),
                        (0.82, srgb(116, 124, 46)), (0.93, srgb(150, 138, 68)), (1.0, srgb(178, 158, 96))])
    P = s.geo('Position')
    patch = s.maprange(s.noise(P, 0.25, detail=3.0), 0.3, 0.7, 0.8, 1.15)
    base = s.hsv(base, v=patch)
    dry = s.maprange(s.noise(P, 0.6, detail=3.0), 0.58, 0.72, 0.0, 0.55)
    base = s.mix(dry, base, srgb(150, 140, 80))
    col = s.mix(s.maprange(icpt, 0.0, 0.7), s.hsv(base, v=0.45), s.hsv(base, v=1.1, s=0.95))
    bs = s.principled(base=col, rough=0.5, spec=0.35)
    tr = s.node('ShaderNodeBsdfTranslucent', ins={'Color': s.hsv(col, s=1.2, v=1.2)})
    mx = s.node('ShaderNodeMixShader', ins={0: 0.3})
    s.t.links.new(bs, mx.inputs[1])
    s.t.links.new(tr.outputs[0], mx.inputs[2])
    s.out_material(mx.outputs[0])
    return m


def grass(name, V, F, weights, count, length, collection, mat, children=10, child_radius=0.06,
          root=0.0025, tip=0.0004, rough=0.02, clump=0.0, seed=1):
    ob = mesh_np(name, V, F, collection=collection, smooth=True)
    ob.data.materials.append(M.get('_dummy') if False else mat)
    vg = ob.vertex_groups.new(name='dens')
    for i, w in enumerate(weights):
        if w > 0:
            vg.add([i], float(w), 'REPLACE')
    mod = ob.modifiers.new('grass', 'PARTICLE_SYSTEM')
    psys = ob.particle_systems[0]
    psys.seed = seed
    ps = psys.settings
    ps.type = 'HAIR'
    ps.count = count
    ps.hair_length = length
    ps.emit_from = 'FACE'
    ps.use_emit_random = True
    ps.distribution = 'RAND'
    ps.use_advanced_hair = True
    ps.normal_factor = 1.0
    ps.factor_random = 0.45
    ps.render_type = 'PATH'
    ps.display_step = 2
    ps.render_step = 3
    ps.child_type = 'SIMPLE' if children else 'NONE'
    ps.child_percent = 1
    ps.rendered_child_count = children
    ps.child_radius = child_radius
    ps.child_roundness = 0.6
    ps.child_length = 1.0
    ps.child_length_threshold = 0.5
    ps.clump_factor = clump
    ps.roughness_1 = rough
    ps.roughness_1_size = 1.0
    ps.roughness_endpoint = length * 0.35
    ps.roughness_end_shape = 1.0
    ps.roughness_2 = rough * 0.5
    ps.roughness_2_size = 2.0
    ps.root_radius = root
    ps.tip_radius = tip
    ps.radius_scale = 1.0
    ps.use_close_tip = True
    ps.material_slot = mat.name
    psys.vertex_group_density = 'dens'

    ob.show_instancer_for_render = False
    ps.length_random = 0.6 if hasattr(ps, 'length_random') else 0
    return ob
