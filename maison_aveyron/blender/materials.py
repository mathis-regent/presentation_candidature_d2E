"""Procedural PBR materials (no external textures needed)."""
import bpy
from lib import new_material, srgb

_cache = {}


def get(name):
    if name not in _cache:
        _cache[name] = globals()['mat_' + name]()
    return _cache[name]


def _wall_uv(s):
    """2D (u, z) coordinates on vertical faces, world-aligned."""
    P = s.geo('Position')
    N = s.geo('Normal')
    T = s.vm('NORMALIZE', s.vm('CROSS_PRODUCT', N, (0.0, 0.0, 1.0)))
    u = s.vm('DOT_PRODUCT', P, T)
    z = s.sep(P)[2]
    return s.xyz(u, z, 0.0), P


def mat_stone():
    """Coursed rubble limestone masonry with recessed lime pointing ('pierre vue')."""
    m, s = new_material('stone_wall')
    uv, P = _wall_uv(s)
    warp = s.noise(s.vm('MULTIPLY', uv, (1.6, 4.0, 1.0)), 1.0, detail=2.0, out='Color')
    warp = s.vm('SUBTRACT', warp, (0.5, 0.5, 0.5))
    # large coursed stones (~0.55 x 0.17 m) and small packing stones
    big_c = s.vm('ADD', s.vm('MULTIPLY', uv, (1 / 0.52, 1 / 0.165, 1.0)), s.vm('SCALE', warp, scale=0.7))
    small_c = s.vm('ADD', s.vm('MULTIPLY', uv, (1 / 0.24, 1 / 0.095, 1.0)), s.vm('SCALE', warp, scale=0.6))
    region = s.maprange(s.noise(s.vm('MULTIPLY', uv, (0.9, 1.6, 1.0)), 1.0, detail=3.0), 0.56, 0.60)
    vb = s.voronoi(big_c, 1.0, 'F1', '2D', rnd=0.9, out=['Color'])[0]
    eb = s.voronoi(big_c, 1.0, 'DISTANCE_TO_EDGE', '2D', rnd=0.9, out='Distance')
    vs = s.voronoi(small_c, 1.0, 'F1', '2D', rnd=0.9, out=['Color'])[0]
    es = s.voronoi(small_c, 1.0, 'DISTANCE_TO_EDGE', '2D', rnd=0.9, out='Distance')
    cell_col = s.mix(region, vb, vs)
    edge = s.mix(region, eb, s.m('MULTIPLY', es, 0.8), dtype='FLOAT')
    edge_n = s.m('ADD', edge, s.m('MULTIPLY', s.m('SUBTRACT', s.noise(P, 22.0, detail=3.0), 0.5), 0.07))
    stone_mask = s.maprange(edge_n, 0.03, 0.085)
    r = s.sep(cell_col)
    stone_col = s.ramp(r[0], [
        (0.00, srgb(182, 146, 98)),
        (0.15, srgb(204, 172, 124)),
        (0.30, srgb(160, 126, 84)),
        (0.45, srgb(214, 190, 146)),
        (0.60, srgb(150, 130, 104)),
        (0.74, srgb(178, 140, 90)),
        (0.88, srgb(196, 176, 140)),
        (1.00, srgb(170, 150, 120)),
    ])
    mott = s.noise(P, 5.0, detail=6.0, rough=0.62)
    stone_col = s.mix(s.maprange(mott, 0.3, 0.7), s.hsv(stone_col, v=0.80, s=1.1), s.hsv(stone_col, v=1.07, s=0.92))
    spk = s.maprange(s.noise(P, 70.0, detail=2.0), 0.64, 0.74)
    stone_col = s.mix(s.m('MULTIPLY', spk, 0.4), stone_col, srgb(86, 76, 62))
    lich = s.maprange(s.noise(P, 3.0, detail=4.0), 0.64, 0.7)
    stone_col = s.mix(s.m('MULTIPLY', lich, 0.35), stone_col, srgb(176, 172, 156))
    # mortar: recessed, slightly darker sandy lime; darker close to the stone edge (shadowed recess)
    mortar = s.mix(s.noise(P, 40.0, detail=2.0), srgb(150, 134, 108), srgb(120, 106, 84))
    recess = s.maprange(edge_n, 0.0, 0.035, 0.0, 1.0)
    mortar = s.mix(s.m('MULTIPLY', s.m('SUBTRACT', 1.0, recess), 0.5), mortar, srgb(70, 60, 48))
    col = s.mix(stone_mask, mortar, stone_col)
    z = s.sep(P)[2]
    grime = s.maprange(z, -0.2, 0.8, 0.6, 0.0)
    col = s.mix(grime, col, s.hsv(col, v=0.55, s=1.1))
    streak_n = s.noise(s.vm('MULTIPLY', P, (7.0, 7.0, 0.3)), 3.0, detail=3.0)
    streak = s.m('MULTIPLY', s.maprange(streak_n, 0.58, 0.78), 0.3)
    col = s.mix(streak, col, s.hsv(col, v=0.72))
    cell_h = s.m('MULTIPLY', r[1], 0.4)
    rock = s.noise(P, 12.0, detail=8.0, rough=0.62)
    h = s.m('ADD', s.m('MULTIPLY', stone_mask, s.m('ADD', 0.55, cell_h)),
            s.m('MULTIPLY', rock, s.m('MULTIPLY', stone_mask, 0.5)))
    nrm = s.bump(h, strength=0.9, distance=0.045)
    rough = s.mix(stone_mask, 0.97, s.maprange(rock, 0.3, 0.7, 0.8, 0.93), dtype='FLOAT')
    bsdf = s.principled(base=col, rough=rough, normal=nrm, spec=0.3)
    s.out_material(bsdf)
    return m


def mat_dressed():
    """Cut limestone (quoins, lintels, sills, surrounds)."""
    m, s = new_material('dressed_stone')
    P = s.geo('Position')
    rnd = s.attr('rnd')
    base = s.ramp(s.m('FRACT', s.m('MULTIPLY', rnd, 7.31)), [
        (0.0, srgb(184, 162, 124)), (0.5, srgb(196, 176, 140)), (1.0, srgb(170, 148, 110))])
    n1 = s.noise(P, 4.0, detail=6.0, rough=0.6)
    col = s.mix(s.maprange(n1, 0.35, 0.7), s.hsv(base, v=0.86), s.hsv(base, v=1.06, s=0.9))
    pits = s.maprange(s.noise(P, 90.0, detail=1.0), 0.6, 0.75)
    col = s.mix(s.m('MULTIPLY', pits, 0.35), col, srgb(120, 108, 88))
    z = s.sep(P)[2]
    col = s.mix(s.maprange(z, 0.0, 0.8, 0.5, 0.0), col, s.hsv(col, v=0.6))
    h = s.m('ADD', s.m('MULTIPLY', n1, 0.5), s.m('MULTIPLY', pits, -0.3))
    nrm = s.bump(h, strength=0.35, distance=0.01)
    s.out_material(s.principled(base=col, rough=0.86, normal=nrm, spec=0.35))
    return m


def mat_lauze():
    """Schist 'lauze' roof slabs with lichen."""
    m, s = new_material('lauze')
    P = s.geo('Position')
    rnd = s.attr('rnd')
    base = s.ramp(rnd, [
        (0.00, srgb(62, 60, 56)), (0.25, srgb(80, 75, 66)), (0.5, srgb(52, 51, 49)),
        (0.75, srgb(94, 87, 74)), (1.0, srgb(70, 66, 60))])
    n1 = s.noise(P, 7.0, detail=6.0, rough=0.6)
    col = s.mix(s.maprange(n1, 0.3, 0.7), s.hsv(base, v=0.78), s.hsv(base, v=1.12))
    # lichens: yellow-grey crust patches + pale spots
    li = s.noise(s.vm('ADD', P, s.xyz(s.m('MULTIPLY', rnd, 13.0))), 3.0, detail=5.0, rough=0.65)
    lichen_mask = s.maprange(li, 0.6, 0.7)
    col = s.mix(s.m('MULTIPLY', lichen_mask, 0.8), col, srgb(158, 136, 84))
    pale = s.maprange(s.noise(P, 22.0, detail=3.0), 0.7, 0.74)
    col = s.mix(s.m('MULTIPLY', pale, 0.6), col, srgb(170, 168, 156))
    moss = s.maprange(s.noise(P, 1.3, detail=3.0), 0.62, 0.72)
    col = s.mix(s.m('MULTIPLY', moss, 0.5), col, srgb(70, 78, 38))
    h = s.m('ADD', n1, s.m('MULTIPLY', lichen_mask, 0.25))
    nrm = s.bump(h, strength=0.5, distance=0.012)
    rough = s.mix(lichen_mask, 0.78, 0.92, dtype='FLOAT')
    s.out_material(s.principled(base=col, rough=rough, normal=nrm, spec=0.3))
    return m


def _oak(name, tone=1.0, axis='Z', weather=0.28):
    m, s = new_material(name)
    P = s.geo('Position')
    rnd = s.attr('rnd')
    if axis == 'Z':
        st = (28.0, 28.0, 1.2)
    elif axis == 'X':
        st = (1.2, 28.0, 28.0)
    else:
        st = (28.0, 1.2, 28.0)
    Pq = s.vm('ADD', P, s.xyz(s.m('MULTIPLY', rnd, 37.0), s.m('MULTIPLY', rnd, 11.0), 0.0))
    grain = s.noise(s.vm('MULTIPLY', Pq, st), 2.5, detail=8.0, rough=0.65, distortion=0.4)
    fine = s.noise(s.vm('MULTIPLY', Pq, (st[0] * 6, st[1] * 6, st[2] * 6)), 3.0, detail=3.0)
    base = s.ramp(s.m('FRACT', s.m('MULTIPLY', rnd, 5.7)), [
        (0.0, srgb(122, 92, 62)), (0.5, srgb(138, 104, 70)), (1.0, srgb(108, 80, 54))])
    base = s.hsv(base, v=tone)
    col = s.mix(s.maprange(grain, 0.35, 0.65), s.hsv(base, v=0.7, s=1.1), s.hsv(base, v=1.1, s=0.95))
    col = s.mix(s.m('MULTIPLY', s.maprange(fine, 0.5, 0.7), 0.4), col, s.hsv(col, v=0.75))
    # silver weathering
    wn = s.maprange(s.noise(P, 2.0, detail=4.0), 0.4, 0.7, 0.0, weather)
    col = s.mix(wn, col, srgb(150, 140, 126))
    h = s.m('ADD', grain, s.m('MULTIPLY', fine, 0.3))
    nrm = s.bump(h, strength=0.3, distance=0.004)
    s.out_material(s.principled(base=col, rough=0.62, normal=nrm, spec=0.4))
    return m


def mat_oak_v():
    return _oak('oak_vertical', axis='Z')


def mat_oak_x():
    return _oak('oak_x', axis='X')


def mat_oak_y():
    return _oak('oak_y', axis='Y')


def mat_frame_paint():
    m, s = new_material('frame_paint')
    P = s.geo('Position')
    n = s.noise(P, 30.0, detail=2.0)
    col = s.mix(s.m('MULTIPLY', n, 0.2), srgb(206, 204, 194), srgb(170, 168, 160))
    s.out_material(s.principled(base=col, rough=0.45, spec=0.5))
    return m


def mat_anthracite():
    m, s = new_material('anthracite_alu')
    s.out_material(s.principled(base=srgb(42, 43, 45), rough=0.38, metal=0.6, spec=0.5))
    return m


def mat_glass():
    """Architectural glass: transparent + Fresnel reflection (shadow-friendly)."""
    m, s = new_material('glass')
    lw = s.node('ShaderNodeLayerWeight', ins={'Blend': 0.12})
    fres = s.m('POWER', lw.outputs['Fresnel'], 1.3)
    fres = s.m('ADD', s.m('MULTIPLY', fres, 0.92), 0.06)
    tr = s.node('ShaderNodeBsdfTransparent', ins={'Color': (0.80, 0.84, 0.82, 1)})
    gl = s.node('ShaderNodeBsdfGlossy', ins={'Roughness': 0.015, 'Color': (0.95, 0.97, 0.98, 1)})
    mixs = s.node('ShaderNodeMixShader')
    s.t.links.new(fres, mixs.inputs[0])
    s.t.links.new(tr.outputs[0], mixs.inputs[1])
    s.t.links.new(gl.outputs[0], mixs.inputs[2])
    s.out_material(mixs.outputs[0])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m


def mat_plaster():
    m, s = new_material('plaster')
    P = s.geo('Position')
    n = s.noise(P, 3.0, detail=3.0)
    col = s.mix(s.m('MULTIPLY', n, 0.3), srgb(232, 226, 214), srgb(200, 192, 178))
    s.out_material(s.principled(base=col, rough=0.9))
    return m


def mat_floor():
    m, s = new_material('floor_oak')
    P = s.geo('Position')
    g = s.noise(s.vm('MULTIPLY', P, (1.0, 20.0, 1.0)), 3.0, detail=4.0)
    col = s.mix(g, srgb(150, 110, 72), srgb(120, 84, 52))
    s.out_material(s.principled(base=col, rough=0.35, spec=0.5))
    return m


def mat_fabric():
    m, s = new_material('fabric')
    s.out_material(s.principled(base=srgb(170, 160, 146), rough=0.95, sheen=0.4))
    return m


def mat_dark_wood():
    m, s = new_material('dark_wood')
    P = s.geo('Position')
    g = s.noise(s.vm('MULTIPLY', P, (20.0, 1.0, 20.0)), 3.0, detail=4.0)
    col = s.mix(g, srgb(58, 44, 34), srgb(44, 34, 26))
    s.out_material(s.principled(base=col, rough=0.75))
    return m


def mat_lamp():
    m, s = new_material('lamp_glow')
    em = s.node('ShaderNodeEmission', ins={'Color': (1.0, 0.72, 0.42, 1), 'Strength': 18.0})
    s.out_material(em.outputs[0])
    return m


def mat_black_metal():
    m, s = new_material('black_metal')
    s.out_material(s.principled(base=srgb(30, 30, 30), rough=0.5, metal=0.8))
    return m


def mat_gravel():
    m, s = new_material('gravel')
    P = s.geo('Position')
    cells = s.voronoi(P, 55.0, 'F1', '3D', out=['Distance', 'Color'])
    c2 = s.voronoi(P, 140.0, 'F1', '3D', out=['Distance', 'Color'])
    r = s.sep(cells[1])
    col = s.ramp(r[0], [(0.0, srgb(200, 188, 166)), (0.3, srgb(176, 164, 142)), (0.6, srgb(214, 204, 184)),
                       (0.85, srgb(150, 138, 118)), (1.0, srgb(190, 172, 140))])
    r2 = s.sep(c2[1])
    col = s.mix(s.m('MULTIPLY', s.m('GREATER_THAN', r2[1], 0.55), 0.6), col,
                s.ramp(r2[0], [(0, srgb(170, 160, 140)), (1, srgb(220, 212, 196))]))
    dirt = s.maprange(s.noise(P, 1.5, detail=5.0), 0.45, 0.75, 0.0, 0.6)
    col = s.mix(dirt, col, srgb(130, 112, 86))
    h = s.m('ADD', s.m('MULTIPLY', s.m('SUBTRACT', 1.0, cells[0]), 0.7), s.m('MULTIPLY', s.m('SUBTRACT', 1.0, c2[0]), 0.4))
    nrm = s.bump(h, strength=0.9, distance=0.02)
    s.out_material(s.principled(base=col, rough=0.9, normal=nrm, spec=0.3))
    return m


def mat_flagstone():
    m, s = new_material('flagstone')
    P = s.geo('Position')
    rnd = s.attr('rnd')
    base = s.ramp(rnd, [(0, srgb(196, 182, 156)), (0.5, srgb(214, 202, 178)), (1, srgb(180, 164, 136))])
    n = s.noise(P, 3.0, detail=6.0)
    col = s.mix(s.maprange(n, 0.3, 0.7), s.hsv(base, v=0.85), s.hsv(base, v=1.05))
    nrm = s.bump(n, strength=0.25, distance=0.01)
    s.out_material(s.principled(base=col, rough=0.8, normal=nrm, spec=0.35))
    return m


def mat_drystone():
    """Grey-beige Causse limestone for dry-stone walls, with lichen."""
    m, s = new_material('drystone')
    P = s.geo('Position')
    rnd = s.attr('rnd')
    base = s.ramp(rnd, [(0.0, srgb(170, 162, 146)), (0.3, srgb(190, 178, 156)), (0.55, srgb(150, 142, 128)),
                       (0.8, srgb(200, 190, 170)), (1.0, srgb(160, 146, 122))])
    n1 = s.noise(P, 6.0, detail=7.0, rough=0.62)
    col = s.mix(s.maprange(n1, 0.3, 0.7), s.hsv(base, v=0.72), s.hsv(base, v=1.08))
    li = s.maprange(s.noise(P, 4.0, detail=4.0), 0.58, 0.68)
    col = s.mix(s.m('MULTIPLY', li, 0.7), col, srgb(176, 172, 150))
    li2 = s.maprange(s.noise(P, 9.0, detail=3.0), 0.64, 0.7)
    col = s.mix(s.m('MULTIPLY', li2, 0.6), col, srgb(120, 120, 60))
    moss = s.maprange(s.noise(P, 2.0, detail=3.0), 0.6, 0.7)
    N = s.geo('Normal')
    up = s.maprange(s.sep(N)[2], 0.3, 0.9)
    col = s.mix(s.m('MULTIPLY', s.m('MULTIPLY', moss, up), 0.8), col, srgb(64, 74, 30))
    nrm = s.bump(n1, strength=0.6, distance=0.02)
    s.out_material(s.principled(base=col, rough=0.9, normal=nrm, spec=0.3))
    return m


def mat_bark():
    m, s = new_material('bark')
    P = s.geo('Position')
    n = s.noise(s.vm('MULTIPLY', P, (6.0, 6.0, 1.2)), 3.0, detail=8.0, rough=0.65, distortion=0.6)
    c = s.voronoi(s.vm('MULTIPLY', P, (5.0, 5.0, 1.5)), 3.0, 'DISTANCE_TO_EDGE', '3D', out='Distance')
    cr = s.maprange(c, 0.0, 0.12)
    col = s.mix(s.maprange(n, 0.3, 0.7), srgb(56, 50, 44), srgb(104, 98, 88))
    col = s.mix(s.m('MULTIPLY', s.m('SUBTRACT', 1.0, cr), 0.8), col, srgb(30, 26, 22))
    li = s.maprange(s.noise(P, 3.0, detail=3.0), 0.6, 0.7)
    col = s.mix(s.m('MULTIPLY', li, 0.6), col, srgb(120, 128, 90))
    h = s.m('ADD', s.m('MULTIPLY', cr, 0.6), s.m('MULTIPLY', n, 0.5))
    nrm = s.bump(h, strength=0.9, distance=0.03)
    s.out_material(s.principled(base=col, rough=0.92, normal=nrm, spec=0.25))
    return m


def _leaf(name, cols, trans=0.35):
    m, s = new_material(name)
    rnd = s.attr('rnd')
    rnd2 = s.m('FRACT', s.m('MULTIPLY', rnd, 13.7))
    col = s.ramp(rnd, cols)
    col = s.hsv(col, v=s.maprange(rnd2, 0, 1, 0.75, 1.15))
    P = s.geo('Position')
    patch = s.maprange(s.noise(P, 0.35, detail=2.0), 0.3, 0.7, 0.85, 1.15)
    col = s.hsv(col, v=patch)
    diff = s.principled(base=col, rough=0.55, spec=0.35, sheen=0.0)
    tr = s.node('ShaderNodeBsdfTranslucent', ins={'Color': s.hsv(col, s=1.25, v=1.3)})
    mx = s.node('ShaderNodeMixShader', ins={0: trans})
    s.t.links.new(diff, mx.inputs[1])
    s.t.links.new(tr.outputs[0], mx.inputs[2])
    s.out_material(mx.outputs[0])
    return m


def mat_leaf_oak():
    return _leaf('leaf_oak', [(0.0, srgb(52, 70, 22)), (0.4, srgb(64, 84, 28)), (0.75, srgb(78, 92, 30)),
                              (0.93, srgb(110, 104, 36)), (1.0, srgb(140, 110, 40))])


def mat_leaf_chestnut():
    return _leaf('leaf_chestnut', [(0.0, srgb(58, 80, 24)), (0.5, srgb(76, 98, 30)), (0.85, srgb(96, 110, 34)),
                                   (1.0, srgb(150, 124, 44))])


def mat_leaf_far():
    return _leaf('leaf_far', [(0.0, srgb(44, 60, 22)), (0.5, srgb(58, 76, 26)), (1.0, srgb(80, 92, 34))], trans=0.25)


def mat_vine():
    return _leaf('leaf_vine', [(0.0, srgb(70, 96, 30)), (0.6, srgb(92, 112, 36)), (1.0, srgb(130, 120, 40))])


def mat_lavender():
    return _leaf('lavender', [(0.0, srgb(98, 110, 80)), (0.45, srgb(116, 124, 92)), (0.55, srgb(118, 96, 156)),
                              (0.8, srgb(96, 78, 140)), (1.0, srgb(132, 110, 170))], trans=0.2)
