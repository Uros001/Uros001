"""Shared helpers for the Pemmican 1814 Blender scenes (Blender 5.2 bpy module, Cycles CPU).

Every scene script builds its scene procedurally (no external assets), so the
.blend files saved next to the renders are fully reproducible.
"""
import math, random
import bpy
from mathutils import Vector, Euler

FPS = 30


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = FPS
    return scn


def render_settings(scn, res=(1920, 1080), samples=24, frames=(1, 1), mist=None, motion_blur=False,
                    bounces=4, threshold=0.03):
    scn.render.engine = 'CYCLES'
    c = scn.cycles
    c.device = 'CPU'
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = threshold
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.max_bounces = bounces
    c.diffuse_bounces = 2
    c.glossy_bounces = 2
    c.transmission_bounces = 4
    c.volume_bounces = 0
    c.transparent_max_bounces = 8
    c.sample_clamp_indirect = 4.0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    scn.render.use_persistent_data = True
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.frame_start, scn.frame_end = frames
    scn.render.use_motion_blur = motion_blur
    scn.render.motion_blur_shutter = 0.4
    scn.view_settings.view_transform = 'AgX'
    try:
        scn.view_settings.look = 'AgX - Base Contrast'
    except TypeError:
        pass
    scn.render.image_settings.file_format = 'PNG'
    scn.render.image_settings.color_mode = 'RGB'
    scn.render.image_settings.color_depth = '8'
    if mist:
        vl = scn.view_layers[0]
        vl.use_pass_mist = True
        scn.world.mist_settings.start = mist[0]
        scn.world.mist_settings.depth = mist[1]
        scn.world.mist_settings.falloff = 'QUADRATIC'


def node(nt, typ, loc=(0, 0), **kw):
    n = nt.nodes.new(typ)
    n.location = loc
    for k, v in kw.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
        else:
            setattr(n, k, v)
    return n


def link(nt, a, b):
    nt.links.new(a, b)


def mat_new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = node(nt, 'ShaderNodeOutputMaterial', (900, 0))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled', (600, 0))
    link(nt, bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m, nt, bsdf, out


def color_ramp(nt, stops, loc=(0, 0)):
    r = node(nt, 'ShaderNodeValToRGB', loc)
    cr = r.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = cr.elements.new(p)
        e.color = (*c, 1)
    return r


def srgb(h):
    """Hex -> linear RGB tuple."""
    h = h.lstrip('#')
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in v)


def sky_world(scn, sun_elev_deg=4.0, sun_rot_deg=180.0, strength=1.0, air=1.0, dust=1.0, ozone=1.0,
              tint=None, tint_mix=0.0):
    w = bpy.data.worlds.new('World')
    scn.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = node(nt, 'ShaderNodeOutputWorld', (600, 0))
    bg = node(nt, 'ShaderNodeBackground', (400, 0))
    sky = node(nt, 'ShaderNodeTexSky', (0, 0))
    try:
        sky.sky_type = 'NISHITA'
    except TypeError:
        sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    for attr, val in (('air_density', air), ('dust_density', dust), ('ozone_density', ozone)):
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    if hasattr(sky, 'sun_disc'):
        sky.sun_disc = True
    src = sky.outputs['Color']
    if tint is not None and tint_mix > 0:
        mix = node(nt, 'ShaderNodeMix', (200, 0), data_type='RGBA', blend_type='MULTIPLY')
        mix.inputs['Factor'].default_value = tint_mix
        link(nt, src, mix.inputs[6])
        mix.inputs[7].default_value = (*tint, 1)
        src = mix.outputs[2]
    link(nt, src, bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    link(nt, bg.outputs['Background'], out.inputs['Surface'])
    return w, sky


def flat_world(scn, color, strength=1.0):
    w = bpy.data.worlds.new('World')
    scn.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background') or w.node_tree.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength
    return w


def sun(name='Sun', elev=5, azim=180, strength=3.0, color=(1, 0.85, 0.7), angle=1.0):
    d = bpy.data.lights.new(name, 'SUN')
    d.energy = strength
    d.color = color
    d.angle = math.radians(angle)
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    # Blender sun points down -Z; rotate so light travels from azimuth/elevation toward origin.
    o.rotation_euler = Euler((math.radians(90 - elev), 0, math.radians(azim + 180)), 'XYZ')
    return o


def area_light(name, loc, rot, size, energy, color=(1, 1, 1), shape='RECTANGLE', size_y=None):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.color = color
    d.shape = shape
    d.size = size
    if size_y:
        d.size_y = size_y
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    return o


def point_light(name, loc, energy, color=(1, 0.6, 0.3), radius=0.05):
    d = bpy.data.lights.new(name, 'POINT')
    d.energy = energy
    d.color = color
    d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    return o


def camera(name='Cam', lens=35, fstop=None, focus_obj=None, focus_dist=None, sensor=36):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    c.sensor_width = sensor
    c.clip_start = 0.02
    c.clip_end = 5000
    if fstop:
        c.dof.use_dof = True
        c.dof.aperture_fstop = fstop
        if focus_obj:
            c.dof.focus_object = focus_obj
        if focus_dist:
            c.dof.focus_distance = focus_dist
    o = bpy.data.objects.new(name, c)
    bpy.context.collection.objects.link(o)
    bpy.context.scene.camera = o
    return o


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def keyframe_path(cam, keys, target_keys=None, interp='BEZIER', ease=True):
    """keys: list of (frame, (x,y,z)); target_keys: list of (frame, (x,y,z)) points to look at."""
    for f, p in keys:
        cam.location = p
        cam.keyframe_insert('location', frame=f)
    if target_keys:
        tgt = bpy.data.objects.new(cam.name + '_tgt', None)
        bpy.context.collection.objects.link(tgt)
        for f, p in target_keys:
            tgt.location = p
            tgt.keyframe_insert('location', frame=f)
        con = cam.constraints.new('TRACK_TO')
        con.target = tgt
        con.track_axis = 'TRACK_NEGATIVE_Z'
        con.up_axis = 'UP_Y'
    for obj in [cam] + ([tgt] if target_keys else []):
        if obj.animation_data and obj.animation_data.action:
            set_interp(obj.animation_data.action, interp)
    return tgt if target_keys else None


def _fcurves(action):
    """Blender 5.x layered actions keep fcurves in channelbags; fall back to legacy action.fcurves."""
    if hasattr(action, 'fcurves') and len(getattr(action, 'fcurves', [])):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for cb in getattr(strip, 'channelbags', []):
                out.extend(cb.fcurves)
    return out


def set_interp(action, interp='BEZIER'):
    for fc in _fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.easing = 'AUTO'


def add_handheld(obj, strength=0.004, scale=60, seed=1):
    """Subtle organic camera drift via noise modifiers on rotation (radians)."""
    if not obj.animation_data or not obj.animation_data.action:
        obj.rotation_euler = obj.rotation_euler
        obj.keyframe_insert('rotation_euler', frame=1)
    obj.keyframe_insert('rotation_euler', frame=1)
    for fc in _fcurves(obj.animation_data.action):
        if fc.data_path == 'rotation_euler':
            m = fc.modifiers.new('NOISE')
            m.strength = strength
            m.scale = scale
            m.phase = seed * 13.7 + fc.array_index * 41.3


def obj_from_bmesh(name, bm, mat=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if mat:
        o.data.materials.append(mat)
    return o


def shade_smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def add_subsurf(o, levels=2, render=None):
    m = o.modifiers.new('Subsurf', 'SUBSURF')
    m.levels = levels
    m.render_levels = render if render is not None else levels
    return m


def mist_compositor(scn, fog_color, gamma=1.0, strength=1.0, glare=None, blur_fog=0.0, blur_px=180,
                    sky_keep=0.0):
    """Composite fog over the render using the mist pass (cheap stand-in for volumetrics).

    blur_fog: 0..1 — how much the fog colour is taken from a heavily blurred copy of the
    render instead of the flat fog_color (keeps sky gradients / sun glow in the haze).
    sky_keep: 0..1 — reduce fog on pure background (alpha==0 requires film_transparent; unused).
    Blender 5.x compositor: CompositorNodeTree on scene.compositing_node_group.
    """
    scn.render.use_compositing = True
    nt = bpy.data.node_groups.new('Comp', 'CompositorNodeTree')
    scn.compositing_node_group = nt
    nt.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = nt.nodes.new('CompositorNodeRLayers'); rl.location = (0, 0)
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.location = (250, -250)
    pw.inputs[1].default_value = gamma
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.location = (450, -250)
    mul.inputs[1].default_value = strength
    mul.use_clamp = True
    nt.links.new(rl.outputs['Mist'], pw.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[0])
    fogsrc = None
    if blur_fog > 0:
        bl = nt.nodes.new('CompositorNodeBlur'); bl.location = (250, 250)
        sx = blur_px * scn.render.resolution_x / 1920.0
        bl.inputs['Size'].default_value = (sx, sx)
        clampn = nt.nodes.new('ShaderNodeVectorMath'); clampn.operation = 'MINIMUM'; clampn.location = (100, 250)
        clampn.inputs[1].default_value = (2.5, 2.5, 2.5)
        nt.links.new(rl.outputs['Image'], clampn.inputs[0])
        nt.links.new(clampn.outputs['Vector'], bl.inputs['Image'])
        fm = nt.nodes.new('ShaderNodeMix'); fm.data_type = 'RGBA'; fm.location = (450, 250)
        fm.inputs['Factor'].default_value = blur_fog
        fm.inputs[6].default_value = (*fog_color, 1)
        nt.links.new(bl.outputs[0], fm.inputs[7])
        fogsrc = fm.outputs[2]
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.location = (650, 0)
    nt.links.new(mul.outputs[0], mix.inputs['Factor'])
    nt.links.new(rl.outputs['Image'], mix.inputs[6])
    if fogsrc is not None:
        nt.links.new(fogsrc, mix.inputs[7])
    else:
        mix.inputs[7].default_value = (*fog_color, 1)
    last = mix.outputs[2]
    out = nt.nodes.new('NodeGroupOutput'); out.location = (1100, 0)
    nt.links.new(last, out.inputs[0])
    return nt


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)


def world_volume(world, density=0.003, anisotropy=0.6, color=(0.85, 0.88, 0.92)):
    """Thin homogeneous haze in the world volume: affects reflections and gives a sun halo."""
    nt = world.node_tree
    out = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputWorld'][0]
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    vs.location = (400, -250)
    vs.inputs['Density'].default_value = density
    vs.inputs['Anisotropy'].default_value = anisotropy
    vs.inputs['Color'].default_value = (*color, 1)
    nt.links.new(vs.outputs[0], out.inputs['Volume'])
    return vs


def mat_hair(name='Hair', melanin=0.86, redness=0.55, rough=0.38):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (400, 0)
    h = nt.nodes.new('ShaderNodeBsdfHairPrincipled'); h.location = (100, 0)
    try:
        h.parametrization = 'MELANIN'
    except Exception:
        pass
    for k, v in (('Melanin', melanin), ('Melanin Redness', redness), ('Roughness', rough),
                 ('Radial Roughness', 0.45), ('Coat', 0.05), ('Random Color', 0.25), ('Random Roughness', 0.2)):
        if k in h.inputs:
            h.inputs[k].default_value = v
    nt.links.new(h.outputs[0], out.inputs['Surface'])
    return m


def add_fur(obj, hair_mat, density=150000.0, length=0.022, radius=0.00045, mask_scale=3.0,
            mask_threshold=0.45, comb=(0.15, -0.3, -1.0), frizz=0.5, seed=0):
    """Patchy short fur as geometry-nodes curves (rendered natively as hair by Cycles)."""
    ng = bpy.data.node_groups.new(obj.name + '_fur', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes.new
    L = ng.links.new
    gi = N('NodeGroupInput'); gi.location = (-1400, 0)
    go = N('NodeGroupOutput'); go.location = (1400, 0)
    pos = N('GeometryNodeInputPosition'); pos.location = (-1400, -300)
    nz = N('ShaderNodeTexNoise'); nz.location = (-1200, -300)
    nz.inputs['Scale'].default_value = mask_scale; nz.inputs['Detail'].default_value = 4.0
    L(pos.outputs['Position'], nz.inputs['Vector'])
    cmp = N('FunctionNodeCompare'); cmp.location = (-1000, -300)
    cmp.data_type = 'FLOAT'; cmp.operation = 'GREATER_THAN'
    L(nz.outputs['Factor'], cmp.inputs['A']); cmp.inputs['B'].default_value = mask_threshold
    dist = N('GeometryNodeDistributePointsOnFaces'); dist.location = (-800, 0)
    dist.distribute_method = 'RANDOM'
    dist.inputs['Density'].default_value = density
    dist.inputs['Seed'].default_value = seed
    L(gi.outputs[0], dist.inputs['Mesh']); L(cmp.outputs['Result'], dist.inputs['Selection'])
    line = N('GeometryNodeCurvePrimitiveLine'); line.location = (-800, -300)
    line.inputs['Start'].default_value = (0, 0, 0); line.inputs['End'].default_value = (0, 0, 1)
    rnd = N('FunctionNodeRandomValue'); rnd.location = (-800, -500); rnd.data_type = 'FLOAT'
    for i in rnd.inputs:
        if i.name == 'Min' and i.type == 'VALUE':
            i.default_value = length * 0.55
        if i.name == 'Max' and i.type == 'VALUE':
            i.default_value = length
    rv = [o for o in rnd.outputs if o.type == 'VALUE'][0]
    inst = N('GeometryNodeInstanceOnPoints'); inst.location = (-550, 0)
    L(dist.outputs['Points'], inst.inputs['Points']); L(line.outputs['Curve'], inst.inputs['Instance'])
    L(dist.outputs['Rotation'], inst.inputs['Rotation']); L(rv, inst.inputs['Scale'])
    real = N('GeometryNodeRealizeInstances'); real.location = (-350, 0)
    L(inst.outputs['Instances'], real.inputs['Geometry'])
    res = N('GeometryNodeResampleCurve'); res.location = (-150, 0)
    res.inputs['Count'].default_value = 6
    L(real.outputs['Geometry'], res.inputs['Curve'])
    sp = N('GeometryNodeSplineParameter'); sp.location = (-150, -300)
    pos2 = N('GeometryNodeInputPosition'); pos2.location = (-150, -500)
    fz = N('ShaderNodeTexNoise'); fz.location = (50, -500)
    fz.inputs['Scale'].default_value = 90.0; fz.inputs['Detail'].default_value = 2.0
    L(pos2.outputs['Position'], fz.inputs['Vector'])
    sub = N('ShaderNodeVectorMath'); sub.location = (250, -500); sub.operation = 'SUBTRACT'
    L(fz.outputs['Color'], sub.inputs[0]); sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    sq = N('ShaderNodeMath'); sq.location = (50, -300); sq.operation = 'POWER'; sq.inputs[1].default_value = 1.6
    L(sp.outputs['Factor'], sq.inputs[0])
    fs = N('ShaderNodeMath'); fs.location = (250, -300); fs.operation = 'MULTIPLY'; fs.inputs[1].default_value = length * frizz
    L(sq.outputs[0], fs.inputs[0])
    sc1 = N('ShaderNodeVectorMath'); sc1.location = (450, -500); sc1.operation = 'SCALE'
    L(sub.outputs['Vector'], sc1.inputs[0]); L(fs.outputs[0], sc1.inputs['Scale'])
    cs = N('ShaderNodeMath'); cs.location = (250, -150); cs.operation = 'MULTIPLY'; cs.inputs[1].default_value = length * 0.7
    L(sq.outputs[0], cs.inputs[0])
    sc2 = N('ShaderNodeVectorMath'); sc2.location = (450, -250); sc2.operation = 'SCALE'
    sc2.inputs[0].default_value = comb
    L(cs.outputs[0], sc2.inputs['Scale'])
    add = N('ShaderNodeVectorMath'); add.location = (650, -350); add.operation = 'ADD'
    L(sc1.outputs['Vector'], add.inputs[0]); L(sc2.outputs['Vector'], add.inputs[1])
    setp = N('GeometryNodeSetPosition'); setp.location = (650, 0)
    L(res.outputs['Curve'], setp.inputs['Geometry']); L(add.outputs['Vector'], setp.inputs['Offset'])
    rad = N('GeometryNodeSetCurveRadius'); rad.location = (850, 0)
    rad.inputs['Radius'].default_value = radius
    L(setp.outputs['Geometry'], rad.inputs['Curve'])
    sm = N('GeometryNodeSetMaterial'); sm.location = (1050, 0)
    sm.inputs['Material'].default_value = hair_mat
    L(rad.outputs['Curve'], sm.inputs['Geometry'])
    jn = N('GeometryNodeJoinGeometry'); jn.location = (1250, 0)
    L(gi.outputs[0], jn.inputs['Geometry']); L(sm.outputs['Geometry'], jn.inputs['Geometry'])
    L(jn.outputs['Geometry'], go.inputs[0])
    mod = obj.modifiers.new('Fur', 'NODES')
    mod.node_group = ng
    if hair_mat.name not in [m.name for m in obj.data.materials if m]:
        obj.data.materials.append(hair_mat)
    return mod


def add_fur_curves(obj, hair_mat, density=120000.0, length=0.022, radius=0.0005, mask_scale=3.0,
                   mask_threshold=0.45, comb=(0.15, -0.3, -1.0), frizz=0.5, seed=0, points=6,
                   max_strands=250000, curl=0.35, soft=0.08, comb_var=0.6, length_fn=None):
    """Fur as a native Curves object (Cycles in this bpy build renders native curves only).

    Samples the *evaluated* surface of `obj` (area-weighted). A smooth 3D noise mask with a soft
    edge (`soft`) thins the hair into worn patches. Strands grow along the normal, bent by a
    matting direction (`comb`, varied regionally by `comb_var`), with per-strand curl and frizz.
    """
    import numpy as np
    from mathutils import noise as mnoise
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = obj.matrix_world
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    co = (np.c_[co, np.ones(nv)] @ np.array(mw).T)[:, :3]
    nt = len(me.loop_triangles)
    tri = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', tri); tri = tri.reshape(-1, 3)
    ev.to_mesh_clear()
    a, b, c = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    cr = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    nrm = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    rng = np.random.default_rng(seed)
    n = int(min(max_strands * 3, area.sum() * density))
    idx = rng.choice(nt, size=n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    root = a[idx] + (b[idx] - a[idx]) * u[:, None] + (c[idx] - a[idx]) * v[:, None]
    N = nrm[idx]
    ofs = np.array(obj.location)
    q = (root - ofs) * mask_scale + seed * 7.1
    mv = np.array([mnoise.noise(Vector(p)) for p in q]) * 0.5 + 0.5
    prob = np.clip((mv - (mask_threshold - soft)) / (2 * soft), 0, 1)
    sel = rng.random(len(prob)) < prob
    root, N = root[sel], N[sel]
    if len(root) > max_strands:
        pick = rng.choice(len(root), max_strands, replace=False)
        root, N = root[pick], N[pick]
    m = len(root)
    L = length * rng.uniform(0.45, 1.0, m)
    if length_fn is not None:
        L = L * np.array([length_fn(r) for r in root], np.float32)
    # regional matting direction
    base = np.array(comb, np.float32); base /= np.linalg.norm(base)
    q2 = (root - ofs) * (mask_scale * 0.6)
    cv = np.array([mnoise.noise_vector(Vector(p)) for p in q2], np.float32)
    combv = base[None] + cv * comb_var
    combv -= N * np.sum(combv * N, axis=1, keepdims=True) * 0.6   # lie along the surface
    combv /= np.maximum(np.linalg.norm(combv, axis=1, keepdims=True), 1e-6)
    # curl basis
    t1 = np.cross(N, np.array([0.31, 0.57, 0.76], np.float32)); t1 /= np.maximum(np.linalg.norm(t1, axis=1, keepdims=True), 1e-6)
    t2 = np.cross(N, t1)
    ph = rng.uniform(0, 6.283, m); w = rng.uniform(5.0, 9.0, m)
    fr = rng.normal(0, 1, (m, 3)) * frizz
    t = np.linspace(0, 1, points)
    pos = np.empty((m, points, 3), np.float32)
    for k, tk in enumerate(t):
        bend = tk ** 1.4
        cur = (t1 * np.cos(ph + w * tk)[:, None] + t2 * np.sin(ph + w * tk)[:, None]) * (curl * L * tk)[:, None]
        pos[:, k] = root + N * (L * tk * 0.55)[:, None] + (combv * 0.85 + fr * 0.3) * (L * bend)[:, None] + cur
    rad = np.repeat((radius * (1.0 - 0.7 * t))[None], m, 0).astype(np.float32)
    hc = bpy.data.hair_curves.new(obj.name + '_fur')
    hc.add_curves([points] * m)
    hc.attributes['position'].data.foreach_set('vector', pos.reshape(-1))
    rattr = hc.attributes.get('radius') or hc.attributes.new('radius', 'FLOAT', 'POINT')
    rattr.data.foreach_set('value', rad.reshape(-1))
    hc.materials.append(hair_mat)
    ho = bpy.data.objects.new(obj.name + '_fur', hc)
    bpy.context.scene.collection.objects.link(ho)
    print(f'fur: {m} strands on {obj.name}', flush=True)
    return ho
