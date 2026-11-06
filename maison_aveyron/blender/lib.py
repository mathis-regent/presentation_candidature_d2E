"""Helpers: mesh creation from numpy, node-tree builders, misc geometry."""
import math
import bpy
import numpy as np


# ----------------------------------------------------------------------------
# Scene / collections
# ----------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


# ----------------------------------------------------------------------------
# Mesh creation
# ----------------------------------------------------------------------------
def mesh_np(name, V, F, mats=None, collection=None, smooth=False,
            mat_index=None, face_attrs=None, point_attrs=None, link=True):
    """Create a mesh object from numpy arrays.
    V: (n,3) floats. F: (m,k) int array or list of index sequences.
    face_attrs / point_attrs: {name: (n,) or (n,4) array} stored as FLOAT/FLOAT_COLOR.
    """
    V = np.ascontiguousarray(np.asarray(V, np.float32).reshape(-1, 3))
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set('co', V.ravel())
    if isinstance(F, np.ndarray):
        F = F.astype(np.int32)
        sizes = np.full(len(F), F.shape[1], np.int32)
        flat = F.ravel()
    else:
        sizes = np.array([len(f) for f in F], np.int32)
        flat = (np.concatenate([np.asarray(f, np.int32) for f in F])
                if len(F) else np.zeros(0, np.int32))
    starts = np.zeros(len(sizes), np.int32)
    if len(sizes) > 1:
        starts[1:] = np.cumsum(sizes)[:-1]
    me.loops.add(len(flat))
    me.loops.foreach_set('vertex_index', flat)
    me.polygons.add(len(sizes))
    me.polygons.foreach_set('loop_start', starts)
    me.update(calc_edges=True)
    if mats:
        for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
            me.materials.append(m)
    if mat_index is not None:
        me.polygons.foreach_set('material_index', np.asarray(mat_index, np.int32))
    for attrs, domain in ((face_attrs, 'FACE'), (point_attrs, 'POINT')):
        if not attrs:
            continue
        for an, arr in attrs.items():
            arr = np.asarray(arr, np.float32)
            if arr.ndim == 2:
                a = me.attributes.new(an, 'FLOAT_COLOR', domain)
                a.data.foreach_set('color', arr.ravel())
            else:
                a = me.attributes.new(an, 'FLOAT', domain)
                a.data.foreach_set('value', arr.ravel())
    me.validate(clean_customdata=False)
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    if link:
        (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


class MeshBuilder:
    """Accumulates many small parts (with material slot index) into one mesh."""

    def __init__(self):
        self.V, self.F, self.M, self.FA = [], [], [], []
        self.n = 0

    def add(self, V, F, mat=0, fattr=0.0):
        V = np.asarray(V, np.float64).reshape(-1, 3)
        if isinstance(F, np.ndarray):
            F = [list(f) for f in F]
        self.V.append(V)
        for f in F:
            self.F.append([i + self.n for i in f])
            self.M.append(mat)
            self.FA.append(fattr)
        self.n += len(V)

    def add_box(self, center, half, R=None, mat=0, fattr=0.0, template=None):
        tv, tf = template if template is not None else BOX
        v = tv * np.asarray(half)
        if R is not None:
            v = v @ np.asarray(R).T
        self.add(v + np.asarray(center), tf, mat, fattr)

    def build(self, name, mats, collection=None, smooth=False, attr_name='rnd'):
        if not self.V:
            return None
        V = np.concatenate(self.V)
        return mesh_np(name, V, self.F, mats=mats, collection=collection,
                       smooth=smooth, mat_index=self.M,
                       face_attrs={attr_name: np.asarray(self.FA)})


# unit cube [-1,1]^3 with outward quads
_bv = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
_bf = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
BOX = (_bv, _bf)


def chamfer_box(c=0.18):
    """Unit cube with chamfered edges/corners (24 verts), good for stones."""
    V = []
    idx = {}
    k = 1 - c
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                for ax in range(3):
                    p = [sx * k, sy * k, sz * k]
                    p[ax] = [sx, sy, sz][ax]
                    idx[(sx, sy, sz, ax)] = len(V)
                    V.append(p)
    F = []
    # 6 main faces
    for ax in range(3):
        for s in (-1, 1):
            o = [a for a in range(3) if a != ax]
            quad = []
            for (u, w) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [0, 0, 0]
                key[ax] = s
                key[o[0]] = u
                key[o[1]] = w
                quad.append(idx[(key[0], key[1], key[2], ax)])
            F.append(quad)
    # 12 edge faces
    for ax in range(3):  # edge parallel to axis ax
        o = [a for a in range(3) if a != ax]
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                q = []
                for sa in (-1, 1):
                    for which in (o[0], o[1]):
                        key = [0, 0, 0]
                        key[ax] = sa
                        key[o[0]] = s1
                        key[o[1]] = s2
                        q.append(idx[(key[0], key[1], key[2], which)])
                F.append([q[0], q[1], q[3], q[2]])
    # 8 corner triangles
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                F.append([idx[(sx, sy, sz, 0)], idx[(sx, sy, sz, 1)], idx[(sx, sy, sz, 2)]])
    V = np.array(V, float)
    # orient faces outward
    F2 = []
    for f in F:
        p = V[f]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        if np.dot(n, p.mean(0)) < 0:
            f = f[::-1]
        F2.append(list(f))
    return V, F2


CBOX = chamfer_box()


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_axis(axis, a):
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s = math.cos(a), math.sin(a)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


# ----------------------------------------------------------------------------
# Shader node helpers
# ----------------------------------------------------------------------------
def _fix(sock, val):
    if sock.type == 'RGBA' and isinstance(val, (tuple, list)) and len(val) == 3:
        return tuple(val) + (1.0,)
    if sock.type == 'RGBA' and isinstance(val, (int, float)):
        return (val, val, val, 1.0)
    if sock.type == 'VECTOR' and isinstance(val, (int, float)):
        return (val, val, val)
    return val


class NT:
    """Tiny node-tree builder. Inputs may be sockets or constants."""

    def __init__(self, tree, clear=True):
        self.t = tree
        if clear:
            for n in list(tree.nodes):
                tree.nodes.remove(n)

    def _set(self, node, key, val):
        if val is None:
            return
        sock = node.inputs[key] if not isinstance(key, str) else self._find_in(node, key)
        if isinstance(val, bpy.types.NodeSocket):
            self.t.links.new(val, sock)
        else:
            sock.default_value = _fix(sock, val)

    @staticmethod
    def _find_in(node, name):
        for s in node.inputs:
            if s.name == name and s.enabled:
                return s
        return node.inputs[name]

    def node(self, typ, ins=None, **props):
        n = self.t.nodes.new(typ)
        for k, v in props.items():
            setattr(n, k, v)
        if ins:
            items = ins.items() if isinstance(ins, dict) else enumerate(ins)
            for k, v in items:
                self._set(n, k, v)
        return n

    # math
    def m(self, op, a, b=None, c=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self._set(n, i, v)
        return n.outputs[0]

    def vm(self, op, a, b=None, scale=None):
        n = self.node('ShaderNodeVectorMath', operation=op)
        if a is not None:
            self._set(n, 0, a)
        if b is not None:
            self._set(n, 1, b)
        if scale is not None:
            self._set(n, 'Scale', scale)
        if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE'):
            return n.outputs['Value']
        return n.outputs['Vector']

    def mix(self, fac, a, b, blend='MIX', dtype='RGBA', clamp=False):
        n = self.node('ShaderNodeMix', data_type=dtype, blend_type=blend, clamp_result=clamp)
        typ = {'RGBA': 'RGBA', 'FLOAT': 'VALUE', 'VECTOR': 'VECTOR'}[dtype]
        ins = [s for s in n.inputs if s.type == typ and s.name in ('A', 'B')]
        fac_s = [s for s in n.inputs if s.name == 'Factor' and s.enabled][0]
        for s, v in ((fac_s, fac), (ins[0], a), (ins[1], b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.t.links.new(v, s)
            else:
                s.default_value = _fix(s, v)
        return [s for s in n.outputs if s.type == typ][0]

    def ramp(self, fac, stops, interp='LINEAR'):
        n = self.node('ShaderNodeValToRGB')
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        for i, (p, col) in enumerate(stops):
            col = tuple(col) + ((1.0,) if len(col) == 3 else ())
            e = cr.elements[0] if i == 0 else cr.elements.new(p)
            e.position = p
            e.color = col
        self._set(n, 0, fac)
        return n.outputs['Color']

    def maprange(self, v, a0, a1, b0=0.0, b1=1.0, clamp=True, interp='LINEAR'):
        n = self.node('ShaderNodeMapRange', interpolation_type=interp, clamp=clamp)
        for k, val in zip(('Value', 'From Min', 'From Max', 'To Min', 'To Max'), (v, a0, a1, b0, b1)):
            self._set(n, k, val)
        return n.outputs['Result']

    def noise(self, vec, scale, detail=4.0, rough=0.5, dim='3D', distortion=0.0, lac=2.0,
              out='Fac', ntype='FBM'):
        n = self.node('ShaderNodeTexNoise', noise_dimensions=dim)
        try:
            n.noise_type = ntype
        except Exception:
            pass
        self._set(n, 'Vector', vec)
        self._set(n, 'Scale', scale)
        self._set(n, 'Detail', detail)
        self._set(n, 'Roughness', rough)
        self._set(n, 'Lacunarity', lac)
        self._set(n, 'Distortion', distortion)
        return n.outputs[out]

    def voronoi(self, vec, scale, feature='F1', dim='3D', rnd=1.0, out='Distance', detail=0.0):
        n = self.node('ShaderNodeTexVoronoi', voronoi_dimensions=dim, feature=feature)
        self._set(n, 'Vector', vec)
        self._set(n, 'Scale', scale)
        self._set(n, 'Randomness', rnd)
        if detail:
            self._set(n, 'Detail', detail)
        return n.outputs[out] if isinstance(out, str) else [n.outputs[o] for o in out]

    def xyz(self, x=0.0, y=0.0, z=0.0):
        n = self.node('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            self._set(n, i, v)
        return n.outputs[0]

    def sep(self, v):
        n = self.node('ShaderNodeSeparateXYZ')
        self._set(n, 0, v)
        return n.outputs

    def bump(self, height, strength=1.0, distance=0.02, normal=None):
        n = self.node('ShaderNodeBump')
        self._set(n, 'Height', height)
        self._set(n, 'Strength', strength)
        self._set(n, 'Distance', distance)
        if normal is not None:
            self._set(n, 'Normal', normal)
        return n.outputs['Normal']

    def hsv(self, col, h=0.5, s=1.0, v=1.0, fac=1.0):
        n = self.node('ShaderNodeHueSaturation')
        for k, val in (('Hue', h), ('Saturation', s), ('Value', v), ('Fac', fac), ('Color', col)):
            self._set(n, k, val)
        return n.outputs[0]

    def attr(self, name, out='Fac', atype='GEOMETRY'):
        n = self.node('ShaderNodeAttribute', attribute_name=name, attribute_type=atype)
        return n.outputs[out]

    def geo(self, out):
        return self.node('ShaderNodeNewGeometry').outputs[out]

    def texcoord(self, out):
        return self.node('ShaderNodeTexCoord').outputs[out]

    def objinfo(self, out):
        return self.node('ShaderNodeObjectInfo').outputs[out]

    def principled(self, **ins):
        mapping = {'base': 'Base Color', 'rough': 'Roughness', 'metal': 'Metallic',
                   'normal': 'Normal', 'spec': 'Specular IOR Level', 'trans': 'Transmission Weight',
                   'sss': 'Subsurface Weight', 'sss_r': 'Subsurface Radius', 'sss_s': 'Subsurface Scale',
                   'coat': 'Coat Weight', 'sheen': 'Sheen Weight', 'sheen_tint': 'Sheen Tint',
                   'emit': 'Emission Color', 'emit_s': 'Emission Strength', 'alpha': 'Alpha',
                   'ior': 'IOR', 'thin': 'Thin Wall', 'coat_r': 'Coat Roughness'}
        n = self.node('ShaderNodeBsdfPrincipled')
        for k, v in ins.items():
            self._set(n, mapping.get(k, k), v)
        return n.outputs[0]

    def out_material(self, shader, volume=None, displacement=None):
        n = self.node('ShaderNodeOutputMaterial', target='ALL')
        self._set(n, 'Surface', shader)
        if volume is not None:
            self._set(n, 'Volume', volume)
        if displacement is not None:
            self._set(n, 'Displacement', displacement)
        return n


def new_material(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    return m, NT(m.node_tree)


def srgb(r, g=None, b=None):
    """sRGB 0-255 (or 0-1) to linear tuple."""
    if g is None:
        r, g, b = r
    vals = []
    for c in (r, g, b):
        c = c / 255.0 if c > 1.0 else c
        vals.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(vals)
