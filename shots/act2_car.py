"""ACT II - ASSEMBLY. One script, --shot 2A..2G (plus LOOK lookdev cameras on frames 1..4)."""
import sys, os, json, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import car as CAR
import act2lib as A
from mathutils import Vector, Matrix, Euler, Quaternion

SHOT = arg('--shot', '2F')
SL = {s['id']: s for s in json.load(open(os.path.join(FILM, 'shotlist.json')))['shots']}
info = SL.get(SHOT, {'render_frames': 48, 'cut_in_local': 7, 'cut_out_local': 42})
NF = info['render_frames']
CIN = info['cut_in_local']

import time as _t; T0 = _t.time()
reset()
setup_render(1, NF, samples=32, vol_tile='8', vol_samples=32, vol_end=120.0, shutter=0.5,
             look='AgX - Medium High Contrast')
bpy.context.scene.eevee.shadow_ray_count = 1
bpy.context.scene.eevee.shadow_step_count = 6
try:
    bpy.context.scene.eevee.shadow_pool_size = '1024'     # "Shadow buffer full (4800/2048)" with the voxel room
except Exception:
    pass


def emit_sock(mat):
    """Animatable emission master of a material (mat_strip exposes a 'Master' value node)."""
    n = mat.node_tree.nodes.get('Master')
    if n is not None:
        return n.outputs[0]
    return mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
compositor(bloom=0.45, threshold=1.2, bloom_size=0.7, dispersion=0.004)
sc = bpy.context.scene

coll = collection('act2')
VOXEL = SHOT == '2G'
if VOXEL:
    SUN = A.sun_vector(float(arg('--sunel', 4.0, float)), float(arg('--sunaz', 0.0, float)))
    WORLD = A.world_dusk2(SUN, strength=1.0)
else:
    world_color((0.0015, 0.0018, 0.0022), 1.0)
S = A.build_studio(coll, voxel=VOXEL, cube=float(arg('--cube', 0.3, float)))   # r3: 0.3 m chunks (0.14 read as glitter)
print('[time] studio %.1fs' % (_t.time() - T0))
car = CAR.build_car(coll, 'Car')
print('[time] car %.1fs' % (_t.time() - T0))
P = car['parts']
ROOT = car['root']
A.probes(coll)
fx = collection('fx')

# r3: light linking - the rim / door-spill keys light ONLY the car (their speculars mirrored in the wet floor
# as hard white/cream cards; with specular 0 the graphite paint lost all shape)
CAR_RECV = bpy.data.collections.new('car_recv')
def _car_objs(o):
    yield o
    for ch in o.children:
        yield from _car_objs(ch)
for o_ in _car_objs(ROOT):
    if o_.type == 'MESH':
        CAR_RECV.objects.link(o_)


def car_only(L_, spec=1.0):
    try:
        L_.light_linking.receiver_collection = CAR_RECV
        L_.data.specular_factor = spec
    except Exception as e:
        print('[light-link] failed', e)
    return L_


for L_ in S.get('rims', []) + [S['door_spill']]:
    car_only(L_)


# ============================================================================ helpers

def cam_rig(name, loc, target, lens=35, fstop=2.8, focus_obj=True):
    tgt = empty(name + '_tgt', target, coll)
    c = camera(name, loc, None, lens=lens, fstop=fstop)
    track_to(c, tgt)
    if focus_obj:
        c.data.dof.focus_object = tgt
    return c, tgt


def lights_on(strength_r=9, strength_f=6, frame=1):     # client rule 2: practicals at moderate intensity
    CAR.set_light(car, 'rear', strength_r, frame, spill=strength_r * 1.6)
    CAR.set_light(car, 'front', strength_f, frame, spill=strength_f * 0.5)


def hull_from(f_on):
    """The inner gap-blocker hull must not show while the panels are exploded."""
    h = P.get('inner_hull')
    if h is None:
        return
    for f, s in ((1, 0.0), (max(1, f_on - 1), 0.0), (f_on, 1.0)):
        h.scale = (s, s, s); h.keyframe_insert('scale', frame=f)
    set_interp(h, 'CONSTANT', path='scale')


def lights_off(frame=1):
    CAR.set_light(car, 'rear', 0.0, frame, spill=0.0)
    CAR.set_light(car, 'front', 0.0, frame, spill=0.0)


def ease_io(t, p=3.0):
    t = max(0.0, min(1.0, t))
    return t ** p / (t ** p + (1 - t) ** p)


def key_path(o, fn, f0, f1, path='location', step=1):
    for f in range(f0, f1 + 1, step):
        setattr(o, path, fn(f))
        o.keyframe_insert(path, frame=f)
    set_interp(o, 'LINEAR', path=path)


def world_pt(local):
    return ROOT.matrix_world @ Vector(local)


# ---------------------------------------------------------------- exploded view
SLAMS = [18, 30, 42, 54, 66]     # local frames in 2B (cut frames 12/24/36/48/60)
EXPLODE = {
    # name: (group, offset, rot_deg)
    'tub': (0, (0, 0.0, 0.35), (0, 0, 0)), 'engine': (0, (0, -0.7, 1.05), (-10, 0, 6)),
    'susp_FL': (0, (-0.7, 0.4, 0.5), (0, 0, -10)), 'susp_FR': (0, (0.7, 0.4, 0.5), (0, 0, 10)),
    'susp_RL': (0, (-0.7, -0.4, 0.5), (0, 0, 10)), 'susp_RR': (0, (0.7, -0.4, 0.5), (0, 0, -10)),
    'corner_FL': (1, (-1.9, 0.3, 0.2), (0, 0, 0)), 'corner_FR': (1, (1.9, 0.3, 0.2), (0, 0, 0)),
    'corner_RL': (1, (-1.9, -0.3, 0.2), (0, 0, 0)), 'corner_RR': (1, (1.9, -0.3, 0.2), (0, 0, 0)),
    'body': (2, (0, 0, 2.1), (0, 3, 0)), 'nose': (2, (0, 2.1, 1.55), (-12, 0, 0)), 'tail': (2, (0, -2.3, 1.85), (10, 0, 0)),
    'door_L': (2, (-1.7, 0.2, 1.5), (0, -25, 0)), 'door_R': (2, (1.7, 0.2, 1.5), (0, 25, 0)),
    'canopy': (3, (0, 0.3, 3.1), (6, 0, 0)), 'buttresses': (3, (0, -0.7, 2.7), (-6, 0, 0)), 'wing': (3, (0, -1.9, 2.9), (14, 0, 0)),
    'diffuser': (3, (0, -1.7, 0.25), (-10, 0, 0)), 'splitter': (3, (0, 1.6, 0.05), (0, 0, 0)), 'louvres': (3, (0, -0.4, 1.9), (0, 0, 0)),
    'side_vents': (3, (0, 0, 0.0), (0, 0, 0)), 'canards': (3, (0, 1.3, 0.3), (0, 0, 0)), 'grille': (3, (0, 1.2, 0.0), (0, 0, 0)),
    'exhaust': (3, (0, -1.2, 0.2), (0, 0, 0)), 'exhaust_surround': (3, (0, -1.2, 0.2), (0, 0, 0)),
    'side_intake_backs': (3, (0, 0, 0.3), (0, 0, 0)), 'rear_grille': (3, (0, -2.0, 1.2), (10, 0, 0)),
    'hood_vents': (2, (0, 2.1, 1.55), (-12, 0, 0)), 'fin': (3, (0, -1.0, 3.0), (0, 0, 0)), 'skirts': (3, (0, 0, -0.08), (0, 0, 0)),
    'rear_light': (4, (0, -1.3, 0.75), (0, 0, 0)), 'front_light': (4, (0, 1.1, 0.9), (0, 0, 0)),
    'mirror_L': (4, (-0.8, 0.3, 0.7), (0, 0, 20)), 'mirror_R': (4, (0.8, 0.3, 0.7), (0, 0, -20)), 'screws': (4, (0, 0, 0.5), (0, 0, 0)),
}
SPARK_PTS = [
    [(0, -0.75, 0.55), (0.42, 1.35, 0.4), (-0.42, -1.35, 0.4)],
    [(0.72, 1.35, 0.35), (-0.72, 1.35, 0.35), (0.72, -1.35, 0.35), (-0.72, -1.35, 0.35)],
    [(0.55, 1.0, 0.72), (-0.55, 1.0, 0.72), (0.6, -0.95, 0.85), (0.95, 0.2, 0.55), (-0.95, 0.2, 0.55)],
    [(0.6, 0.0, 0.84), (-0.6, 0.0, 0.84), (0.32, -2.05, 0.86), (0, 2.25, 0.12)],
    [(0, -2.25, 0.70), (0.7, 1.9, 0.5), (-0.7, 1.9, 0.5)],
]
HOME = {}
for k in EXPLODE:
    if k in P:
        HOME[k] = (P[k].location.copy(), P[k].rotation_euler.copy())


def place(k, frac, f, jitter=0.0, seed=0):
    g, off, rot = EXPLODE[k]
    hl, hr = HOME[k]
    rng = random.Random(sum(map(ord, {'hood_vents': 'nose', 'exhaust_surround': 'exhaust'}.get(k, k))) + seed)
    j = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jitter
    o = P[k]
    o.location = hl + Vector(off) * frac + j
    o.rotation_euler = Euler([hr[i] + math.radians(rot[i]) * frac for i in range(3)])
    o.keyframe_insert('location', frame=f)
    o.keyframe_insert('rotation_euler', frame=f)


def explode_static(f0, f1, frac0=1.06, frac1=1.0):
    for k in HOME:
        place(k, frac0, f0, 0.0)
        place(k, frac1, f1, 0.03)


def explode_assemble(start=1):
    for k in HOME:
        g = EXPLODE[k][0]
        s = SLAMS[g]
        o = P[k]
        place(k, 1.0, start, 0.0)
        place(k, 0.94, s - 7, 0.03)            # slow hover drift
        hl, hr = HOME[k]
        off = Vector(EXPLODE[k][1])
        d = off.normalized() if off.length > 1e-6 else Vector((0, 0, 1))
        # expo slam: overshoot 2.5 cm past home, rebound, settle
        for f, a in ((s, -0.025), (s + 1, 0.008), (s + 3, 0.0)):
            o.location = hl + d * a
            o.keyframe_insert('location', frame=f)
            o.rotation_euler = hr
            o.keyframe_insert('rotation_euler', frame=f)
        for fc in fcurves(o):
            for kp in fc.keyframe_points:
                if abs(kp.co[0] - (s - 7)) < 0.5:
                    kp.interpolation = 'EXPO'
                    kp.easing = 'EASE_IN'
                elif kp.co[0] >= s:
                    kp.interpolation = 'BEZIER'


def slam_fx(seed=0, flash_e=500):
    for gi, s in enumerate(SLAMS):
        pts = SPARK_PTS[gi]
        per = max(7, 30 // len(pts))      # client: sparks few, small, short
        for j, p in enumerate(pts):
            A.spark_burst(fx, world_pt(p), s, n=per, seed=seed + gi * 10 + j, speed=(3.0, 10.0), up=0.5, life=(3, 8),
                          flat=(0, 0, 1) if gi in (2, 3) else None)
        A.flash(fx, world_pt(pts[0]) + Vector((0, 0, 0.1)), s, energy=flash_e)


def spin_decel(w, f0, f1, rev_s0, tau_s, sign=1.0, phase=0.0, hold=0):
    w0 = rev_s0 * 2 * math.pi
    for f in range(f0, f1 + 1):
        th = min(f - f0, hold) / FPS
        t = max(0, f - f0 - hold) / FPS
        w.rotation_euler[0] = phase + sign * (w0 * th + w0 * tau_s * (1 - math.exp(-t / tau_s)))
        w.keyframe_insert('rotation_euler', index=0, frame=f)
    set_interp(w, 'LINEAR', path='rotation_euler')


def orbit(center, R, phi_deg, h):
    p = math.radians(phi_deg)
    return Vector((center[0] + R * math.cos(p), center[1] + R * math.sin(p), h))


# ============================================================================ shots

def shot_LOOK():
    lights_on()
    views = {'LOOK_F': ((4.6, 5.4, 0.75), (0, 0.4, 0.5), 32), 'LOOK_S': ((7.5, 0.0, 0.7), (0, 0, 0.55), 40),
             'LOOK_R': ((-3.8, -5.6, 1.0), (0, -0.6, 0.55), 32), 'LOOK_T': ((5, 6, 4.5), (0, 0, 0.4), 30)}
    cuts = []
    for i, k in enumerate(('LOOK_F', 'LOOK_S', 'LOOK_R', 'LOOK_T')):
        p, t, lens = views[k]
        cam, tgt = cam_rig('cam' + k, p, t, lens, 4.0)
        cuts.append((i + 1, cam))
    bind_cameras(cuts)

def studio_level(keys):
    """Scale every studio practical + light by a keyed factor [(frame, k), ...] (2A: black like 1E at the cut)."""
    socks = [emit_sock(S['mats']['tube']), emit_sock(S['mats']['tube_flicker']), emit_sock(S['mats']['door']),
             S['mats']['panel'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'],
             bpy.data.materials['softbox_emit'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength']]
    for sk in socks:
        v0 = sk.default_value
        for f, k in keys:
            sk.default_value = v0 * k; sk.keyframe_insert('default_value', frame=f)
        sk.default_value = v0
    ls = S['strip_lights'] + [S['softbox'], S['door_light'], S['door_spill'], S['door_beam']] + S.get('rims', []) + S.get('washes', [])
    for L_ in ls:
        e0 = L_.data.energy
        for f, k in keys:
            L_.data.energy = e0 * k; L_.data.keyframe_insert('energy', frame=f)


def shot_2A():
    # T1: head-on RR rim, clockwise, ~95% frame height, decelerates; pull back to the exploded car
    lights_off()
    hull_from(10000)
    explode_static(1, NF, 1.0, 1.0)
    sc.frame_set(1)
    bpy.context.view_layer.update()
    hub = P['corner_RR']
    wc = hub.matrix_world.translation.copy()            # exploded wheel centre
    lip = 0.163
    D = 0.70 * 50 / (0.95 * 20.25)      # tyre OD (=gear tip in 1E) at 95% frame height; rim lip ~ gear rim
    sc.render.motion_blur_shutter = 0.75
    try:
        sc.eevee.motion_blur_steps = 2
    except Exception:
        pass
    cam, tgt = cam_rig('cam', wc + Vector((lip + D, 0, 0)), wc, 50, 2.8)
    wheel = car['wheels'][3]
    spin_decel(wheel, 1, NF, 26.0 * 24 / 360, 0.55, 1.0, hold=8)   # 26 deg/frame at cut-in = 1E's final speed
    for i, w in enumerate(car['wheels'][:3]):
        spin_decel(w, 1, NF, 0.4, 1.0, 1.0, phase=i)
    end_c = Vector((0, -0.1, 1.0))
    def cpos(f):
        u = ease_io((f - 15) / 21.0, 2.6)
        a = wc + Vector((lip + D, 0, 0))
        b = orbit(end_c, 9.4, 20, 2.3)
        p = a.lerp(b, u)
        p.z += 0.3 * math.sin(math.pi * u)
        return p
    def tpos(f):
        u = ease_io((f - 15) / 21.0, 2.2)
        return wc.lerp(end_c, u)
    key_path(cam, cpos, 1, NF)
    key_path(tgt, tpos, 1, NF)
    for f, L in ((1, 50), (15, 50), (36, 30), (NF, 29)):
        cam.data.lens = L
        cam.data.keyframe_insert('lens', frame=f)
    for f, fs in ((1, 1.4), (15, 1.6), (30, 4.0)):
        cam.data.dof.aperture_fstop = fs
        cam.data.dof.keyframe_insert('aperture_fstop', frame=f)
    shake(cam, amp=0.002, rot_amp=0.0, scale=8, seed=2)
    # r3: the cut-in frame is black like 1E (studio at 15%), only the wheel; the room fades up on the pull-back
    studio_level([(1, 0.15), (14, 0.15), (30, 1.0)])
    # warm ring of back light behind the tyre: the tread shoulder reads as a bright OD silhouette (= 1E's brass
    # gear rim on black); car-only light link so nothing else picks it up
    # (v1 r3: one disc light on the axis shone through the spokes onto the barrel -> a ring of 6 small lights
    # OUTSIDE the tyre radius, just behind the tyre plane, grazing the tread shoulder toward the camera)
    rims_ = []
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        off = Vector((-0.12, 0.62 * math.cos(a), 0.62 * math.sin(a)))
        L_ = light('AREA', f'tyre_rim{k}', wc + off, energy=48, color=(1.0, 0.50, 0.18), size=0.16,
                   target=wc + Vector((0.10, 0.28 * math.cos(a), 0.28 * math.sin(a))))
        L_.data.volume_factor = 0.0
        car_only(L_)
        rims_.append(L_)
    kf = light('AREA', 'tyre_key', wc + Vector((0.9, 0.55, 0.85)), energy=30, color=(0.7, 0.86, 1.0), size=0.6, target=wc)
    kf.data.volume_factor = 0.0
    car_only(kf)
    for L_ in rims_ + [kf]:
        e0 = L_.data.energy
        for f, k in ((1, 1.0), (15, 1.0), (30, 0.25)):
            L_.data.energy = e0 * k; L_.data.keyframe_insert('energy', frame=f)


def shot_2B():
    lights_off()
    hull_from(SLAMS[2])
    explode_assemble(1)
    slam_fx(seed=100)
    try:
        sc.eevee.motion_blur_steps = 3        # r3: curved spark streaks
    except Exception:
        pass
    for i, w in enumerate(car['wheels']):
        spin_decel(w, 1, NF, 0.25, 2.0, 1.0, phase=i * 0.7)
    C0 = Vector((0, -0.1, 0.75))
    cam, tgt = cam_rig('cam', (8, 4, 1), C0, 26, 4.0)
    rng = random.Random(5)
    imp = {}
    for s in SLAMS:
        imp[s] = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.3, 1))).normalized()
    def shake_at(f, amp):
        out = Vector()
        for s, v in imp.items():
            k = f - s
            if 0 <= k <= 5:
                out += v * amp * (1.0, -0.6, 0.35, -0.15, 0.05, 0.0)[k]
        return out
    # r3: opens LOW at the rear-right quarter looking up at the floating stack (2A ended high front-right:
    # no jump cut), fast low orbit round to the front as the parts slam home
    def phi_R_h(f):
        u = (f - 1) / (NF - 1)
        return -62 + 150 * ease_io(u, 1.5), 8.6 - 2.4 * u, 0.6 + 0.55 * math.sin(math.pi * min(1.0, u * 1.15)) - 0.1 * u
    def cpos(f):
        phi, R, h = phi_R_h(f)
        return orbit(C0, R, phi, h) + shake_at(f, 0.09)
    key_path(cam, cpos, 1, NF)
    key_path(tgt, lambda f: C0 + Vector((0, 0, 0.55 - 0.3 * ease_io((f - 1) / NF, 1.4))) + shake_at(f, 0.05), 1, NF)
    # cool top-rim light opposite the camera: every floating part gets a clean edge highlight
    rl = light('AREA', 'orbit_rim', (0, 0, 5), energy=850, color=(0.32, 0.76, 1.0), size=2.5, size_y=0.8)
    rl.data.shape = 'RECTANGLE'
    car_only(rl)
    rl.visible_camera = False
    def rpos(f):
        phi, R, h = phi_R_h(f)
        return orbit(C0, 3.8, phi + 180, 4.6)
    key_path(rl, rpos, 1, NF)
    rlt = empty('orbit_rim_tgt', C0 + Vector((0, 0, 0.6)), coll)
    track_to(rl, rlt)
    # power surge on every slam: strips + softbox spike for a frame
    bs = emit_sock(S['mats']['tube'])
    e0 = bs.default_value
    keys = [(1, e0)]
    for s in SLAMS:      # power dip + surge (the strips brown out on each impact)
        keys += [(s - 1, e0), (s, e0 * 0.25), (s + 1, e0 * 1.25), (s + 3, e0)]
    for f, e in keys:
        bs.default_value = e; bs.keyframe_insert('default_value', frame=f)
    for L_ in S['strip_lights'] + [S['softbox']]:
        e1 = L_.data.energy
        for f, e in [(1, e1)] + [kk for s in SLAMS for kk in ((s - 1, e1), (s, e1 * 0.35), (s + 1, e1 * 1.25), (s + 3, e1))]:
            L_.data.energy = e; L_.data.keyframe_insert('energy', frame=f)
    # the rear bar flickers alive at the light-bar slam (group 4 = f66): red into the floor reflections
    for f, s_, w_ in ((1, 0.0, 0.0), (SLAMS[4], 0.0, 0.0), (SLAMS[4] + 1, 9.0, 14.0), (SLAMS[4] + 2, 2.0, 3.0), (SLAMS[4] + 3, 9.0, 14.0)):
        CAR.set_light(car, 'rear', s_, f, spill=w_)

def _revolve_rings(rings, segs, fan_top=None, fan_bot=None, hexr=None):
    """rings: [(r, z, hex?)] -> closed bmesh by revolving (hex rings follow a hexagon of corner radius r)."""
    bm = bmesh.new()
    c30 = math.cos(math.pi / 6)
    grid = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        hx = c30 / math.cos(((a + math.pi / 6) % (math.pi / 3)) - math.pi / 6)
        col = []
        for (r, z, isx) in rings:
            rr = r * hx if isx else r
            col.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        grid.append(col)
    n = len(rings)
    for k in range(segs):
        A_, B_ = grid[k], grid[(k + 1) % segs]
        for j in range(n - 1):
            bm.faces.new((A_[j], B_[j], B_[j + 1], A_[j + 1]))
    for zc, j in ((fan_top, 0), (fan_bot, n - 1)):
        if zc is None:
            continue
        c = bm.verts.new((0, 0, zc))
        for k in range(segs):
            bm.faces.new((grid[k][j], grid[(k + 1) % segs][j], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bolt_bm(r=0.0080, h=0.0042, rs=0.0029, sd=0.0026, rsh=0.0040, L=0.012, segs=72):
    """ISO 7380-style button head with a true hex socket (closed manifold, no skipped faces)."""
    rings = [(rs * 0.55, h - sd - 0.0004, True), (rs * 0.98, h - sd, True), (rs, h - 0.0002, True), (rs + 0.00035, h, True),
             (r * 0.52, h * 0.985, False), (r * 0.72, h * 0.92, False), (r * 0.86, h * 0.78, False), (r * 0.96, h * 0.55, False),
             (r, h * 0.30, False), (r, 0.00025, False), (r * 0.975, 0.0, False), (rsh, 0.0, False), (rsh, -L, False)]
    return _revolve_rings(rings, segs, fan_top=h - sd - 0.0008, fan_bot=-L)


def counterbore_cutter_bm(segs=64):
    """Counterbore (head pocket 2 mm deep) + through-hole + 45 deg chamfer at the paint, as one closed solid."""
    rings = [(0.0046, -0.03, False), (0.0046, -0.0020, False), (0.0093, -0.0020, False), (0.0093, -0.0003, False),
             (0.0111, 0.0015, False), (0.0111, 0.012, False)]
    return _revolve_rings(rings, segs, fan_top=-0.03, fan_bot=0.012)


def shot_2C():
    # macro: multi-spindle nutrunner drives three button-head bolts into counterbored holes in the nose panel;
    # a fourth (already seated) bolt is the out-of-focus foreground occluder. No sparks (not physical).
    lights_off()
    sc.frame_set(1)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    S['softbox'].data.energy = 0.0
    bpy.data.materials['softbox_emit'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0
    sc.eevee.volumetric_start = 0.02
    sc.eevee.volumetric_end = 2.5
    bolt_m = mat_metal('macro_ti', base=(0.50, 0.48, 0.46), rough=(0.16, 0.34), scale=400)
    bit_m = mat_metal('macro_bit', base=(0.10, 0.10, 0.11), rough=(0.25, 0.4), scale=300)
    chrome_m = mat_metal('macro_chrome', base=(0.75, 0.75, 0.77), rough=(0.06, 0.14), scale=200)
    tool_m = mat_principled('macro_tool', (0.035, 0.036, 0.04), 0.45, 0.6)
    xs = (0.40, 0.47, 0.54, 0.61)
    seats = []
    for x in xs:
        hit, loc, nrm, *_ = sc.ray_cast(dg, Vector((x, 1.035, 2.0)), Vector((0, 0, -1)))
        loc = loc if hit else Vector((x, 1.035, 0.66))
        nrm = nrm if hit else Vector((0, 0, 1))
        seats.append((loc.copy(), nrm.copy()))
        print('[2C] seat', tuple(round(c, 4) for c in loc), 'n', tuple(round(c, 3) for c in nrm))
    # counterbored holes cut into the nose shell (one boolean, cutter parented to the panel)
    nose = P['nose']
    cb = bmesh.new()
    for loc, nrm in seats:
        part = counterbore_cutter_bm()
        q = nrm.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.transform(part, matrix=Matrix.Translation(loc) @ q, verts=part.verts)
        tmp = bpy.data.meshes.new('cb_tmp'); part.to_mesh(tmp); part.free()
        cb.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    cut = from_bmesh('macro_cutter', cb, coll, smooth=False)
    set_mat(cut, car['mats']['machined'])
    cut.hide_render = True; cut.display_type = 'WIRE'
    bo = nose.modifiers.new('bores', 'BOOLEAN')
    bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'; bo.object = cut
    try:
        bo.material_mode = 'TRANSFER'
    except Exception:
        pass
    LAND = (None, 9, 13, 17)
    bm_b = bolt_bm()
    me_b = bpy.data.meshes.new('macro_bolt'); bm_b.to_mesh(me_b); bm_b.free()
    for i, (loc, nrm) in enumerate(seats):
        so = bpy.data.objects.new(f'macro_bolt{i}', me_b); link(so, coll)
        set_mat(so, bolt_m)
        shade(so, 35)
        qe = nrm.to_track_quat('Z', 'Y').to_euler()
        seat = loc - nrm * 0.0020          # head underside sits on the counterbore floor
        if LAND[i] is None:                # foreground bolt: already home
            so.location = seat; so.rotation_euler = (qe.x, qe.y, qe.z - 0.4)
            continue
        land = LAND[i]
        # 1.5 turns (3.3 turns was an unreadable smear), slowing as it torques down
        keys = ((1, 0.034, 0.0), (land - 5, 0.026, 0.35), (land, -0.0003, 1.42), (land + 1, 0.00008, 1.48), (land + 2, 0.0, 1.5))
        for f, dz, spin in keys:
            so.location = seat + nrm * dz
            so.keyframe_insert('location', frame=f)
            so.rotation_euler = (qe.x, qe.y, qe.z - spin * 2 * math.pi)
            so.keyframe_insert('rotation_euler', frame=f)
        set_interp(so, 'BEZIER')
        for fc in fcurves(so):
            for kp in fc.keyframe_points:
                if abs(kp.co[0] - (land - 5)) < 0.5:
                    kp.interpolation = 'EXPO'; kp.easing = 'EASE_IN'
        # nutrunner spindle: hex bit in the socket, chrome holder, dark tool nose; drives the bolt, retracts
        bmh = bmesh.new()
        hexb = _revolve_rings([(0.0027, 0.0, True), (0.0027, 0.022, True)], 6 * 6, fan_top=-0.0004, fan_bot=0.0224)
        tmp = bpy.data.meshes.new('t'); hexb.to_mesh(tmp); hexb.free(); bmh.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        bit = from_bmesh(f'macro_bit{i}', bmh, coll, smooth=True, sharp_angle=30); set_mat(bit, bit_m)
        hold = _revolve_rings([(0.0034, 0.020, False), (0.0055, 0.024, False), (0.0055, 0.060, False), (0.0125, 0.075, False),
                               (0.0125, 0.25, False)], 48, fan_top=0.020, fan_bot=0.25)
        me_h = bpy.data.meshes.new(f'macro_holder{i}'); hold.to_mesh(me_h); hold.free()
        ho = bpy.data.objects.new(f'macro_holder{i}', me_h); link(ho, coll); shade(ho, 40)
        me_h.materials.append(chrome_m)
        ho.parent = bit
        tl = prim('cylinder', f'macro_tool{i}', loc=(0, 0, 0.16), coll=coll, r=0.016, depth=0.18, segments=32)
        set_mat(tl, tool_m); tl.parent = bit
        ret = land + 2
        for f, dz, spin in keys[:3] + ((land + 1, 0.0, 1.48),):
            bit.location = seat + nrm * (dz + 0.0042 - 0.0026 + 0.0002)
            bit.rotation_euler = (qe.x, qe.y, qe.z - spin * 2 * math.pi)
            bit.keyframe_insert('location', frame=f); bit.keyframe_insert('rotation_euler', frame=f)
        for f, dz in ((ret, 0.004), (ret + 2, 0.05), (ret + 4, 0.12)):
            bit.location = seat + nrm * (dz + 0.0042)
            bit.keyframe_insert('location', frame=f)
        set_interp(bit, 'BEZIER')
        for fc in fcurves(bit):
            for kp in fc.keyframe_points:
                if abs(kp.co[0] - (land - 5)) < 0.5:
                    kp.interpolation = 'EXPO'; kp.easing = 'EASE_IN'
    # camera (r3b): 4.5 cm off the paint looking ALONG the row - bolts recede on a diagonal from the lower
    # third to the centre, bits drop in from the top of frame, the seated bolt 0 is a soft foreground shape
    l1, n1 = seats[1]
    c0 = l1 + Vector((-0.17, 0.022, 0.0)) + n1 * 0.075      # r3c: higher so the hex sockets read, bolts whole
    aim = empty('cam_aim', (seats[1][0] + seats[2][0]) * 0.5 + n1 * 0.004, coll)
    cam = camera('cam', c0, None, lens=60, fstop=8.0)
    track_to(cam, aim)
    fo = empty('cam_focus', seats[1][0], coll)
    cam.data.dof.focus_object = fo
    def jolt(f):      # tiny impact jolt on every landing
        out = Vector()
        for s_ in (9, 13, 17):
            k = f - s_
            if 0 <= k <= 3:
                out += Vector((0.2, -0.3, -1.0)) * 0.0010 * (1.0, -0.5, 0.2, 0.0)[k]
        return out
    key_path(cam, lambda f: c0 + Vector((0.0012 * f, 0.0, 0.0)) + jolt(f) * 0.5, 1, NF)
    a0 = (seats[1][0] + seats[2][0]) * 0.5 + n1 * 0.004
    a1 = (seats[2][0] + seats[3][0]) * 0.5 + n1 * 0.004
    key_path(aim, lambda f: a0.lerp(a1, ease_io((f - 9) / 9.0, 1.6)), 1, NF)
    # rack focus: bolt1 -> bolt2 finished 2 frames before bolt2 lands (f11), -> bolt3 by f15
    hb = Vector((0, 0, 0.0035))
    def fpos(f):
        if f <= 9:
            return seats[1][0] + hb
        if f <= 11:
            return (seats[1][0] + hb).lerp(seats[2][0] + hb, ease_io((f - 9) / 2.0, 2.0))
        if f <= 13:
            return seats[2][0] + hb
        if f <= 15:
            return (seats[2][0] + hb).lerp(seats[3][0] + hb, ease_io((f - 13) / 2.0, 2.0))
        return seats[3][0] + hb
    key_path(fo, fpos, 1, NF)
    shake(cam, amp=0.0003, rot_amp=0.0, scale=6, seed=4)
    # warm raking kick light grazing the panel at ~7 deg from the far side + cool strip reflections
    l2 = seats[2][0]
    l3 = seats[3][0]
    # warm raking back-kick beyond the far bolt, ~8 deg off the paint: dome edges + socket rims catch it
    kick = light('AREA', 'macro_kick', l3 + Vector((0.22, -0.05, 0.0)) + n1 * 0.03, energy=1.6, color=(1.0, 0.56, 0.30), size=0.08,
                 target=l1 + n1 * 0.004)
    kick.data.specular_factor = 1.0
    top = light('AREA', 'macro_top', l2 + n1 * 0.32 + Vector((-0.05, 0.10, 0.0)), energy=0.5, color=(0.6, 0.82, 1.0), size=0.3, target=l2)
    # thin local haze slab over the panel (the kick light scatters in it)
    hzm = mat_volume('macro_haze', density=5.0, color=(0.9, 0.85, 0.8), anisotropy=0.6, noise_scale=18.0, noise_contrast=(0.42, 0.75))
    volume_box('macro_haze_box', l2 + n1 * 0.025, (0.5, 0.3, 0.04), hzm, coll)

def look_roll(cam_p, tgt_p, roll_deg):
    q = (Vector(tgt_p) - Vector(cam_p)).to_track_quat('-Z', 'Y')
    return (q @ Quaternion((0, 0, 1), math.radians(roll_deg))).to_euler()


def shot_2D():
    CAR.set_light(car, 'front', 0.0, 1, spill=0.0)
    m = car['mats']['rear_light']
    for f, s, w_ in ((1, 0.0, 0.0), (7, 0.0, 0.0), (8, 12.0, 22.0), (9, 6.0, 10.0), (11, 8.0, 14.0), (16, 7.0, 13.0)):
        CAR.set_light(car, 'rear', s, f, interp='LINEAR', spill=w_)
    for f, v in ((1, 0.0), (8, 0.0), (17, 1.0)):
        CAR.set_sweep(car, 'rear', v, f)
    for fc in fcurves(m.node_tree):
        if 'Sweep' in fc.data_path:
            for kp in fc.keyframe_points:
                if kp.co[0] == 8:
                    kp.interpolation = 'EXPO'; kp.easing = 'EASE_OUT'
    # r3: the warm door spill turned the glossy tail into a bronze bathtub -> off; low camera (18 cm) so the
    # wet floor carries the red bar's reflection + spill
    S['door_spill'].data.energy = 0.0
    S['door_beam'].data.specular_factor = 0.0        # the tail faces the doorway: no warm mirror of it
    dm2 = emit_sock(S['mats']['door']); dm2.default_value = 0.35
    # the bar's mirror image sits ~14 deg below the horizon whatever the camera height -> 35 mm, pitched down
    # so the tail fills the upper half and its red reflection the lower half of the wet floor
    cam, tgt = cam_rig('cam', (2.0, -5.6, 0.16), (-0.15, -2.25, 0.10), 35, 2.0)
    key_path(cam, lambda f: Vector((2.0 - 0.026 * f, -5.6 + 0.02 * f, 0.16 + 0.0012 * f)), 1, NF)
    key_path(tgt, lambda f: Vector((-0.15 - 0.004 * f, -2.25, 0.10)), 1, NF)
    tgt_f = empty('cam_focus', (0.0, -2.28, 0.62), coll)
    cam.data.dof.focus_object = tgt_f
    shake(cam, amp=0.002, rot_amp=0.0, scale=9, seed=7)


def shot_2E():
    CAR.set_light(car, 'rear', 9.0, 1, spill=14.0)
    seq = [(1, 0.0), (7, 0.0), (8, 8.0), (9, 0.3), (10, 0.0), (11, 4.5), (12, 0.6), (13, 9.0), (14, 3.5), (15, 7.0), (16, 6.0)]
    for f, s in seq:
        CAR.set_light(car, 'front', s, f, interp='CONSTANT', spill=s * 0.4)
    # r3: 90 mm, low off the right nose corner, Dutch roll so the slash strip cuts diagonally through the
    # centre third; focus on the strip at f/2
    sc.frame_set(1); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    hit, sm, *_ = sc.ray_cast(dg, Vector((0.70, 1.86, 2.0)), Vector((0, 0, -1)))
    smid = sm if hit else Vector((0.70, 1.86, 0.5))
    smid = smid + Vector((0, 0, 0.006))
    c0 = smid + Vector((0.95, 1.85, 0.12))
    cam = camera('cam', c0, None, lens=90, fstop=2.0)
    fo = empty('cam_focus', smid, coll)
    cam.data.dof.focus_object = fo
    def cp(f):
        return c0 + Vector((-0.010 * f, -0.012 * f, 0.0006 * f))
    key_path(cam, cp, 1, NF)
    key_path(cam, lambda f: look_roll(cp(f), smid + Vector((-0.02, 0.0, -0.01)), -62.0), 1, NF, path='rotation_euler')
    shake(cam, amp=0.0012, rot_amp=0.0, scale=9, seed=8)
    # the overhead softbox turned the whole hood milky grey -> mostly off: the strip + its spill own the frame
    S['softbox'].data.energy *= 0.15
    bpy.data.materials['softbox_emit'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.3
    for L_ in S['strip_lights']:
        L_.data.energy *= 0.35
    for L_ in (S['door_spill'], S['door_beam']):
        L_.data.energy *= 0.3


def shot_2F():
    lights_on()
    cam, tgt = cam_rig('cam', (3.4, 4.3, 0.28), (0.1, 0.6, 0.5), 28, 2.8)
    key_path(cam, lambda f: Vector((3.5, 4.4, 0.27)).lerp(Vector((2.75, 3.45, 0.33)), ease_io((f - 1) / (NF - 1), 1.5)), 1, NF)
    sp = P['sprung']
    fc_key(sp, 'rotation_euler', 0, [(1, 0), (14, 0), (17, math.radians(-1.2)), (21, math.radians(0.6)), (25, math.radians(-0.35)),
                                      (30, math.radians(0.1)), (36, 0)])
    fc_key(sp, 'rotation_euler', 1, [(1, 0), (14, 0), (16, math.radians(0.8)), (19, math.radians(-0.5)), (23, math.radians(0.2)), (28, 0)])
    fc_key(sp, 'location', 2, [(1, 0), (14, 0), (17, -0.025), (22, 0.006), (27, -0.003), (32, 0)])
    for f, s in ((1, 8), (14, 8), (15, 13), (17, 10), (22, 8)):
        CAR.set_light(car, 'rear', s, f, spill=s * 1.6)
    shake(cam, amp=0.004, rot_amp=0.0, scale=10)
    shake(cam, amp=0.012, rot_amp=0.002, scale=2.5, seed=11, start=14, end=26)   # rev rumble

def _release_frame(p):
    """Same accelerating wavefront as act2lib._gn_debris_group (without the per-voxel noise)."""
    V_ = A.VOX
    d = (Vector(p) - Vector((A.DOOR[0], A.SY0, 1.5))).length
    return V_['t0'] + (math.sqrt(V_['v'] ** 2 + 2 * V_['acc'] * d) - V_['v']) / V_['acc']


def _fall(o, fr, f_end, seed, spin=2.5, light=None, emit_sock=None):
    """Rigid fixture shakes loose at frame fr: drops with gravity, gets dragged toward the doorway, tumbles,
    its tube flickers and dies."""
    rng = random.Random(seed)
    p0 = o.location.copy(); r0 = o.rotation_euler.copy()
    sink = Vector(A.VOX['sink'])
    sd = ((sink - p0) * Vector((0.35, 1.0, 0.22))).normalized()
    av = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * spin
    Aa = A.VOX['A'] * rng.uniform(0.5, 0.9)
    fr = int(round(fr)) + rng.randint(-1, 1)
    for f in range(1, f_end + 1):
        t = max(0.0, f - fr) / FPS
        acc = sd * Aa + Vector((0, 0, -9.8))
        o.location = p0 + sd * 1.0 * t + acc * 0.5 * t * t
        o.rotation_euler = Euler((r0[0] + av.x * t, r0[1] + av.y * t, r0[2] + av.z * t))
        o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)
        if o.location.z < -1.0 or o.location.y < A.SY0 - 8:
            o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=f)
            break
    set_interp(o, 'LINEAR')
    set_interp(o, 'CONSTANT', path='scale')
    fl = [(1, 1.0), (fr - 1, 1.0), (fr, 0.25), (fr + 1, 0.9), (fr + 2, 0.0)]
    es0 = emit_sock.default_value if emit_sock is not None else 1.0
    if light is not None:
        e0 = light.data.energy
        for f, v in fl:
            light.data.energy = e0 * v; light.data.keyframe_insert('energy', frame=max(1, f))
    if emit_sock is not None:
        for f, v in fl:
            emit_sock.default_value = v * es0; emit_sock.keyframe_insert('default_value', frame=max(1, f))
    return fr


def shot_2G():
    sc.render.motion_blur_shutter = 0.5
    try:
        sc.eevee.motion_blur_steps = 3        # r3: curved whip/wheel blur (was 1 = straight smears)
    except Exception:
        pass
    canyon = A.build_canyon2(coll, SUN)
    bg = [n for n in WORLD.node_tree.nodes if n.type == 'BACKGROUND'][0]
    for f, v in ((1, 0.25), (10, 0.25), (28, 0.80), (NF, 0.80)):
        bg.inputs['Strength'].default_value = v
        bg.inputs['Strength'].keyframe_insert('default_value', frame=f)
    sun = canyon['sun']
    # sun off while the voxel wall is intact (its shadow map leaked a dotted patch through the tile seams)
    for f, e in ((1, 0.0), (10, 0.0), (13, 1.6), (28, 3.6)):
        sun.data.energy = e; sun.data.keyframe_insert('energy', frame=f)
    # ---- the studio comes apart with the wavefront: every fixture falls when the wave reaches it
    fl_ = S.get('flicker_light')
    if fl_ is not None and fl_.data.animation_data:
        fl_.data.animation_data_clear()
    for i, (so_, L_) in enumerate(S['segs']):
        m_ = so_.data.materials[0]
        sock = None
        if m_ is not None and m_.name.startswith('strip_emit'):
            mc = m_.copy(); so_.data.materials[0] = mc
            sock = mc.node_tree.nodes['Master'].outputs[0]
        _fall(so_, _release_frame(so_.location), NF, 50 + i, light=L_, emit_sock=sock)
    for i, bo in enumerate(S['beam_list']):
        _fall(bo, _release_frame(bo.location + Vector((-4.0, 0, 0))), NF, 90 + i, spin=0.6)
    for i, pn in enumerate(S['panels']):
        pm = pn.data.materials[0].copy(); pn.data.materials[0] = pm
        _fall(pn, _release_frame(pn.location), NF, 120 + i, spin=1.5,
              emit_sock=pm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'])
    sbf = bpy.data.objects.get('softbox_face')
    fr_sb = _release_frame((0, 0, A.SH))
    if sbf is not None:
        _fall(sbf, fr_sb, NF, 140, spin=1.0, emit_sock=bpy.data.materials['softbox_emit'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'])
    L_ = S['softbox']; e0 = L_.data.energy
    for f, v in ((1, 1.0), (fr_sb - 1, 1.0), (fr_sb, 0.3), (fr_sb + 1, 0.8), (fr_sb + 2, 0.0)):
        L_.data.energy = e0 * v; L_.data.keyframe_insert('energy', frame=max(1, int(f)))
    # door: the warm doorway light / beam hand over to the real sun as the front wall goes (f10-16)
    for L_, fe in ((S['door_light'], 13), (S['door_beam'], 17), (S['door_spill'], 20)):
        e0 = L_.data.energy
        for f, v in ((1, 1.0), (10, 1.0), (fe, 0.0)):
            L_.data.energy = e0 * v; L_.data.keyframe_insert('energy', frame=f)
    S['door_light'].data.specular_factor = 0.0
    for L_ in S.get('rims', []) + S.get('washes', []):
        e0 = L_.data.energy
        for f, v in ((1, 1.0), (16, 1.0), (27, 0.0)):
            L_.data.energy = e0 * v; L_.data.keyframe_insert('energy', frame=f)
    dm_ = emit_sock(S['mats']['door'])
    for f, e in ((1, 1.0), (4, 1.0), (9, 0.0)):
        dm_.default_value = e; dm_.keyframe_insert('default_value', frame=f)
    S['door_glow'].scale = (0, 0, 0)
    # haze: cool studio haze -> thin warm dusk air
    hzo = S['haze']
    hzo.location = (0, -60, 40); hzo.scale = (420, 420, 80)
    hz = hzo.active_material.node_tree
    mr = [n for n in hz.nodes if n.type == 'MAP_RANGE'][0]
    vp = [n for n in hz.nodes if n.type == 'PRINCIPLED_VOLUME'][0]
    for f, d in ((1, 0.007), (12, 0.007), (30, 0.0002)):
        mr.inputs['To Max'].default_value = d; mr.inputs['To Max'].keyframe_insert('default_value', frame=f)
    mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
    for f, c in ((1, (0.75, 0.85, 0.95)), (12, (0.75, 0.85, 0.95)), (28, (1.0, 0.80, 0.62))):
        vp.inputs['Color'].default_value = (*c, 1); vp.inputs['Color'].keyframe_insert('default_value', frame=f)
    mo = S.get('motes')
    if mo is not None:
        for f, s_ in ((1, 1.0), (18, 1.0), (19, 0.0)):
            mo.scale = (s_, s_, s_); mo.keyframe_insert('scale', frame=f)
    # ---- launch: speed ramp 16 -> 28 m/s^2 (a hypercar, not a rocket), squat, wheelspin
    LAUNCH = 22
    ys = {}
    yv, vv, tt = 0.0, 0.0, 0.0
    dt = 1.0 / (FPS * 8)
    ys[LAUNCH] = 0.0
    for f in range(LAUNCH + 1, NF + 1):
        for _ in range(8):
            a_ = 16.0 + 12.0 * min(tt / 0.8, 1.0)
            vv += a_ * dt; yv += vv * dt; tt += dt
        ys[f] = yv
    def ypos(f):
        return ys.get(int(f), 0.0) if f >= LAUNCH else 0.0
    key_path(ROOT, lambda f: Vector((0, ypos(f), 0)), 1, NF)
    if not arg('--nodust'):
        A.launch_dust(fx, lambda f: Vector((0, ypos(f), 0)), LAUNCH, NF)
    for w in car['wheels']:
        for f in range(1, NF + 1):
            k = max(0, f - LAUNCH)
            w.rotation_euler[0] = ypos(f) / CAR.WR + (0.0 if f < LAUNCH else 1.4 * (1 - math.exp(-k / 6.0)) * 8.0)
            w.keyframe_insert('rotation_euler', index=0, frame=f)
        set_interp(w, 'LINEAR')
    sp = P['sprung']
    fc_key(sp, 'rotation_euler', 0, [(1, 0), (LAUNCH - 1, 0), (LAUNCH + 3, math.radians(2.8)), (LAUNCH + 8, math.radians(2.0)),
                                      (NF, math.radians(1.4))])
    fc_key(sp, 'location', 2, [(1, 0), (LAUNCH - 1, 0), (LAUNCH + 3, -0.018), (NF, -0.01)])
    for f, s, w_ in ((1, 9, 14), (LAUNCH - 1, 9, 14), (LAUNCH, 14, 24), (LAUNCH + 3, 11, 18)):
        CAR.set_light(car, 'rear', s, f, spill=w_)
    CAR.set_light(car, 'front', 6, 1, spill=3.0)
    # ---- camera: the portal sits right behind the car (same side as 2F's doorway, centred), slow push-in
    # while the room peels, then low beside the launch lane; the car blasts past ~0.8 m from the lens and
    # the camera whips to follow it down the canyon road (sun cheat flips inside the whip blur)
    CAM0, CAM1 = Vector((2.5, 8.6, 0.95)), Vector((1.85, 7.6, 0.62))
    cam, tgt = cam_rig('cam', CAM0, (-0.2, -0.5, 0.85), 24, 4.0)
    key_path(cam, lambda f: CAM0.lerp(CAM1, ease_io((f - 1) / (LAUNCH + 2 - 1), 1.7)), 1, NF)
    def tpos(f):
        a = Vector((-0.2, -0.5, 0.85)).lerp(Vector((0.0, 0.2, 0.62)), ease_io((f - 1) / (LAUNCH - 1), 1.6))
        if f >= LAUNCH:
            a = Vector((0.0, 0.2 + ypos(f) * 0.96, 0.62 + 0.08 * min(1.0, (f - LAUNCH) / 10.0)))
        return a
    key_path(tgt, tpos, 1, NF)
    tgt.keyframe_insert('location', frame=NF)
    pass_f = next((f for f in range(LAUNCH, NF + 1) if ypos(f) > CAM1.y), NF - 6)
    shake(cam, amp=0.004, rot_amp=0.0, scale=7, seed=9)
    shake(cam, amp=0.012, rot_amp=0.0015, scale=2.0, seed=19, start=LAUNCH, end=pass_f + 3)     # launch rumble
    cam.data.clip_end = 6000
    A.flip_sun(pass_f + 1, 180.0 - 6.0, extra=[sun])
    print('[2G] launch f%d, passes lens f%d, sun flip f%d' % (LAUNCH, pass_f, pass_f + 1))

SHOTS = {'LOOK': shot_LOOK, '2A': shot_2A, '2B': shot_2B, '2C': shot_2C, '2D': shot_2D, '2E': shot_2E, '2F': shot_2F,
         '2G': shot_2G}


def _snapshot():
    snap = {'objs': set(bpy.data.objects.keys()), 'tf': {}, 'light': {}, 'sock': []}
    for o in bpy.data.objects:
        snap['tf'][o.name] = (o.location.copy(), o.rotation_euler.copy(), o.scale.copy())
        if o.type == 'LIGHT':
            snap['light'][o.name] = o.data.energy
    for m in bpy.data.materials:
        if m.node_tree:
            for n in m.node_tree.nodes:
                for s in n.inputs:
                    if s.name in ('Emission Strength', 'To Max'):
                        snap['sock'].append((s, s.default_value))
                if n.name in ('Sweep', 'Master'):
                    snap['sock'].append((n.outputs[0], n.outputs[0].default_value))
    return snap


def _restore(snap):
    for k in list(bpy.data.objects.keys()):
        if k not in snap['objs']:
            bpy.data.objects.remove(bpy.data.objects[k], do_unlink=True)
    for idb in list(bpy.data.objects) + list(bpy.data.lights) + list(bpy.data.cameras) + list(bpy.data.materials):
        if idb.animation_data and idb.name != 'motes':
            idb.animation_data_clear()
        nt = getattr(idb, 'node_tree', None)
        if nt is not None and nt.animation_data:
            nt.animation_data_clear()
    for o in bpy.data.objects:
        if o.name in snap['tf']:
            o.location, o.rotation_euler, o.scale = snap['tf'][o.name]
        if o.name in snap['light']:
            o.data.energy = snap['light'][o.name]
    for s, v in snap['sock']:
        s.default_value = v
    sc.timeline_markers.clear()
    sc.render.motion_blur_shutter = 0.5


def _hide_lights():
    for o_ in bpy.data.objects:
        if o_.type == 'LIGHT':
            try:
                o_.visible_camera = False
            except Exception:
                pass


MULTI = arg('--multi', None)      # e.g. "2A:7,22,36/2B:8,19,43/2F:12"
if MULTI:
    print('[time] build %.1fs' % (_t.time() - T0))
    snap = _snapshot()
    tag = arg('--tag', '')
    pct = arg('--pct', 50, int)
    smp = arg('--samples', 16, int)
    for spec in MULTI.split('/'):
        sid, frames = spec.split(':')
        T1 = _t.time()
        inf = SL.get(sid, {'render_frames': 48})
        NF = inf['render_frames']
        sc.frame_start, sc.frame_end = 1, NF
        SHOTS[sid]()
        _hide_lights()
        sc.eevee.taa_render_samples = smp
        sc.render.resolution_percentage = pct
        isf = sc.render.image_settings
        isf.file_format = 'JPEG'; isf.quality = 92
        if frames == 'none':            # build-only validation (no GPU needed)
            for fr in (1, NF // 2, NF):
                sc.frame_set(fr)
            print('[valid] %s built + evaluated OK' % sid)
            flist = []
        elif frames.startswith('anim'):
            stp = int(frames[4:] or 2)
            odir = os.path.join(FILM, 'tests', f'{sid}_motion')
            os.makedirs(odir, exist_ok=True)
            for old_ in os.listdir(odir):
                os.remove(os.path.join(odir, old_))
            flist = [(fr, os.path.join(odir, f'{fr:04d}.jpg')) for fr in range(1, NF + 1, stp)]
        else:
            flist = [(int(x), os.path.join(FILM, 'tests', f'{sid}{tag}_f{int(x):04d}.jpg')) for x in frames.split(',')]
        for fr, path in flist:
            sc.frame_set(fr)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            print('[still]', sc.render.filepath)
        print('[time] %s %.1fs' % (sid, _t.time() - T1))
        _restore(snap)
else:
    SHOTS['LOOK' if SHOT.startswith('LOOK') else SHOT]()
    _hide_lights()
    print('[time] build %.1fs' % (_t.time() - T0)); T1 = _t.time()
    finish(SHOT)
    print('[time] render %.1fs' % (_t.time() - T1))
