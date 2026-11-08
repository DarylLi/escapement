"""ACT III - THE RUN (dusk canyon drive).  Shots 3A 3B 3F 3C 3G 3D 3H 3E (edit order).
test stills : rb.py shots/act3_canyon.py -- --shot 3A --stills 7,20 --pct 50 --samples 16
batch tests : rb.py shots/act3_canyon.py -- --shot 3A,3E --stills 14 --stills_3E 30,60 --pct 30 --samples 16 --tag _vN
              (--<flag>_<ID> overrides --<flag> for that shot)
FINAL       : rb.py shots/act3_canyon.py -- --shot 3E --anim --from 1 --to 84
              -> film/renders/<ID>/0001.png.. at the script default samples (one shot id per call)
"""
import sys, os, json, math, random, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import canyon as C
from mathutils import Vector as V, Matrix, Quaternion, Euler

SL = json.load(open(os.path.join(FILM, 'shotlist.json')))
SAMPLES = 48

# per-frame render timer (starts after the GPU lock is held, so queue waits are excluded)
_RT = {}


@bpy.app.handlers.persistent
def _rt_pre(*_a):
    _RT['t'] = time.time()


@bpy.app.handlers.persistent
def _rt_post(*_a):
    if 't' in _RT:
        print(f"[act3] frame {bpy.context.scene.frame_current} rendered in {time.time() - _RT.pop('t'):.1f}s "
              f"({bpy.context.scene.render.resolution_percentage}%, {bpy.context.scene.eevee.taa_render_samples} spp)",
              flush=True)


bpy.app.handlers.render_pre.append(_rt_pre)
bpy.app.handlers.render_post.append(_rt_post)

VOL_END = {'3A': 60.0, '3B': 60.0, '3C': 75.0, '3D': 40.0, '3E': 90.0, '3F': 70.0, '3G': 50.0, '3H': 60.0}
MB_STEPS = {'3A': 4, '3E': 6, '3G': 6, '3F': 4, '3H': 3}
SHUTTER = {'3C': 0.25}
EXPOSURE = {'3B': -0.3, '3C': -0.75, '3E': -0.3, '3F': -0.2}


def setup(shot):
    global SHOT, INFO, N, CUT_IN, CUT_OUT, sc, T0
    T0 = time.time()
    SHOT = shot
    INFO = [s for s in SL['shots'] if s['id'] == SHOT][0]
    N = INFO['render_frames']
    CUT_IN, CUT_OUT = INFO['cut_in_local'], INFO['cut_out_local']
    vol_start = {'3C': 25.0, '3E': 0.3}.get(SHOT, 0.05)
    reset()
    C._SCATTER_NG = None
    C._PUFF_ME.clear()
    sc = setup_render(1, N, samples=SAMPLES, vol_tile='4', vol_samples=64, vol_end=VOL_END[SHOT], vol_start=vol_start,
                      look='AgX - Medium High Contrast', shutter=SHUTTER.get(SHOT, 0.5), exposure=EXPOSURE.get(SHOT, 0.0))
    try:
        sc.eevee.volumetric_sample_distribution = 0.3 if SHOT == '3C' else 0.8
        sc.eevee.volumetric_light_clamp = 20.0
        sc.eevee.volumetric_ray_depth = 16
        sc.eevee.motion_blur_max = 128
        # v11: multi-step motion blur: 1 step can't represent wheel spin / a car 1.5 m from the lens
        sc.eevee.motion_blur_steps = MB_STEPS.get(SHOT, 1)
    except Exception as e:
        print('[act3] setup', e)


road = C.Road()
LANE_C = C.LANE


def s_lin(s_ref, f_ref, v=40.0):
    return lambda f: s_ref + v * (f - f_ref) / FPS


def sun_dir(s, back=0.0, right=0.0, rd=None):
    """direction toward the sun from the road tangent at s: angles in degrees (back=180 -> behind)."""
    P, t, r, th, k = (rd or road).at(s)
    a = math.radians(back)
    d = t * math.cos(a) + r * math.sin(a)
    if right:
        b = math.radians(right)
        d = d * math.cos(b) + r * math.sin(b)
    return (d.x, d.y)


def car_world(s, local, lane=None, rd=None, slip=0.0):
    """world position of a car-frame point (x right, y forward, z up) for the car at arc length s."""
    P, t, r, th, k = (rd or road).at(s)
    lane = LANE_C if lane is None else lane
    if slip:
        cs, sn = math.cos(slip), math.sin(slip)
        t, r = t * cs - r * sn, r * cs + t * sn
    return P + (rd or road).at(s)[2] * lane + r * local[0] + t * local[1] + V((0, 0, local[2]))


def local_cam(name, root, pos, target, lens=35, fstop=None, focus=None):
    cam = camera(name, (0, 0, 0), lens=lens, fstop=fstop, focus=focus, clip=(0.02, 4000))
    cam.parent = root
    cam.matrix_parent_inverse = Matrix.Identity(4)
    cam.location = pos
    d = V(target) - V(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return cam


def yp(d):
    d = d.normalized()
    return math.atan2(d.y, d.x), math.asin(max(-1.0, min(1.0, d.z)))


def from_yp(y, p):
    return V((math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def spring_aim(cam, f0, f1, raw_dir, omega=0.9, zeta=0.7, sub=8, roll_fn=None, pos_fn=None):
    """Key the camera rotation (and optional position) per frame; the aim follows raw_dir(f) through a
    2nd-order spring (operator lag + slight overshoot on whip-pans). omega in rad/frame."""
    y, p = yp(raw_dir(f0 - 3))
    vy = vp = 0.0
    prev = None
    cam.rotation_mode = 'XYZ'
    dt = 1.0 / sub
    for f in range(f0 - 3, f1 + 1):
        for k in range(sub):
            ff = f - 1 + (k + 1) * dt
            ty, tp = yp(raw_dir(ff))
            ay = omega * omega * wrap(ty - y) - 2 * zeta * omega * vy
            ap = omega * omega * (tp - p) - 2 * zeta * omega * vp
            vy += ay * dt; vp += ap * dt
            y += vy * dt; p += vp * dt
        if f < f0:
            continue
        d = from_yp(y, p)
        q = d.to_track_quat('-Z', 'Y')
        if roll_fn:
            q = Quaternion(d, roll_fn(f)) @ q
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        prev = e
        cam.rotation_euler = e
        cam.keyframe_insert('rotation_euler', frame=f)
        if pos_fn:
            cam.location = pos_fn(f)
            cam.keyframe_insert('location', frame=f)
    for fc in fcurves(cam):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def red_glow(car, root, strength=120.0):
    """red area light behind the rear bar: tints dust + road crimson."""
    L = light('AREA', 'RearGlow', (0, 0, 0), energy=strength, color=(1.0, 0.03, 0.012), size=1.6, size_y=0.15)
    L.parent = root; L.matrix_parent_inverse = Matrix.Identity(4)
    L.location = (0, -2.45, 0.85)
    L.rotation_euler = (math.radians(-90), 0, 0)   # area light shines along -Z -> point it backward (-Y)
    return L


PLUME_COL = (0.62, 0.43, 0.28)


def dust_mat(density=0.9, emit=0.03, color=PLUME_COL, **kw):
    kw.setdefault('contrast', 3.0)
    kw.setdefault('nscale', 2.4)
    kw.setdefault('soft', (0.32, 0.64))
    return C.mat_dust2('Dust', density=density, color=color, aniso=0.7, emit=emit, f0=-160, f1=N + 20, **kw)


REAR, FRONT = 4.0, 16.0   # v11: deep crimson bar at moderate strength (30 read as salmon through AgX)


def lights_on(car, rear=REAR, front=FRONT):
    C.car_lights(car, rear, front, 1)
    m = car.get('mats', {}).get('rear_light')
    if m is not None:
        try:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    if not n.inputs['Emission Color'].links:
                        n.inputs['Emission Color'].default_value = (1.0, 0.012, 0.004, 1)
                if n.type == 'MIX' and n.data_type == 'RGBA':
                    for sock in n.inputs:
                        if sock.type == 'RGBA' and abs(sock.default_value[1] - 0.015) < 1e-4 and sock.default_value[0] > 0.99:
                            sock.default_value = (1.0, 0.012, 0.004, 1)
        except Exception as e:
            print('[act3] bar colour', e)


def fix_bar_fins(car):
    """3D: the bar's vertical end fins intersected the tail (torn jagged edge) -> drop the fin blades."""
    o = car.get('parts', {}).get('rear_light')
    if o is None:
        return
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    kill = [v for v in bm.verts if abs(v.co.x) > 0.8795 and v.co.z < 0.686]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(o.data); bm.free()


def path_motes(s_fn, f0, f1, d=(-1.0, 6.0), every=12.0, n=40, zmax=2.2, seed=40):
    """sparse airborne dust grains along the car's path (sun-lit, non-emissive)."""
    s = s_fn(f0) - 6
    i = 0
    while s < s_fn(f1) + 10:
        c = road.point(s, LANE_C + (d[0] + d[1]) / 2, 0.0)
        C.motes((c.x, c.y, 0.0), radius=max(every * 0.75, (d[1] - d[0]) / 2), n=n, size=(0.003, 0.008),
                zmax=zmax, seed=seed + i, name=f'Motes{i}')
        s += every
        i += 1


def lens_motes(cam_p, fwd, n=60, seed=55, drift=(0, 0, 0)):
    """a few big soft out-of-focus grains 0.3-2 m from the lens (sun-lit, backlit glow only)."""
    c = cam_p + fwd.normalized() * 1.2
    return C.motes((c.x, c.y, 0.0), radius=1.3, n=n, size=(0.0015, 0.004), zmax=max(0.3, cam_p.z + 0.9), seed=seed,
                   drift=drift, f0=1, f1=N)


def rot2(v, deg):
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))

# ------------------------------------------------------------------------------------------------ shots


def shot_3E():
    s_cam = 170.0
    f_pass = 13   # v11: the car is seen charging at the lens for 6 cut frames, passes at cut frame 7
    s_fn = C.speed_curve(s_cam, f_pass, [(-10, 50.0), (40, 56.0)])
    cam_p = road.point(s_cam, 4.3, 0.30)
    tgt = road.point(s_cam + 70, 0.0, 4.5)
    fwd = (tgt - cam_p)
    C.set_sun(rot2((fwd.x, fwd.y), -9), 4.0)     # just right of frame centre, over the canyon side
    C.mat_sky_world(fog=0.0022, strength=1.15)
    C.sun_lamp(4.2)
    env = C.build_environment(road, -60, 540, res=1.6, cam_hint=[(cam_p, (fwd.x, fwd.y), 50.0), (cam_p, (-fwd.x, -fwd.y), 50.0)])
    car = C.get_car()
    C.drive(car, road, s_fn, -2, N + 3)
    lights_on(car)
    red_glow(car, car['root'], 60)
    # v11: sun-rimmed, self-shadowed rust plume (v10 emissive cream read as steam)
    dm = dust_mat(1.0, 0.02)
    P, t, r, th, k = road.at(s_cam + 30)
    wind = (-t.x * 4.5, -t.y * 4.5)                 # tail wind toward the lens
    C.dust_trail(road, s_fn, f_pass - 2, N + 2, dm, every=1, life=110, wind=wind,
                 grow=(2.4, 3.6, 1.4), rise=0.5, skip=lambda s, f: s < s_cam + 14.0, seed=5)
    # the near wake billows: born where the car passed close to the lens, they grow and roll back into it
    eng = C.mat_dust2('Engulf', density=0.6, color=PLUME_COL, aniso=0.7, emit=0.02, f0=-60, f1=N + 20,
                      nscale=2.8, contrast=3.5, soft=(0.35, 0.62))
    for i, (ds_, dd, sz) in enumerate([(16, 0.5, 4.5), (22, 1.5, 5.5), (29, 2.5, 6.5), (37, 3.0, 7.0), (46, 3.5, 8.0)]):
        o = C.puff(f'Billow{i}', eng)
        a = road.point(s_cam + ds_, dd, 0.9)
        b = cam_p + (cam_p - a).normalized() * (2.0 + i) + V((0, 0, 0.8 + 0.35 * i))
        dist = (a - cam_p).length
        u_c = dist / (dist + (b - cam_p).length)
        f_b = f_pass + ds_ / 2.3
        f_c = 59 + 2 * i
        o.rotation_euler = (0.2 * i, 0.1, -th)
        for fk, u, g in ((f_b - 1, 0.0, 0.0), (f_b, 0.0, 0.02), (f_b + 12, u_c * 0.05, 0.3), (f_c - 14, u_c * 0.35, 0.55),
                         (f_c - 6, u_c * 0.7, 0.75), (f_c, u_c, 0.9), (N + 4, 1.0, 1.0)):
            o.location = a.lerp(b, u)
            s_ = 0.6 + sz * g
            o.scale = (s_ * 1.2, s_ * 1.4, s_ * 0.75)
            o.keyframe_insert('location', frame=fk); o.keyframe_insert('scale', frame=fk)
        for fk, dv in ((f_b - 1, 0.0), (f_b + 3, 0.6), (f_c - 6, 0.9), (63, 1.0), (67, 0.0)):   # gone once the lens dust is solid
            o.color = (dv, 1.0, 0, 1); o.keyframe_insert('color', frame=fk)
    # camera: static low on the shoulder; aims back at the oncoming car, whip-pans with the pass, settles down-road
    cam = camera('Cam3E', cam_p, lens=20, fstop=4.0, focus=8.0, clip=(0.02, 4000))
    tdir = (tgt - cam_p).normalized()

    def raw(f):
        c = C.car_pose(road, s_fn(f))[0] + V((0, 0, 0.65))
        dc = (c - cam_p)
        dc = (dc.normalized() + V((0, 0, 0.03))).normalized()
        w = smooth_(f_pass + 3, f_pass + 13, f)
        return dc.lerp(tdir, w).normalized()
    spring_aim(cam, 1, N + 2, raw, omega=0.95, zeta=0.62)
    # focus pull: on the approaching car, then out to the plume
    fd = cam.data.dof
    for f in range(1, N + 1, 2):
        c = C.car_pose(road, s_fn(f))[0]
        fd.focus_distance = min(14.0, max(1.6, (c - cam_p).length)) if f <= f_pass + 6 else 12.0
        fd.keyframe_insert('focus_distance', frame=f)
    # lens-glued dust sheets: wisps from f60, featureless warm tan from CUT_OUT-11 (T3 hand-off)
    C.lens_dust(cam, [(1, 0.0), (60, 0.0), (64, 0.5), (67, 1.0), (N + 2, 1.0)],
                color=(0.95, 0.78, 0.60), strength=1.6, layers=2, seed=3, stream=(2.2, 0.35), f_end=N + 2,
                method='DITHERED')
    # out-of-focus foreground at the lens (grass + one dark rock), front and back so the whip has parallax
    Pc, tc_, rc, thc, kc = road.at(s_cam)
    for i, (dx, dy, sc_, kind) in enumerate([(0.9, 1.6, 1.3, 'g'), (1.8, 2.6, 0.55, 'r'), (0.5, 0.9, 1.2, 'g'),
                                            (1.3, 0.7, 1.1, 'g'), (0.8, -1.4, 1.3, 'g'), (1.6, -2.2, 0.5, 'r'),
                                            (0.35, -0.8, 1.0, 'g')]):
        if kind == 'r':
            o = C.rock_mesh(f'NearRock{i}', 1.0, seed=90 + i, flat=0.7)
            set_mat(o, env['mats']['boulder'])
        else:
            o = C.grass_mesh(f'NearGrass{i}', seed=80 + i, n=40, h=0.42)
            set_mat(o, env['mats']['scrub'])
        p = cam_p + rc * dx + tc_ * dy
        o.location = (p.x, p.y, -0.17)
        o.rotation_euler = (0, 0, i * 1.7)
        o.scale = (sc_, sc_, sc_)
    lens_motes(cam_p, tdir, n=60, drift=(wind[0] * 0.4, wind[1] * 0.4, 0.1))
    return car, cam


def smooth_(a, b, x):
    return C.smooth(a, b, x)


def shot_3A():
    # v11: speed ramp 34 -> 46 m/s (squat under power), camera slides back along the flank + rig jolt
    s_fn = C.speed_curve(262, 1, [(1, 34.0), (30, 46.0)])
    s_mid = s_fn(N / 2)
    C.set_sun(sun_dir(s_mid, back=180), 3.6)   # straight behind -> sun at the road's vanishing point
    C.mat_sky_world(fog=0.0020, strength=1.15)
    C.sun_lamp(4.2)
    env = C.build_environment(road, s_fn(1) - 190, s_fn(N) + 60, res=1.6)
    car = C.get_car()
    root = car['root']
    C.drive(car, road, s_fn, -2, N + 3)
    lights_on(car)
    red_glow(car, root, 60)
    dm = dust_mat(1.4, 0.03)
    C.dust_trail(road, s_fn, -50, N + 2, dm, every=2, life=110, grow=(2.8, 4.6, 2.1), rise=1.3, seed=7)
    cam = camera('Cam3A', (0, 0, 0), lens=18, fstop=4.0, focus=1.5, clip=(0.02, 4000))
    cam.parent = root; cam.matrix_parent_inverse = Matrix.Identity(4)
    tgt = V((-0.55, -3.0, 0.80))
    cam.rotation_mode = 'XYZ'
    prev = None
    locs = {}
    for f in range(-2, N + 3):
        u = C.smooth(1, N, f) ** 1.4
        p = V((-1.45, 2.55 - 1.15 * u, 0.45))
        if f in (18, 19):   # 2-frame rig jolt (expansion joint) at cut frame 12
            p.z += -0.025 if f == 18 else 0.012
        locs[f] = p
        cam.location = p
        q = (tgt - p).to_track_quat('-Z', 'Y')
        if f == 18:
            q = Quaternion(V((1, 0, 0)), 0.012) @ q
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        prev = e
        cam.rotation_euler = e
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    cam.data.dof.focus_distance = 1.6
    # grit: few, dark, matte, and never inside 1 m of the lens
    C.grit_spray(road, s_fn, -14, N + 2, every=2, n_per=30,
                 cam=lambda f: car_world(s_fn(f), locs.get(int(f), locs[min(max(int(f), -2), N + 2)])), cam_r=1.0)
    path_motes(s_fn, 1, N, d=(-4.5, 1.5), every=12.0, n=40, zmax=1.6, seed=41)
    shake(cam, amp=0.004, rot_amp=0.003, scale=3.0, seed=1)
    return car, cam


def shot_3B():
    s_fn = C.speed_curve(395, 1, [(1, 40.0), (30, 43.0)])
    s_mid = s_fn(N / 2)
    C.set_sun(sun_dir(s_mid, back=125), 5.0)   # behind-right: lights the cliff face, out of the mirror
    C.mat_sky_world(fog=0.0020, strength=1.15)
    C.sun_lamp(4.4)
    env = C.build_environment(road, s_fn(1) - 200, s_fn(N) + 120, res=1.6)
    car = C.get_car()
    root = car['root']
    C.drive(car, road, s_fn, -2, N + 3)
    lights_on(car)
    red_glow(car, root, 60)
    dm = dust_mat(1.0, 0.03)
    C.dust_trail(road, s_fn, -50, N + 2, dm, every=2, life=110, grow=(2.4, 4.0, 1.8), rise=1.2, seed=9)
    mir = mirror_rig(car)
    c = mir['center']
    can = car.get('parts', {}).get('canopy')
    if can is not None:
        can.visible_camera = False      # the lens sits at the window line; never look through the smoked glass
    # v11: further back + yawed outboard so the near cliff, posts and scrub streak past behind the mirror
    cp = V((c.x - 0.10, c.y - 0.78, c.z + 0.005))
    look = V((math.sin(math.radians(-14)), math.cos(math.radians(-14)), -0.02))
    cam = local_cam('Cam3B', root, tuple(cp), tuple(cp + look), lens=24, fstop=2.8, focus=(c - cp).length)
    C.light_leak(cam, fx=-1.05, fy=0.45, size=0.5, strength=0.9, keys=[(1, 0.5), (12, 1.2), (22, 0.4), (N, 0.9)])
    shake(cam, amp=0.002, rot_amp=0.0025, scale=4.0, seed=2)
    return car, cam


TOE, MIRROR_K = 16.0, 1.8   # v8: 8 deg looked straight back into our own dark rear flank (black blob)


def mirror_rig(car):
    """Make sure there is a mirror with real (planar probe) reflections on the LEFT side."""
    root = car['root']
    gl = bpy.data.objects.get('Car_mirror_glass_L')
    if gl is not None and not car.get('proxy'):
        vs = [v.co.copy() for v in gl.data.vertices]   # car.py parts sit at home: local == car frame
        center = sum(vs, V()) / len(vs)
        size = ((max(v.x for v in vs) - min(v.x for v in vs)) / 2, (max(v.z for v in vs) - min(v.z for v in vs)) / 2)
        for v in gl.data.vertices:
            v.co = v.co - center
        gl.location = center
        gl.rotation_euler = (0, 0, math.radians(-TOE))
        g = gl
        rot = (math.radians(90), 0, math.radians(-TOE))
        mo = gl.parent
        if mo is not None:
            K = MIRROR_K
            mo.location = tuple(center * (1 - K))
            mo.scale = (K, K, K)
            size = (size[0] * K, size[1] * K)
            off = V((0.0, -0.035, 0.0))
            gl.location = center + off / K
            center = center + off
            # v11: rounded-rect glass (ref mirror), satin bezel shell in body paint with a lip
            hh = (max(v.co.z for v in gl.data.vertices) - min(v.co.z for v in gl.data.vertices)) / 2
            bz = bpy.data.objects.new('MirrorBezel', gl.data.copy())
            link(bz)
            bz.parent = gl; bz.matrix_parent_inverse = Matrix.Identity(4)
            bz.location = (0, 0.006 / K, 0)
            bz.scale = (1.08, 1.0, 1.3)
            pm = car['mats'].get('paint') or mat_principled('MirrorBezel', (0.012, 0.013, 0.015), 0.35, 0.0, coat=1.0)
            bz.data.materials.clear(); bz.data.materials.append(pm)
            for ob, w in ((gl, hh * 0.7), (bz, hh * 1.3 * 0.7)):
                bv = ob.modifiers.new('Round', 'BEVEL')
                bv.affect = 'VERTICES'; bv.width = w; bv.segments = 8; bv.limit_method = 'NONE'
            gl.data.update()
            ny = gl.data.polygons[0].normal.y if len(gl.data.polygons) else 1.0
            so = bz.modifiers.new('Shell', 'SOLIDIFY'); so.thickness = 0.03 / K
            so.offset = 1.0 if ny > 0 else -1.0     # grow the shell forward, away from the lens
            try:
                so.use_rim = True
            except Exception:
                pass
            mm = car['mats'].get('mirror')
            if mm is not None:
                for n in mm.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED':
                        n.inputs['Roughness'].default_value = 0.03
                        n.inputs['Base Color'].default_value = (0.78, 0.80, 0.84, 1)
        center = V((center.x, center.y - 0.002, center.z))
    else:
        center = V((-1.05, 0.95 - 0.105, 1.05)); size = (0.20, 0.11)
        glass_m = mat_principled('MirrorGlass', (0.9, 0.9, 0.9), 0.0, 1.0)
        g = prim('plane', 'MirrorGlass', coll=None)
        g.parent = root; g.matrix_parent_inverse = Matrix.Identity(4)
        g.location = center
        rot = (math.radians(90), 0, 0)
        g.rotation_euler = rot
        g.scale = (size[0] * 2, size[1] * 2, 1)
        set_mat(g, glass_m)
    try:
        pd = bpy.data.lightprobes.new('MirrorProbe', 'PLANE')
    except Exception:
        pd = bpy.data.lightprobes.new('MirrorProbe', 'PLANAR')
    po = bpy.data.objects.new('MirrorProbe', pd)
    link(po)
    po.parent = car.get('sprung') or root; po.matrix_parent_inverse = Matrix.Identity(4)
    po.location = center
    po.rotation_euler = rot
    po.scale = (size[0] * 1.1, size[1] * 1.1, 1)
    try:
        pd.influence_distance = 0.05
    except Exception:
        pass
    return {'center': center, 'glass': g, 'probe': po}


def shot_3C():
    # v11: brakes into the bend (nose dive), powers out
    s_fn = C.speed_curve(518, 1, [(1, 40.0), (14, 30.0), (30, 30.0), (46, 40.0)])
    C.set_sun(sun_dir(580, back=95), 4.5)    # from the canyon side: long shadows across the road
    C.SKY_LIGHT = 0.15                        # v12: from above the flat ground had no shadow depth (p5 .14)
    C.mat_sky_world(fog=0.0012, strength=1.15)
    C.SKY_LIGHT = 0.3
    C.sun_lamp(6.5)
    env = C.build_environment(road, s_fn(1) - 120, s_fn(N) + 140, res=1.5, left=110, right=200)
    car = C.get_car()
    root = car['root']
    C.drive(car, road, s_fn, -2, N + 3)
    lights_on(car)
    red_glow(car, root, 60)
    # v11: thin ochre wake sheared by a cross wind toward the open side (v10: opaque white sausage)
    dm = dust_mat(1.3, 0.03, color=(0.60, 0.40, 0.26), contrast=2.4, soft=(0.25, 0.7))
    P, t, r, th, k = road.at(s_fn(N / 2))
    C.dust_trail(road, s_fn, -70, N + 2, dm, every=2, life=150, grow=(7.0, 11.0, 2.5), rise=1.0, seed=13,
                 wind=(r.x * 3.0, r.y * 3.0))
    cam = camera('Cam3C', (0, 0, 80), lens=30, clip=(1.0, 4000))
    cam.rotation_mode = 'QUATERNION'
    th0 = road.at(s_fn(N * 0.5))[3]
    prev_q = None
    for f in range(-2, N + 4):
        s = s_fn(f)
        Pc, tc, rc, thc, kc = C.car_pose(road, s)
        Pa, ta, ra, tha, ka = road.at(s + 14)
        tg = Pc.lerp(Pa, 0.35)
        hh = th0 + math.radians(-5.0 + 10.0 * f / N)
        up_dir = V((math.sin(hh), math.cos(hh), 0.0))
        # v11: 27 deg off nadir (cliff height, shadows and the bend read in depth)
        pos = tg - up_dir * 21.0 + V((0, 0, 41.0 - 4.0 * f / N))
        fwd = (tg - pos).normalized()
        q = fwd.to_track_quat('-Z', 'Y')
        m = q.to_matrix()
        up_cam = m @ V((0, 1, 0))
        upw = (up_dir - fwd * up_dir.dot(fwd)).normalized()
        ang = math.atan2(fwd.dot(up_cam.cross(upw)), up_cam.dot(upw))
        qq = (Matrix.Rotation(ang, 4, fwd) @ q.to_matrix().to_4x4()).to_quaternion()
        if prev_q is not None and qq.dot(prev_q) < 0:
            qq.negate()
        prev_q = qq.copy()
        cam.location = pos
        cam.rotation_quaternion = qq
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_quaternion', frame=f)
    for fc in fcurves(cam):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
    return car, cam


def shot_3D():
    s_fn = C.speed_curve(760, 1, [(1, 38.0), (28, 44.0)])
    s_mid = s_fn(N / 2)
    C.set_sun(sun_dir(s_mid + 60, back=10), 4.0)   # ahead: back-lit car, glowing bar
    C.mat_sky_world(fog=0.0022, strength=1.15)
    C.sun_lamp(4.0)
    env = C.build_environment(road, s_fn(1) - 40, s_fn(N) + 320, res=1.7)
    car = C.get_car()
    root = car['root']
    C.drive(car, road, s_fn, -2, N + 3)
    lights_on(car, 1.0, FRONT)          # v12: client rule 3 - deep red bar (3.5-7 went salmon through AgX)
    red_glow(car, root, 14)
    dm = dust_mat(0.5, 0.02)
    C.dust_trail(road, s_fn, -40, N + 2, dm, every=2, life=90, grow=(2.0, 3.5, 1.5), rise=1.0, seed=17,
                 sides=(-1,), spread=(-2.5, -0.5))
    exhaust_fx(car, root, bursts=((10, 12), (17, 18)))
    path_motes(s_fn, 1, N, d=(-2.0, 2.0), every=12.0, n=40, zmax=1.8, seed=61)
    cam = local_cam('Cam3D', root, (0.85, -4.75, 0.58), (-0.10, -2.20, 0.66), lens=50, fstop=2.0, focus=2.62)
    shake(cam, amp=0.004, rot_amp=0.003, scale=3.0, seed=4)
    return car, cam


def exhaust_fx(car, root, bursts=((10, 12), (17, 18)), strength=1.4, light_w=1.0):
    """v11: short soft blue-orange flame cores that pop on 2 decaying bursts (overrun crackle), else off."""
    if car.get('proxy'):
        pts = [V((-0.35, -2.3, 0.35)), V((0.35, -2.3, 0.35))]
    else:   # car.py quad centre exhaust
        pts = [V((x, -2.272, 0.43)) for x in (-0.24, -0.08, 0.08, 0.24)]
    root = car.get('sprung') or root
    rng = random.Random(4)
    import bmesh
    for i, p in enumerate(pts):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.012, radius2=0.0, depth=0.15)
        cone = from_bmesh(f'Flame{i}', bm, smooth=True)
        cone.parent = root; cone.matrix_parent_inverse = Matrix.Identity(4)
        cone.location = (p.x, p.y - 0.09, p.z)
        cone.rotation_euler = (math.radians(90), 0, 0)
        b = NB(f'FlameM{i}')
        tc = b.n('ShaderNodeTexCoord'); sp = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Generated'], sp.inputs[0])
        rmp = b.ramp(sp.outputs['Z'], [(0.0, (0.10, 0.22, 1.0)), (0.3, (0.35, 0.3, 0.8)), (0.5, (1.0, 0.42, 0.08)), (1.0, (1.0, 0.16, 0.02))])
        fn = b.noise(tc.outputs['Object'], 40.0, 3, 0.6)
        lw = b.n('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        rim = b.math('POWER', b.math('SUBTRACT', 1.0, lw.outputs['Facing']), 2.0)
        alpha = b.math('MULTIPLY', b.math('POWER', b.math('SUBTRACT', 1.0, sp.outputs['Z']), 1.4),
                       b.maprange(fn.outputs['Fac'], 0.42, 0.62, 0.0, 1.0))
        alpha = b.math('MULTIPLY', alpha, rim)
        em = b.n('ShaderNodeEmission'); b.link(rmp.outputs[0], em.inputs['Color']); em.inputs['Strength'].default_value = strength
        tr = b.n('ShaderNodeBsdfTransparent')
        ms = b.n('ShaderNodeMixShader')
        b.link(b.math('MINIMUM', alpha, 1.0), ms.inputs[0]); b.link(tr.outputs[0], ms.inputs[1]); b.link(em.outputs[0], ms.inputs[2])
        b.link(ms.outputs[0], b.out.inputs['Surface'])
        try:
            b.mat.surface_render_method = 'BLENDED'
        except Exception:
            pass
        set_mat(cone, b.mat)
        cone.visible_shadow = False
        pl = light('POINT', f'FlameLight{i}', (0, 0, 0), energy=light_w, color=(1.0, 0.42, 0.12), shadow_soft=0.05)
        pl.parent = root; pl.matrix_parent_inverse = Matrix.Identity(4)
        pl.location = (p.x, p.y - 0.15, p.z)
        for f in range(-2, N + 4):
            v = 0.0
            for (a_, b_) in bursts:
                if a_ <= f <= b_ + 2:
                    v = max(v, (1.0 - 0.3 * (f - a_)) * rng.uniform(0.7, 1.15))
            v = max(0.0, v)
            cone.scale = (0.8 + 0.4 * v, 0.8 + 0.4 * v, v * rng.uniform(0.8, 1.3)) if v > 0 else (0.0, 0.0, 0.0)
            cone.keyframe_insert('scale', frame=f)
            pl.data.energy = light_w * v
            pl.data.keyframe_insert('energy', frame=f)
        set_interp(cone, 'CONSTANT')
        for fc in fcurves(pl.data):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'

# ---------------------------------------------------------------------------------------- v11 new shots


def shot_3F():
    """DRIFT: low wide on the outside of the hairpin, the car enters in a full four-wheel drift, tail sweeping
    toward the lens, tyres throwing gravel + dust, back-lit by the low sun; camera pans with it."""
    s_apex = 1040.0
    s_fn = C.speed_curve(s_apex, 27, [(1, 38.0), (20, 22.0), (32, 22.0), (48, 30.0)])
    slip_max = math.radians(32)

    def slip_s(s):   # - = nose into the (right-hand) turn, tail out to the left (outside)
        return -slip_max * C.smooth(1003, 1013, s) * (1.0 - C.smooth(1058, 1080, s))

    def slip(f):
        return slip_s(s_fn(f))

    def lane_off(f):   # drifts wide, toward the outside / camera
        s = s_fn(f)
        return -1.1 * C.smooth(1005, 1030, s) * (1.0 - C.smooth(1060, 1085, s))
    s_cam = 1031.0
    cam_p = road.point(s_cam, -6.0, 0.55)
    vd = (C.car_pose(road, s_fn(24))[0] - cam_p)
    sun_az = V(rot2((vd.x, vd.y), 38)).normalized() if False else V((*rot2((vd.x, vd.y), 38), 0)).normalized()
    C.set_sun((sun_az.x, sun_az.y), 4.0)            # v13: just off frame behind the drifting car -> back-lit dust
    C.mat_sky_world(fog=0.0022, strength=1.15)
    C.sun_lamp(4.3)
    env = C.build_environment(road, s_fn(1) - 60, s_fn(N) + 70, res=1.5, right=180)
    car = C.get_car()
    C.drive(car, road, s_fn, -2, N + 3, yaw_fn=slip, lane_fn=lane_off, roll_k=0.0034)
    lights_on(car)
    red_glow(car, car['root'], 60)
    dm = dust_mat(0.2, 0.03)   # v15: the hairpin is in the far cliff's shadow, so the dust is never sun-lit: keep it thin

    def rear_lat(f):
        return lane_off(f) + 1.35 * math.sin(slip(f))
    C.dust_trail(road, s_fn, -30, N + 2, dm, every=1, life=50, grow=(2.0, 2.8, 1.2), rise=0.5, seed=31,
                 lateral=rear_lat, spread=(-4.0, -0.5), dens=1.0)
    C.grit_spray(road, s_fn, 6, N + 2, every=1, n_per=25, life=14, side_vel=-5.0, lateral=rear_lat,
                 back=(1.0, 4.0), up=(1.2, 3.0), size=(0.005, 0.016), cam=lambda f: cam_p, cam_r=3.0, seed=33)
    cam = camera('Cam3F', cam_p, lens=24, fstop=2.8, focus=10.0, clip=(0.02, 4000))

    def raw(f):
        c = C.car_pose(road, s_fn(f - 1))[0] + C.road_r(road, s_fn(f - 1)) * lane_off(f - 1) + V((0, 0, 0.9))
        return (c - cam_p).normalized()
    spring_aim(cam, 1, N + 2, raw, omega=0.7, zeta=0.8)
    fd = cam.data.dof
    for f in range(1, N + 1, 2):
        c = C.car_pose(road, s_fn(f))[0]
        fd.focus_distance = max(3.0, (c - cam_p).length)
        fd.keyframe_insert('focus_distance', frame=f)
    for f, ln in ((22, 24.0), (34, 50.0)):     # v14: push in as the car slides out of the hairpin
        cam.data.lens = ln
        cam.data.keyframe_insert('lens', frame=f)
    shake(cam, amp=0.006, rot_amp=0.004, scale=3.0, seed=6)
    lens_motes(cam_p, raw(30), n=50, seed=57)
    return car, cam


def shot_3G():
    """OVERPASS: lens on the asphalt, the car charges head-on and drives OVER it (underbody, diffuser, exhaust
    glow sweep overhead), then a whip-pan finds it receding."""
    s0 = 640.0
    f_over = 14
    s_fn = C.speed_curve(s0, f_over, [(1, 46.0), (36, 50.0)])
    cam_p = road.point(s0, LANE_C, 0.085)
    # v15: sun behind-right of the oncoming car (172 put it straight behind the lens after the whip and the receding
    # rear mirrored the sunlit horizon -> the black car read white)
    C.set_sun(sun_dir(s0, back=138), 3.8)
    C.mat_sky_world(fog=0.0022, strength=1.15)
    C.sun_lamp(4.2)
    env = C.build_environment(road, s0 - 220, s0 + 160, res=1.7)
    car = C.get_car()

    def lift(f):   # body rides 4 cm higher over the lens (suspension at full droop over the crest)
        return 0.04 * C.smooth(f_over - 4, f_over - 2, f) * (1.0 - C.smooth(f_over + 2, f_over + 4, f))
    C.drive(car, road, s_fn, -2, N + 3, lift_fn=lift)
    lights_on(car, 4.0, FRONT)
    red_glow(car, car['root'], 40)
    exhaust_fx(car, car['root'], bursts=((f_over - 1, f_over + 1),), strength=2.0, light_w=1.0)
    # underbody: dim warm glow from the exhaust/engine bay onto the asphalt as it passes
    ul = light('POINT', 'UnderGlow', (0, 0, 0), energy=6.0, color=(1.0, 0.35, 0.10), shadow_soft=0.2)
    ul.parent = car.get('sprung') or car['root']; ul.matrix_parent_inverse = Matrix.Identity(4)
    ul.location = (0, -1.6, 0.18)
    dm = dust_mat(0.45, 0.02)
    C.dust_trail(road, s_fn, -20, N + 2, dm, every=2, life=90, grow=(2.0, 3.2, 1.2), rise=0.6, seed=41,
                 skip=lambda s, f: abs(s - s0) < 6.0)
    cam = camera('Cam3G', cam_p, lens=16, fstop=2.8, focus=6.0, clip=(0.012, 4000))
    P0, t0, r0, th0, k0 = road.at(s0)
    back = (-t0 + V((0, 0, math.tan(math.radians(6))))).normalized()

    def raw(f):
        if f <= f_over + 1:
            return back
        c = C.car_pose(road, s_fn(f))[0] + V((0, 0, 0.7))
        return (c - cam_p).normalized()
    spring_aim(cam, 1, N + 2, raw, omega=0.75, zeta=0.6)
    fd = cam.data.dof
    for f in range(1, N + 1):
        c = C.car_pose(road, s_fn(f))[0]
        fd.focus_distance = max(0.25, min(40.0, (c - cam_p).length - 2.0))
        fd.keyframe_insert('focus_distance', frame=f)
    # v14: crash zoom onto the receding car once the whip has found it (16 -> 45 mm)
    for f, ln in ((f_over + 3, 16.0), (f_over + 7, 45.0)):
        cam.data.lens = ln
        cam.data.keyframe_insert('lens', frame=f)
    shake(cam, amp=0.002, rot_amp=0.004, scale=2.0, seed=8)
    return car, cam


def shot_3H():
    """SLOT CANYON: FPV drone chase behind the car through a narrow sinuous slot, banking hard,
    walls inches from the lens, the low sun cutting through side-canyon gaps, dust trail."""
    import canyon_slot as CS
    rd = C.Road(s0=-200.0, s1=520.0, bumps=CS.SLOT_BUMPS)
    s_fn = C.speed_curve(40.0, 1, [(1, 30.0), (48, 33.0)])
    s_m = s_fn(N / 2)
    P, t, r, th, k = rd.at(s_m)
    # v14: sun ahead-left and high enough to reach down the slot -> back-lit shafts in the fog toward the lens
    sun_az = (t * 0.9 - r * 0.45).normalized()
    C.set_sun((sun_az.x, sun_az.y), 28.0)
    C.mat_sky_world(fog=0.0, strength=1.15)
    C.sun_lamp(4.6)
    CS.build_slot(rd, s_fn(-6) - 25, s_fn(N + 4) + 90, sun_side=-1, fog=0.011)
    car = C.get_car()
    C.drive(car, rd, s_fn, -2, N + 3, lane=0.0, roll_k=0.003)
    lights_on(car)
    red_glow(car, car['root'], 10)
    dm = dust_mat(0.35, 0.02)
    C.dust_trail(rd, s_fn, -30, N + 2, dm, every=2, life=80, grow=(1.4, 2.6, 0.8), rise=0.2, seed=51, lane=0.0,
                 spread=(-0.6, 0.6))
    cam = camera('Cam3H', (0, 0, 0), lens=14, fstop=None, clip=(0.05, 4000))

    def cam_s(f):
        return s_fn(f) - 7.0

    def pos(f):
        s = cam_s(f)
        k_ = rd.at(s + 4)[4]
        swing = max(-1.2, min(1.2, -k_ * 32.0))      # drifts toward the outside wall in the bends
        return rd.point(s, swing, 1.6 + 0.25 * math.sin(f * 0.21))

    def raw(f):
        c = C.car_pose(rd, s_fn(f), lane=0.0)[0] + V((0, 0, 2.2))
        return (c - pos(f)).normalized()

    def roll(f):
        k_ = rd.at(cam_s(f) + 6)[4]
        return max(-math.radians(18), min(math.radians(18), k_ / 0.04 * math.radians(18)))
    spring_aim(cam, -2, N + 3, raw, omega=1.1, zeta=0.8, roll_fn=roll, pos_fn=pos)
    shake(cam, amp=0.01, rot_amp=0.004, scale=4.0, seed=9)
    return car, cam


def _road_r(rd, s):
    return rd.at(s)[2]


C.road_r = _road_r

cams = {'3A': shot_3A, '3B': shot_3B, '3C': shot_3C, '3D': shot_3D, '3E': shot_3E,
        '3F': shot_3F, '3G': shot_3G, '3H': shot_3H}
# --shot accepts a comma list for batched TEST stills (one GPU-lock wait); final renders use one id
_argv0 = list(sys.argv)
for _shot in str(arg('--shot', '3A')).split(','):
    sys.argv = list(_argv0)
    sfx = '_' + _shot
    for tok in list(_argv0):
        if tok.startswith('--') and tok.endswith(sfx) and not tok.startswith('--anim_'):
            base = tok[:-len(sfx)]
            val = _argv0[_argv0.index(tok) + 1]
            if base in sys.argv:
                sys.argv[sys.argv.index(base) + 1] = val
            else:
                sys.argv += [base, val]
    if '--anim' in _argv0 and ('--anim_' + _shot) not in _argv0 and any(t.startswith('--anim_') for t in _argv0):
        sys.argv = [t for t in sys.argv if t != '--anim']
    try:
        setup(_shot)
        car, cam = cams[SHOT]()
        sc.camera = cam
        C.comp(bloom=0.4, threshold=0.9, size=0.7, dispersion=0.006, streaks=0.18, streak_thr=4.0)
        print(f'[act3] {SHOT} build {time.time() - T0:.1f}s  frames 1..{N} cut {CUT_IN}-{CUT_OUT}', flush=True)
        finish(SHOT)
    except Exception:
        if ',' not in str(arg('--shot', '3A')):
            raise
        import traceback
        traceback.print_exc()
        print(f'[act3] {_shot} FAILED, continuing batch', flush=True)
