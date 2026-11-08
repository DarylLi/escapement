"""ACT I - THE MOVEMENT (+ 6A title).  Shots 1A 1B 1C 1D 1E 6A.
Usage (via tools/rb.py):  shots/act1_gears.py -- --shot 1A --stills 7,20,40 --pct 50 --samples 16
--shot also accepts a comma list (1A,1B,...) to build+render several shots in one Blender session.
"""
import sys, os, json, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import act1_kit as K
from mathutils import Vector, Matrix, Euler, Quaternion

SL = {s['id']: s for s in json.load(open(os.path.join(FILM, 'shotlist.json')))['shots']}
TAU = math.tau
D2R = math.radians


# ============================================================================ common set-up
def base(shot, fog=0.03, fog_col=(0.5, 0.72, 0.92), aniso=0.6, vol_end=40.0, shutter=0.5, samples=32, bloom=0.45,
         look='AgX - Medium High Contrast', world=(0.0012, 0.0016, 0.0022), dof=None):
    reset()
    K._CACHE.clear()
    s = SL[shot]
    sc = setup_render(1, s['render_frames'], samples=samples, vol_tile='8', vol_samples=64, vol_end=vol_end,
                      vol_start=0.05, shutter=shutter, look=look)
    compositor(bloom=bloom, threshold=1.0, bloom_size=0.65, dispersion=0.007)
    w = world_color(world)
    if fog > 0:
        add_world_fog(w, fog, fog_col, aniso)
    K.dof_settings(**(dof or {}))
    M = K.materials()
    C = collection('SET_' + shot)
    random.seed(hash(shot) % 1000)
    return sc, M, C


def frame_empty(name, loc, rot_mat, C):
    e = empty(name, loc, C)
    e.rotation_euler = rot_mat.to_euler()
    return e


def gear_chain(C, M, specs, frame, N, rate0, name='g', phase0=0.0, keys=True):
    """Gears in the XY plane of `frame` (an empty). specs: dicts with t, rp(first/coax), thick, style, body,
    spokes, mat, dir (deg, from previous centre), dz, coax, bend, spoke_w, rim_w.
    Neighbours mesh: speed ~ 1/teeth, alternating direction, tooth-into-gap phase."""
    out = []
    prev = None
    for i, sp in enumerate(specs):
        t = sp['t']
        if prev is None:
            rp = sp['rp']; c = Vector((0, 0, 0)); phi = phase0; w = rate0
        elif sp.get('coax'):
            rp = sp['rp']; c = prev['c'].copy(); phi = random.uniform(0, TAU); w = prev['w']
        else:
            m = 2 * prev['rp'] / prev['t']
            rp = m * t / 2
            d = D2R(sp.get('dir', 0.0))
            c = prev['c'] + Vector((cos(d), sin(d), 0)) * (prev['rp'] + rp)
            c.z = prev['c'].z
            s1 = TAU / prev['t']
            frac = ((d - prev['phi']) / s1) % 1.0
            phi = d + math.pi - (TAU / t) * (0.5 - frac)
            w = -prev['w'] * prev['t'] / t
        c = c.copy()
        c.z += sp.get('dz', 0.0)
        g = K.gear(f"{name}{i}", t, rp, sp.get('thick', rp * 0.08), sp.get('style', 'round'), sp.get('body', 'spokes'),
                   spokes=sp.get('spokes', 5), bend=sp.get('bend', 0.0), spoke_w=sp.get('spoke_w'), rim_w=sp.get('rim_w'),
                   hub=sp.get('hub'), coll=C, mat=sp.get('mat', M['brass']))
        g.parent = frame
        g.location = c
        if keys:
            K.spin_linear(g, 2, 1, N, phi, w)
        else:
            g.rotation_euler[2] = phi
        rec = {'obj': g, 't': t, 'rp': rp, 'c': c, 'phi': phi, 'w': w, 'thick': sp.get('thick', rp * 0.08)}
        out.append(rec)
        prev = rec
    return out


def to_world(frame, p):
    frame.users_scene  # noqa
    bpy.context.view_layer.update()
    return frame.matrix_world @ Vector(p)


def cos(a):
    return math.cos(a)


def sin(a):
    return math.sin(a)


def scatter_screws(C, M, centers, n, rad, z, size, seed=3, mat=None):
    rnd = random.Random(seed)
    for i in range(n):
        cx, cy = rnd.choice(centers)
        a, r = rnd.uniform(0, TAU), rnd.uniform(rad * 0.3, rad)
        K.screw((cx + r * cos(a), cy + r * sin(a), z), size * rnd.uniform(0.8, 1.2), C, mat or M['blued'])


def cam_basic(name, loc, target, lens, fstop, focus):
    c = camera(name, loc, target=target, lens=lens, fstop=fstop, focus=focus, clip=(0.02, 200))
    c.data.dof.aperture_blades = 0
    return c


def key_cam(c, fv_loc, fv_target, interp='BEZIER'):
    """keys location & rotation looking at moving target. fv_*: [(frame, xyz)]"""
    c.rotation_mode = 'QUATERNION'
    prev = None
    for (f, p), (_, t) in zip(fv_loc, fv_target):
        q = K.look_quat(p, t)
        if prev is not None and prev.dot(q) < 0:
            q.negate()
        c.location = p
        c.rotation_quaternion = q
        c.keyframe_insert('location', frame=f)
        c.keyframe_insert('rotation_quaternion', frame=f)
        prev = q
    set_interp(c, interp)


# ============================================================================ background mechanism filler
def bg_field(C, M, N, center, spread, n_chains=4, seed=7, axis_rot=Euler((D2R(90), 0, 0)), size=(0.8, 2.2), mats=None):
    """Clusters of meshing gears floating in haze at the back (planes face the camera by default)."""
    rnd = random.Random(seed)
    mats = mats or [M['brass'], M['steel'], M['brass_big'], M['gold']]
    for k in range(n_chains):
        cx = center[0] + rnd.uniform(-spread[0], spread[0])
        cy = center[1] + rnd.uniform(-spread[1], spread[1])
        cz = center[2] + rnd.uniform(-spread[2], spread[2])
        rot = Euler((axis_rot.x + rnd.uniform(-0.25, 0.25), axis_rot.y + rnd.uniform(-0.2, 0.2), axis_rot.z + rnd.uniform(-0.35, 0.35)))
        fr = frame_empty(f'bgf{k}', (cx, cy, cz), rot.to_matrix(), C)
        r0 = rnd.uniform(*size)
        t0 = int(r0 * rnd.uniform(28, 40))
        specs = [{'t': t0, 'rp': r0, 'thick': r0 * 0.1, 'spokes': rnd.choice([4, 5, 6]), 'mat': rnd.choice(mats),
                  'bend': rnd.choice([0, 0, 0.8])}]
        for j in range(rnd.randint(1, 3)):
            specs.append({'t': rnd.randint(14, 48), 'dir': rnd.uniform(-180, 180), 'dz': rnd.uniform(-0.15, 0.15) * r0,
                          'thick': r0 * 0.09, 'spokes': rnd.choice([4, 5, 6]), 'mat': rnd.choice(mats)})
        gear_chain(C, M, specs, fr, N, rnd.choice([-1, 1]) * rnd.uniform(0.002, 0.006), name=f'bg{k}_')


# ============================================================================ 1A  reveal: wall of giant teeth
def shot_1A():
    sc, M, C = base('1A', fog=0.007, fog_col=(0.5, 0.72, 0.95), aniso=0.7, vol_end=40)
    K.haze('haze', (0.0, 9.0, 0.0), (16.0, 10.0, 8.0), 0.12, (0.45, 0.7, 0.95), 0.6, 2.0)
    N = SL['1A']['render_frames']
    P = Vector((0.12, 0.0, 0.0))            # rim point (focus) slightly right of centre
    R = 2.4
    psi, tau = D2R(52), D2R(-14)
    rot = Matrix.Rotation(tau, 3, 'X') @ Matrix.Rotation(psi, 3, 'Z') @ Matrix.Rotation(D2R(90), 3, 'X')
    centre = P + Matrix.Rotation(tau, 3, 'X') @ Vector((R * cos(psi), R * sin(psi), 0))
    fr = frame_empty('heroFrame', centre, rot, C)
    # local angle pi on hero = rim point P.  Partner meshes at local 168 deg (top of frame).
    ch = gear_chain(C, M, [
        {'t': 90, 'rp': R, 'thick': 0.36, 'style': 'trap', 'spokes': 6, 'spoke_w': 0.3, 'rim_w': 0.42, 'mat': M['brass_big']},
        {'t': 34, 'dir': 166, 'thick': 0.3, 'style': 'trap', 'spokes': 5, 'mat': M['rust'], 'dz': -0.05},
        {'t': 22, 'dir': 120, 'thick': 0.26, 'style': 'trap', 'body': 'disk', 'mat': M['steel'], 'dz': 0.12},
    ], fr, N, 0.0012, name='wall')
    hero = ch[0]
    # rivets/screws around the hero hub ring + face (detail on the dark face)
    for k in range(72):
        a = TAU * k / 72
        s = K.screw((0, 0, 0), 0.026, C, M['steel_pol'] if k % 2 else M['gold_pol'])     # polished heads catch the rim light
        s.parent = hero['obj']
        s.location = (2.12 * cos(a), 2.12 * sin(a), 0.19)
    # foreground occluder (dark rim very close, left)
    fr2 = frame_empty('fgFrame', (-1.18, -1.55, 0.32), Matrix.Rotation(D2R(90), 3, 'X') @ Matrix.Rotation(D2R(8), 3, 'Y'), C)
    gear_chain(C, M, [{'t': 44, 'rp': 1.0, 'thick': 0.12, 'style': 'trap', 'spokes': 5, 'mat': M['rust']}], fr2, N, -0.004, name='fg')
    # mid-ground arbor + jewel bridge crossing behind
    K.cyl('arborMid', 0.05, 6.0, (-0.9, 1.4, 0.0), rot=(0, D2R(90), D2R(20)), coll=C, mat=M['steel_pol'])
    K.slab('beam', K.stadium((-3.0, 0), (2.0, 0), 0.22, 0.22), -0.06, 0.06, C, M['geneve'], 0.02).location = (0, 3.2, -0.9)
    # back field in haze
    bg_field(C, M, N, (0.5, 7.0, 0.0), (3.0, 2.0, 1.6), n_chains=6, seed=11, size=(1.0, 2.6))
    bg_field(C, M, N, (-1.0, 13.0, 1.0), (5.0, 2.0, 2.5), n_chains=4, seed=12, size=(1.5, 3.0))
    K.gear_wall('wall1A', M, 1, N, (0.0, 10.0, 0.0), (12.0, 5.0, 6.0), 50, seed=17, coll=C, radii=(0.5, 1.6))
    # dust motes
    m1 = K.motes('motesNear', 320, (0.0, -0.2, 0.0), (2.0, 1.6, 1.3), (0.0006, 0.0018), 1, C, M['mote'])
    K.motes('motesLens', 40, (0.0, -1.6, 0.0), (1.2, 0.8, 0.7), (0.0006, 0.0012), 5, C, M['mote'])
    m2 = K.motes('motesFar', 1600, (0.3, 4.0, 0.3), (6.0, 6.0, 3.5), (0.004, 0.012), 2, C, M['mote'], cool_frac=0.7)
    K.drift(m1, 1, N, (0.002, 0.0, 0.0018), 0.02)
    K.drift(m2, 1, N, (-0.003, 0.0, 0.003), 0.01)
    # ---- lights
    # 1) the SWEEP: an elongated spot (horizontal band ~1.5 teeth tall) that climbs the tooth stack from below the
    #    frame (local 6) to above it (~local 30), revealing teeth one by one with darkness on both sides.
    tgt = empty('sweepTgt', P + Vector((0.1, 0.25, -0.45)), C)
    sweep = light('SPOT', 'Sweep', (-2.1, -0.75, -0.4), energy=0, color=(1.0, 0.74, 0.48), spot=34, blend=0.45, shadow_soft=0.05, coll=C)
    sweep.scale = (1.0, 0.22, 1.0)
    track_to(sweep, tgt)
    key_vec(tgt, 'location', [(3, tuple(P + Vector((0.1, 0.25, -0.34)))), (30, tuple(P + Vector((0.1, 0.25, 0.62)))),
                              (60, tuple(P + Vector((0.1, 0.25, 1.4))))], interp='BEZIER')
    key_vec(sweep, 'location', [(3, (-2.1, -0.75, -0.14)), (30, (-2.1, -0.75, 0.82)), (60, (-2.1, -0.75, 1.6))], interp='BEZIER')
    K.key_energy(sweep, [(2, 0.0), (5, 380.0), (34, 380.0), (50, 240.0), (60, 200.0)])
    K.vol(sweep, 0.12)
    # 2) broad warm key only after the sweep has crossed (desaturated warm, not deep orange)
    key = light('AREA', 'Key', (-1.5, -1.2, -1.2), energy=0, color=(1.0, 0.72, 0.45), size=1.2, coll=C, target=P)
    K.vol(key, 0.1)
    K.key_energy(key, [(20, 0.0), (40, 45.0), (60, 55.0)])
    rim = light('AREA', 'RimCool', (0.9, 1.3, 1.1), energy=0, color=(0.45, 0.75, 1.0), size=0.6, coll=C, target=P)
    K.key_energy(rim, [(10, 0.0), (32, 220.0), (60, 260.0)])
    # 3) cyan haze behind the teeth: present (dim) from frame 1 so the black opening shows a sliver of haze and a
    #    few backlit dust specks, then blooms to a luminous cyan gap (img_gears signature)
    back = light('SPOT', 'BackHaze', (2.0, 16.0, 3.2), energy=0, color=(0.5, 0.78, 1.0), spot=40, blend=0.6, coll=C, target=(0.0, 0.0, -0.4))
    back.data.shadow_soft_size = 0.4
    K.key_energy(back, [(1, 45000.0), (10, 55000.0), (36, 150000.0), (60, 170000.0)])
    back2 = light('SPOT', 'BackHaze2', (-5.0, 12.0, -1.0), energy=0, color=(0.55, 0.8, 1.0), spot=30, blend=0.5, coll=C, target=(0.5, 0.0, 0.5))
    K.key_energy(back2, [(12, 0.0), (40, 60000.0)])
    sliver = light('SPOT', 'Sliver', (1.6, 4.5, 1.9), energy=0, color=(0.5, 0.8, 1.0), spot=8, blend=0.6, shadow_soft=0.05, coll=C,
                   target=(-0.55, -1.6, -0.55))
    K.vol(sliver, 1.0)
    K.key_energy(sliver, [(1, 2600.0), (14, 2600.0), (30, 900.0), (60, 600.0)])
    # soft sheen on the hero's tarnished face (mirror direction of the camera about the wheel axis) so the face
    # reads as worn brass with screws, not a black board with holes
    n_ax = (rot @ Vector((0, 0, 1))).normalized()
    cpos = Vector((-0.06, -2.7, 0.06))
    face_pt = centre + rot @ Vector((-2.05, 0.15, 0.18))
    if n_ax.dot(cpos - face_pt) < 0:
        n_ax = -n_ax
    fs = K.sheen_card(cpos, face_pt, 3.0, 1.6, 0, (1.0, 0.78, 0.55), C, name='FaceSheen', normal=tuple(n_ax))
    K.key_energy(fs, [(18, 0.0), (40, 6.0), (60, 7.0)])
    K.haze('toothHaze', (-0.3, -0.6, 0.0), (2.6, 2.2, 1.8), 0.035, (0.6, 0.75, 0.9), 0.6, 4.0)
    # ---- camera: slow push, focus on teeth
    cam = cam_basic('Cam1A', (-0.1, -2.9, 0.08), P, 85, 1.6, 2.9)
    key_cam(cam, [(1, (-0.12, -3.0, 0.1)), (N, (0.0, -2.45, 0.02))], [(1, P + Vector((-0.14, 0, 0.02))), (N, P + Vector((-0.1, 0, 0)))])
    K.key_focus(cam, [(1, (P - Vector((-0.12, -3.0, 0.1))).length), (N, (P - Vector((0.0, -2.45, 0.02))).length)])
    sc.camera = cam


# ============================================================================ 1B  escapement tick
def shot_1B():
    sc, M, C = base('1B', fog=0.004, aniso=0.6, vol_end=30, dof=dict(max_px=200.0, jitter=True, overblur=6.0))
    N = SL['1B']['render_frames']
    TICK = 13
    T, rp = 20, 0.55
    ew = K.gear('escapeWheel', T, rp, 0.05, 'club', 'spokes', spokes=4, bend=0.9, coll=C, mat=M['gold'])
    r_tip = ew['r_tip']
    pitch = TAU / T
    a0 = D2R(3)
    # locked -> unlocking (the wheel is drawn slightly BACK while the pallet slides off) -> impulse jump with
    # recoil -> drop/lock, so something moves through the whole cut, not just on the tick frame
    keys = [(-2, a0), (7, a0), (TICK - 1, a0 - 0.012), (TICK, a0 + 0.55 * pitch), (TICK + 1, a0 + 1.07 * pitch),
            (TICK + 2, a0 + 0.965 * pitch), (TICK + 3, a0 + 1.0 * pitch), (N + 3, a0 + 1.0 * pitch)]
    K.rot_keys(ew, 2, keys)
    # escape pinion + arbor
    pin = K.gear('escPinion', 8, 0.12, 0.09, 'pinion', 'disk', coll=C, mat=M['steel_pol'])
    pin.location = (0, 0, -0.13)
    K.rot_keys(pin, 2, keys)
    K.arbor('escArbor', 0, 0, -0.3, 0.2, 0.022, C, M)
    # fourth wheel meshing escape pinion (ticks with the train)
    d4 = D2R(152)
    c4 = Vector((cos(d4), sin(d4), 0)) * (0.9 + 0.12)
    fw = K.gear('fourth', 60, 0.9, 0.05, 'round', 'spokes', spokes=5, bend=0.5, coll=C, mat=M['brass'])
    fw.location = (c4.x, c4.y, -0.13)
    K.rot_keys(fw, 2, [(f, D2R(7) - (v - a0) * 8 / 60) for f, v in keys])
    K.arbor('arb4', c4.x, c4.y, -0.3, 0.2, 0.03, C, M)
    # pallet fork (anchor)
    D = r_tip * 1.42
    piv = empty('anchorPivot', (0, D, 0.0), C)
    amp = D2R(6.5)
    K.rot_keys(piv, 2, [(-2, -amp), (6, -amp), (TICK - 1, -amp * 0.72), (TICK, amp * 0.55), (TICK + 1, amp * 1.13),
                        (TICK + 2, amp * 0.96), (TICK + 3, amp), (TICK + 8, amp * 1.08), (N + 3, amp * 1.08)])
    for fc in [fc for fc in fcurves(piv) if fc.data_path == 'rotation_euler']:   # eased unlock / run-to-banking
        for kp in fc.keyframe_points:
            if kp.co[0] in (6, TICK - 1, TICK + 3, TICK + 8):
                kp.interpolation = 'BEZIER'
    parts = []
    for side in (-1, 1):
        wa = D2R(90 + side * 27)
        cp = Vector((r_tip * 0.98 * cos(wa), r_tip * 0.98 * sin(wa) - D, 0))    # contact point, pivot coords
        arm_end = cp * 1.0 + Vector((cos(wa), sin(wa), 0)) * 0.08
        # bowed arm (curved anchor, not a square frame): mid control point pushed outward
        mid = arm_end * 0.5 + Vector((cos(wa), sin(wa), 0)).cross(Vector((0, 0, 1))) * (-side * 0.06)
        parts.append(K.slab(f'arm{side}', K.band((0, 0), (mid.x, mid.y), (arm_end.x, arm_end.y), 0.075, 0.045), -0.02, 0.025, C, M['steel_pol'], 0.006))
        # ruby pallet stone, pointing at wheel centre (chamfered so its edges catch the key)
        st = K.slab(f'pallet{side}', [(-0.022, -0.09), (0.022, -0.09), (0.022, 0.07), (-0.022, 0.07)], -0.03, 0.03, C, M['ruby'], 0.0065)
        st.location = (cp.x + cos(wa) * 0.03, cp.y + sin(wa) * 0.03, 0)
        st.rotation_euler = (0, 0, wa - math.pi / 2 + side * D2R(8))
        parts.append(st)
    parts.append(K.slab('lever', K.stadium((0, 0), (0, 0.95), 0.07, 0.035), -0.02, 0.025, C, M['steel_pol'], 0.006))
    for side in (-1, 1):
        parts.append(K.slab(f'horn{side}', K.stadium((0, 0.95), (side * 0.085, 1.07), 0.035, 0.022), -0.02, 0.025, C, M['steel_pol'], 0.005))
    parts.append(K.cyl('anchorHub', 0.06, 0.1, (0, 0, 0), coll=C, mat=M['steel_pol']))
    parts.append(K.cyl('guardPin', 0.012, 0.09, (0, 0.9, 0.06), coll=C, mat=M['steel_pol']))
    for p_ in parts:
        p_.parent = piv
    K.arbor('anchorArbor', 0, D, -0.3, 0.2, 0.02, C, M)
    # balance (background, oscillating) at fork end
    bc = Vector((0, D + 1.65, 0.05))
    bal = K.ring_obj('balRim', 0.62, 0.7, -0.045, 0.045, C, M['gold'])
    bal.location = bc
    for k in range(3):
        a = TAU * k / 3
        arm = K.slab(f'balArm{k}', K.stadium((0, 0), (0.66 * cos(a), 0.66 * sin(a)), 0.05, 0.035), -0.02, 0.02, C, M['gold'], 0.004)
        arm.parent = bal
    for k in range(14):
        a = TAU * k / 14
        s = K.screw((0.7 * cos(a), 0.7 * sin(a), 0), 0.03, C, M['gold_pol'], normal_rot=(0, D2R(90), a))
        s.parent = bal
    K.rot_keys(bal, 2, [(f, D2R(150) * math.sin(TAU * (f - TICK) / 20.0)) for f in range(-2, N + 4)])
    # plate + bridges (plate ends at ~y 3.4 so the far field shows beyond it in haze)
    # plate pulled back out of the upper third (the haze window shows past its edge) and lowered out of focus
    K.slab('plate', [(1.8 * cos(TAU * k / 96), 1.8 * sin(TAU * k / 96) - 0.25) for k in range(96)], -0.6, -0.52, C, M['perlage'], 0.01)
    gen_r = K.mat_geneve('GeneveRough', (0.82, 0.64, 0.40), rough=(0.18, 0.4))     # top-edge glint stays < 0.75
    K.bridge_plate('escBridge', (0, 0), (-1.4, -0.35), 0.13, 0.2, 0.12, 0.06, C, M, gen_r, jewels=[(0, 0)], jsize=0.045)
    K.bridge_plate('palletBridge', (0, D), (-1.0, D + 0.55), 0.12, 0.17, 0.12, 0.06, C, M, gen_r, jewels=[(0, D)], jsize=0.04)
    K.bridge_plate('trainBridge', (c4.x, c4.y), (-2.4, 2.2), 0.14, 0.24, 0.12, 0.07, C, M, M['geneve'], jewels=[(c4.x, c4.y)], jsize=0.05)
    for p in ((c4.x, c4.y), (0, 0), (0, D)):
        K.jewel((p[0], p[1], -0.52), 0.05, C, M)
    scatter_screws(C, M, [(1.2, -0.6), (-1.2, -1.0), (0.9, 0.9), (-0.6, -1.5)], 14, 0.45, -0.52, 0.06, seed=5)
    # more wheels on the plate (density): a second train on the right
    fr2 = frame_empty('rightTrain', (1.75, 0.55, -0.22), Matrix.Identity(3), C)
    gear_chain(C, M, [{'t': 72, 'rp': 0.7, 'thick': 0.05, 'spokes': 5, 'mat': M['brass'], 'bend': 0.7},
                      {'t': 14, 'dir': 70, 'thick': 0.12, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
                      {'t': 54, 'rp': 0.5, 'coax': True, 'dz': 0.1, 'thick': 0.045, 'spokes': 4, 'mat': M['gold'], 'bend': 0.9}], fr2, N, -0.006, name='rt')
    # ---- camera: 3/4 from above, 85 mm, razor focus on the exit pallet contact
    tgt = Vector((0.08, 0.6, 0.0))
    p0 = K.orbit_pos(tgt, 24, 32, 2.75)
    p1 = K.orbit_pos(tgt, 21, 31, 2.55)
    contact = Vector((r_tip * cos(D2R(63)), r_tip * sin(D2R(63)), 0))
    cam = cam_basic('Cam1B', p0, tgt, 85, 1.8, (contact - p0).length)
    key_cam(cam, [(1, p0), (N, p1)], [(1, tgt), (N, tgt + Vector((0.02, 0.02, 0)))])
    K.key_focus(cam, [(1, (contact - p0).length), (N, (contact - p1).length)])
    # foreground occluder: out-of-focus wheel rim cutting the lower-left corner, very close to the lens
    f_, r_, u_ = K.cam_basis(p0, tgt)
    fg = K.gear('fgWheel', 70, 0.55, 0.05, 'round', 'spokes', spokes=5, coll=C, mat=M['brass'])
    fg.location = p0 + f_ * 0.95 + r_ * (-0.62) + u_ * (-0.3)
    fg.rotation_euler = (D2R(-20), D2R(10), 0)
    K.spin_linear(fg, 2, 1, N, 0.3, 0.004)
    # haze window: deeper level of wheels in luminous cyan haze, seen past the plate edge in the top third
    K.haze_window('win1B', M, N, p0, tgt, 85, C, ny=0.62, dist=(4.6, 8.5), width=7.0, height=3.0, count=34, density=0.2,
                  energy=36000, seed=23, glow=0.12)

    # motes: few near, most at subject depth / behind
    m1 = K.motes('motes', 260, (0.3, 0.6, 0.15), (2.2, 2.2, 0.5), (0.0007, 0.002), 3, C, M['mote'], cool_frac=0.15)
    K.drift(m1, 1, N, (0.002, 0.001, 0.001), 0.03)
    K.motes('motesFar', 900, (0.0, 5.0, 0.6), (6.0, 4.0, 2.0), (0.004, 0.01), 4, C, M['mote'], cool_frac=0.7)
    # ---- lights
    K.vol(light('SPOT', 'KeyRake', (-2.4, 2.2, 1.0), energy=300, color=(1.0, 0.56, 0.25), spot=40, blend=0.5, coll=C, target=(0.2, 0.4, 0.0)), 0.15)
    K.sheen_card(p0, tgt, 3.0, 1.2, 4, (1.0, 0.7, 0.42), C)
    K.vol(light('AREA', 'Fill', (2.4, -1.2, 0.9), energy=15, color=(1.0, 0.7, 0.45), size=1.5, coll=C, target=tgt), 0.0)
    # cool rim from behind and above: wheel top edges pick up cyan (ties them to the haze window)
    K.vol(light('AREA', 'RimCool', (0.4, 3.4, 2.0), energy=240, color=(0.45, 0.75, 1.0), size=1.2, coll=C, target=(0.1, 0.5, 0)), 0.0)
    glint = light('POINT', 'TickGlint', (contact.x + 0.15, contact.y - 0.2, 0.25), energy=0, color=(1.0, 0.75, 0.5), shadow_soft=0.02, coll=C)
    K.vol(glint, 0.0)
    K.key_energy(glint, [(TICK - 1, 0.0), (TICK + 1, 60.0), (TICK + 5, 0.0)])
    # micro jolt on the tick
    for fc in fcurves(cam):
        if fc.data_path == 'location' and fc.array_index == 2:
            m = fc.modifiers.new('NOISE'); m.scale = 1.2; m.strength = 0.006; m.use_restricted_range = True
            m.frame_start, m.frame_end = TICK, TICK + 5; m.blend_in, m.blend_out = 0.5, 4
    sc.camera = cam


# ============================================================================ 1C  balance wheel + hairspring
def shot_1C():
    sc, M, C = base('1C', fog=0.004, aniso=0.6, vol_end=30)
    N = SL['1C']['render_frames']
    A, PER, F0 = D2R(150), 18.0, 4.0          # a full visible swing happens inside the 14 cut frames
    theta = lambda f: A * math.sin(TAU * (f - F0) / PER)
    bal = empty('balance', (0, 0, 0), C)
    K.rot_keys(bal, 2, [(f, theta(f)) for f in range(-2, N + 4)])
    rim = K.ring_obj('rim', 0.74, 0.83, -0.05, 0.05, C, M['gold'], n=128)
    rim.parent = bal
    for k in range(3):
        a = TAU * k / 3 + 0.3
        arm = K.slab(f'arm{k}', K.stadium((0, 0), (0.78 * cos(a), 0.78 * sin(a)), 0.07, 0.045), -0.025, 0.025, C, M['gold'], 0.006)
        arm.parent = bal
    for k in range(18):
        a = TAU * k / 18
        s = K.screw((0.825 * cos(a), 0.825 * sin(a), 0), 0.034, C, M['gold_pol'], normal_rot=(0, D2R(90), a), rot_z=0.0)
        s.parent = bal
    for k in range(4):     # blued poising/timing screws (accents)
        a = TAU * k / 4 + 0.17
        s = K.screw((0.825 * cos(a), 0.825 * sin(a), 0), 0.036, C, M['blued'], normal_rot=(0, D2R(90), a), rot_z=0.0)
        s.parent = bal
    hub = K.cyl('hub', 0.1, 0.09, (0, 0, 0), coll=C, mat=M['gold'])
    hub.parent = bal
    roller = K.cyl('roller', 0.14, 0.03, (0, 0, -0.08), coll=C, mat=M['steel_pol'])
    roller.parent = bal
    ipin = K.cyl('impulsePin', 0.016, 0.07, (0.11, 0, -0.11), coll=C, mat=M['ruby'])
    ipin.parent = bal
    K.arbor('staff', 0, 0, -0.42, 0.3, 0.022, C, M)
    # hairspring ABOVE the arms, under the cock (breathing via shape keys); outer end/stud under the cock arm
    CK = D2R(150)                                   # cock arm direction (away from camera)
    angs = [D2R(a) for a in range(-180, 181, 30)]
    # hair-thin peacock-blue ribbon: gaps dominate (was a fat violet Slinky)
    hs = K.hairspring('hairspring', 0.1, 0.6, 16, 0.018, 0.005, C, M['blued'], 64, shape_angles=angs)
    hs.location = (0, 0, 0.11)
    hs.rotation_euler = (0, 0, CK)
    K.key_hairspring(hs, angs, [(f, theta(f)) for f in range(-2, N + 4)])
    K.cyl('collet', 0.065, 0.05, (0, 0, 0.11), coll=C, mat=M['steel_pol'])
    sp_ = Vector((0.6 * cos(CK), 0.6 * sin(CK), 0.11))
    stud = K.cyl('stud', 0.03, 0.09, tuple(sp_ + Vector((0, 0, 0.03))), coll=C, mat=M['steel_pol'])
    # balance cock with hero cap jewel (arm runs to the back-left, never between lens and balance)
    hero_ruby = K.mat_ruby('RubyHero', glow=0.05)
    cock_end = (1.35 * cos(CK), 1.35 * sin(CK))
    gen_cock = K.mat_geneve('GeneveCock', (0.49, 0.38, 0.24), stripe=0.035, rough=(0.2, 0.42))    # finer, darker stripes
    K.bridge_plate('cock', (0, 0), cock_end, 0.17, 0.3, 0.19, 0.07, C, M, gen_cock, jewels=[], ssize=0.09)
    jr, jc = K.jewel((0, 0, 0.26), 0.085, C, M, ruby_mat=hero_ruby)
    reg_end = (0.9 * cos(CK - 0.9), 0.9 * sin(CK - 0.9))
    K.slab('regulator', K.stadium((0, 0), reg_end, 0.11, 0.03), 0.26, 0.29, C, M['steel_pol'], 0.006)
    K.cyl('regPin', 0.022, 0.05, (reg_end[0], reg_end[1], 0.3), coll=C, mat=M['blued'])
    # glint: ruby emission spike + tiny light
    gn = hero_ruby.node_tree.nodes.get(hero_ruby['glow_node'])
    for f, v in ((-2, 0.05), (12, 0.05), (14, 1.6), (15, 0.8), (19, 0.05), (N + 3, 0.05)):      # brief glint, pinpoint only
        gn.inputs['To Min'].default_value = v
        gn.inputs['To Min'].keyframe_insert('default_value', frame=f)
    gl = light('POINT', 'Glint', (0.1, -0.16, 0.42), energy=0, color=(1.0, 0.3, 0.25), shadow_soft=0.01, coll=C)
    K.vol(gl, 0.0)
    K.key_energy(gl, [(12, 0.0), (14, 25.0), (19, 0.0)])
    # plate + other parts (plate ends so the far field shows in haze)
    # plate ends ~1.3 m beyond the balance along the view: the top quarter looks past its edge into the haze window
    K.slab('plate', [(1.6 * cos(TAU * k / 96), 1.6 * sin(TAU * k / 96) - 0.4) for k in range(96)], -0.5, -0.42, C, M['perlage'], 0.01)
    for p in ((0, 0), (-1.0, -1.1), (1.1, -0.2)):
        K.jewel((p[0], p[1], -0.42), 0.05, C, M)
    scatter_screws(C, M, [(1.0, -0.9), (-1.2, -0.5), (0.3, -1.6), (1.2, 0.3)], 12, 0.35, -0.42, 0.07, seed=8)
    fr = frame_empty('trainFrame', (1.45, -1.05, -0.25), Matrix.Identity(3), C)
    gear_chain(C, M, [{'t': 64, 'rp': 0.75, 'thick': 0.05, 'spokes': 5, 'mat': M['gold']},
                      {'t': 24, 'dir': 160, 'thick': 0.05, 'body': 'disk', 'mat': M['steel']},
                      {'t': 48, 'rp': 0.55, 'coax': True, 'dz': 0.12, 'thick': 0.05, 'mat': M['brass'], 'bend': 0.8}], fr, N, 0.004, name='tr')
    K.bridge_plate('trBridge', (1.45, -1.05), (2.3, -0.2), 0.13, 0.2, -0.05, 0.06, C, M, M['geneve_rh'], jewels=[(1.45, -1.05)], jsize=0.045)
    m1 = K.motes('motes', 450, (0.3, 0.0, 0.25), (2.4, 2.4, 0.5), (0.0008, 0.0025), 6, C, M['mote'])
    K.drift(m1, 1, N, (0.001, 0.002, 0.0015), 0.03)
    # camera: 3/4 from above, front-right; the whole balance in frame (rim, arms, screws), focus on the cap jewel
    tgt = Vector((0.0, 0.05, 0.05))
    p0 = K.orbit_pos(tgt, 30, 42, 5.0)
    p1 = K.orbit_pos(tgt, 27, 41, 4.8)
    fp = Vector((0.0, 0.0, 0.2))
    K.haze_window('win1C', M, N, p0, tgt, 85, C, ny=0.66, dist=(6.4, 10.0), width=8.0, height=3.0, count=36, density=0.2,
                  energy=40000, seed=33, light_from=(-1, 1), glow=0.04)
    cam = cam_basic('Cam1C', p0, tgt, 85, 2.0, (fp - p0).length)
    key_cam(cam, [(1, p0), (N, p1)], [(1, tgt + Vector((0.04, 0, 0))), (N, tgt)])
    K.key_focus(cam, [(1, (fp - p0).length), (N, (fp - p1).length)])
    # lights
    # key rakes low from the left (out of the cock specular lobe), grazing the rim screws and arms
    K.vol(light('SPOT', 'KeyRake', (-2.8, 0.5, 0.75), energy=260, color=(1.0, 0.62, 0.32), spot=45, blend=0.5, coll=C, target=(0.2, -0.1, 0.0)), 0.15)
    K.sheen_card(p0, tgt, 3.0, 1.1, 5, (1.0, 0.72, 0.45), C)
    K.vol(light('AREA', 'Fill', (2.6, -1.6, 1.0), energy=15, color=(1.0, 0.7, 0.45), size=1.5, coll=C, target=tgt), 0.0)
    K.vol(light('AREA', 'RimCool', (0.6, 3.0, 2.0), energy=260, color=(0.45, 0.75, 1.0), size=1.2, coll=C, target=(0, 0, 0)), 0.0)
    sc.camera = cam


# ============================================================================ 1D  lateral dolly across a train
def shot_1D():
    sc, M, C = base('1D', fog=0.004, aniso=0.6, vol_end=30, dof=dict(max_px=200.0, jitter=True, overblur=6.0))
    N = SL['1D']['render_frames']
    fr = frame_empty('train', (-2.4, 1.0, 0.0), Matrix.Identity(3), C)
    specs = [
        {'t': 80, 'rp': 0.9, 'thick': 0.06, 'spokes': 5, 'mat': M['brass'], 'bend': 0.0},
        {'t': 20, 'dir': -12, 'thick': 0.14, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
        {'t': 64, 'rp': 0.62, 'coax': True, 'dz': 0.2, 'thick': 0.05, 'spokes': 4, 'mat': M['gold'], 'bend': 0.9},
        {'t': 18, 'dir': 32, 'thick': 0.14, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
        {'t': 60, 'rp': 0.5, 'coax': True, 'dz': 0.2, 'thick': 0.05, 'spokes': 5, 'mat': M['brass']},
        {'t': 16, 'dir': -38, 'thick': 0.14, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
        {'t': 56, 'rp': 0.42, 'coax': True, 'dz': -0.2, 'thick': 0.045, 'spokes': 6, 'mat': M['steel'], 'bend': 0.7},
        {'t': 20, 'dir': 20, 'thick': 0.12, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
        {'t': 20, 'rp': 0.4, 'coax': True, 'dz': 0.15, 'thick': 0.04, 'style': 'club', 'spokes': 4, 'mat': M['gold'], 'bend': 0.9},
    ]
    ch = gear_chain(C, M, specs, fr, N, 0.0025, name='tr')
    centres = []
    for r in ch:
        if r['c'].xy[:] not in [c[:] for c in centres]:
            centres.append(r['c'].xy.copy())
    for i, c in enumerate(centres):
        w = fr.location + Vector((c.x, c.y, 0))
        K.arbor(f'arb{i}', w.x, w.y, -0.42, 0.62, 0.025, C, M)
        K.jewel((w.x, w.y, -0.36), 0.05, C, M)
    # bridges over the train
    W = [fr.location + Vector((c.x, c.y, 0)) for c in centres]
    K.bridge_plate('br1', W[1].xy, W[2].xy, 0.14, 0.14, 0.5, 0.07, C, M, M['geneve'], jewels=[W[1].xy, W[2].xy], jsize=0.045)
    K.bridge_plate('br2', W[3].xy, (W[3].x + 1.2, W[3].y + 1.0), 0.14, 0.22, 0.5, 0.07, C, M, M['geneve'], jewels=[W[3].xy], jsize=0.045)
    K.bridge_plate('br0', W[0].xy, (W[0].x - 0.6, W[0].y + 1.4), 0.18, 0.26, 0.42, 0.07, C, M, M['geneve_rh'], jewels=[W[0].xy], jsize=0.055)
    K.slab('plate', [(-5, -1.2), (5, -1.2), (5, 1.6), (-5, 1.6)], -0.44, -0.36, C, M['perlage'], 0.01)
    scatter_screws(C, M, [(c.x, c.y) for c in W], 22, 0.7, -0.36, 0.06, seed=9)
    # second (background) train lower and further back -> depth layer behind the hero train
    fb = frame_empty('trainBack', (-2.0, 3.2, -0.3), Matrix.Identity(3), C)
    gear_chain(C, M, [{'t': 96, 'rp': 1.1, 'thick': 0.06, 'spokes': 6, 'mat': M['gold'], 'bend': 0.8},
                      {'t': 22, 'dir': 8, 'thick': 0.12, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
                      {'t': 70, 'rp': 0.75, 'coax': True, 'dz': 0.15, 'thick': 0.05, 'spokes': 5, 'mat': M['brass']},
                      {'t': 18, 'dir': -10, 'thick': 0.12, 'style': 'pinion', 'body': 'disk', 'mat': M['steel_pol']},
                      {'t': 64, 'rp': 0.6, 'coax': True, 'dz': -0.15, 'thick': 0.05, 'spokes': 4, 'mat': M['rust'], 'bend': 0.6}],
               fb, N, -0.0018, name='tb')
    K.slab('plate2', [(-6, 2.6), (6, 2.6), (6, 5.0), (-6, 5.0)], -1.3, -1.22, C, M['perlage_dark'], 0.01)
    # camera: lateral dolly (left -> right) at 24 deg elevation, rack focus foreground pillar -> train -> back train
    t0, t1 = Vector((-1.05, 0.95, 0.2)), Vector((-0.05, 1.0, 0.2))
    p0 = K.orbit_pos(t0, 8, 19, 3.4)
    p1 = K.orbit_pos(t1, -2, 18, 3.3)
    cam = cam_basic('Cam1D', p0, t0, 100, 1.8, 2.4)
    key_cam(cam, [(1, p0), (N, p1)], [(1, t0), (N, t1)])
    for fc in fcurves(cam):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
    # foreground occluders: two DARK pillars swiping past close to the lens (soft silhouettes with a rim)
    f_, r_, u_ = K.cam_basis(p0, t0)
    for i, (s, x) in enumerate(((1.05, -0.13), (1.15, 1.05))):      # pillar 0 wipes out of frame by ~local 9
        base_p = p0 + f_ * s + Vector((x, 0, 0))
        K.cyl(f'pillar{i}', 0.035, 2.4, (base_p.x, base_p.y, base_p.z - 0.3), rot=(0, 0, 0), coll=C, mat=M['steel_dark'])
    # near layer for the rack: a big flat gold wheel whose teeth cross the lower third, ~2.3 m from the lens
    near_pt = p0 + f_ * 2.3 + u_ * (-0.35)        # lower: only tooth tips enter the bottom ~15%
    near_m = K.mat_brass_x('NearDark', (0.15, 0.10, 0.05), (0.05, 0.035, 0.02), (0.32, 0.55), 0.8, 0.6, scratch=0.4, edge=0.6)
    fg = K.gear('nearWheel', 110, 1.25, 0.06, 'round', 'spokes', spokes=6, bend=0.6, coll=C, mat=near_m)
    fg.location = (near_pt.x + 0.25, near_pt.y - 1.2, near_pt.z - 0.02)
    K.spin_linear(fg, 2, 1, N, 0.0, -0.004)
    # rack: near wheel teeth -> hero train (pinions/arbors)
    d_near = 2.3
    d_mid = (Vector((-0.4, 0.95, 0.3)) - (p0 + (p1 - p0) * 0.6)).length
    K.key_focus(cam, [(1, d_near), (12, d_mid), (N, d_mid)])          # train crisp by cut frame 6
    # far background field in haze
    tmid = (t0 + t1) * 0.5
    pmid = (p0 + p1) * 0.5
    K.haze_window('win1D', M, N, pmid, tmid, 100, C, ny=0.6, dist=(6.5, 10.5), width=11.0, height=3.2, count=44, density=0.2,
                  energy=30000, seed=43, glow=0.16)
    bg_field(C, M, N, tuple(pmid + K.view_dir(pmid, tmid, 100, 0.0, 0.7) * 6.0), (3.5, 0.8, 0.4), n_chains=4, seed=41,
             axis_rot=Euler((D2R(70), 0, 0)), size=(0.6, 1.3))
    m1 = K.motes('motes', 700, (0.0, 0.8, 0.3), (5.0, 2.0, 0.8), (0.0008, 0.0025), 9, C, M['mote'])
    K.drift(m1, 1, N, (0.001, 0.0, 0.0015), 0.0)
    K.motes('motesFar', 1000, (0.0, 5.0, 0.6), (8.0, 4.0, 2.0), (0.004, 0.012), 10, C, M['mote'], cool_frac=0.7)
    # lights
    tm = Vector((-0.2, 1.0, 0.0))
    K.vol(light('SPOT', 'KeyRake', (-3.6, 2.4, 1.3), energy=1100, color=(1.0, 0.56, 0.25), spot=40, blend=0.5, coll=C, target=tuple(tm)), 0.15)
    K.vol(light('SPOT', 'KeyRake2', (3.4, 2.6, 1.0), energy=420, color=(1.0, 0.66, 0.36), spot=40, blend=0.5, coll=C, target=tuple(tm)), 0.15)
    K.sheen_card(p0 + (p1 - p0) * 0.5, tm, 3.4, 1.4, 16, (1.0, 0.72, 0.45), C, size_y=0.7)
    # cool rim placed HIGH (z 3) so it rims edges but is not in the low camera's mirror direction (v8: every
    # horizontal face mirrored it -> silver/white gears)
    K.vol(light('AREA', 'RimCool', (0.5, 3.4, 2.4), energy=90, color=(0.45, 0.75, 1.0), size=1.4, coll=C, target=tuple(tm)), 0.0)
    sc.camera = cam


# ============================================================================ 1E  FPV flight -> head-on 6-spoke gear (T1)
MB_STEPS_1E = [(1, 3), (46, 8)]          # (from frame, eevee motion blur steps): flight 3 (curved path), spin-up 8


def _mb_steps_handler(sc_, *a):
    sc_ = bpy.context.scene
    tab = sc_.get('mb_steps_tab')
    if not tab:
        return
    f = sc_.frame_current
    st = None
    for f0, s in json.loads(tab):
        if f >= f0:
            st = s
    if st and sc_.eevee.motion_blur_steps != st:
        sc_.eevee.motion_blur_steps = st


def shot_1E():
    sc, M, C = base('1E', fog=0.004, aniso=0.6, vol_end=60, shutter=0.75, samples=32)
    N = SL['1E']['render_frames']
    try:
        sc.eevee.motion_blur_steps = 3
        sc.eevee.motion_blur_max = 256
    except Exception:
        pass
    # motion-blur steps cannot be keyed -> a frame-change handler switches 3 (flight) -> 8 (spin-up smear);
    # it runs for stills (frame_set) and for --anim renders alike.
    sc['mb_steps_tab'] = json.dumps(MB_STEPS_1E)
    bpy.app.handlers.frame_change_pre.append(_mb_steps_handler)
    try:
        for f, v in ((1, 0.3), (48, 0.3), (58, 0.75), (N, 0.75)):
            sc.render.motion_blur_shutter = v
            sc.keyframe_insert('render.motion_blur_shutter', frame=f)
    except Exception as e:
        print('[1E] shutter anim failed', e)
    LENS = 28.0
    Y_END = 36.0
    END_FLY = 54
    SPIN0, SPIN1 = 46, 60
    # ---- hero (T1 -> 2A): head-on, 6 spokes, D_tip ~ 95% frame height, clockwise on screen.
    # Read order matched to 2A's wheel: dark 'tyre' band (blackened teeth/rim) at 95%, a polished chrome lip at ~70%,
    # darker brass spokes, a ~13.5% gold castellated centre lock.
    spin = empty('heroSpin', (0, Y_END, 0), C)
    hero_brass = K.mat_brass_x('HeroBrass', (0.62, 0.45, 0.22), (0.26, 0.16, 0.07), (0.22, 0.42), 1.2, 0.4, scratch=0.3, edge=0.8)
    hero = K.gear('hero6', 48, 1.45, 0.24, 'round', 'spokes', spokes=6, spoke_w=0.17, rim_w=0.26, hub=0.2, coll=C, mat=hero_brass)
    hero.parent = spin
    hero.rotation_euler = (D2R(90), 0, 0)
    # dark tyre band: faces outside the spoke ends get the blackened steel slot
    hero.data.materials.append(M['black_steel'])
    inner_r = 1.45 - 1.3 * (2 * 1.45 / 48) - 0.26
    for p in hero.data.polygons:
        c = p.center
        if math.hypot(c.x, c.y) > inner_r + 0.08:
            p.material_index = 1
    D_tip = 2 * hero['r_tip']
    d_final = D_tip * LENS / (0.95 * 36.0 * 9 / 16)
    bz = K.ring_obj('heroBezel', 1.04, 1.12, -0.03, 0.03, C, M['steel_pol'], n=160, bev=0.008)
    bz.parent = spin; bz.rotation_euler = (D2R(90), 0, 0); bz.location = (0, -0.15, 0)
    col_ = K.ring_obj('heroCollar', 0.19, 0.23, -0.035, 0.035, C, M['steel_pol'], n=96, bev=0.006)
    col_.parent = spin; col_.rotation_euler = (D2R(90), 0, 0); col_.location = (0, -0.17, 0)
    nut = K.castle_nut('heroNut', 0.17, 0.075, 0.11, 14, C, M['gold_pol'])
    nut.parent = spin; nut.rotation_euler = (D2R(90), 0, 0); nut.location = (0, -0.14, 0)       # base at -0.14, top toward -Y
    K.cyl('heroArbor', 0.072, 0.2, (0, 0, 0), rot=(D2R(90), 0, 0), coll=C, mat=M['steel_dark']).parent = spin
    bpy.data.objects['heroArbor'].location = (0, -0.18, 0)
    # spin: slow, then hard ease-in from SPIN0 to 26 deg/frame at SPIN1 (stays < 30 -> reads clockwise, no reversal)
    ang = 0.0
    keys = []
    for f in range(-2, N + 4):
        t = max(0.0, min(1.0, (f - SPIN0) / float(SPIN1 - SPIN0)))
        w = D2R(0.4) + (D2R(26.0) - D2R(0.4)) * (t ** 2.2)
        ang += w
        keys.append((f, ang))
    K.rot_keys(spin, 1, keys)
    # ---- the corridor of mechanism the camera threads through (now runs all the way to the hero)
    y_cam_end = Y_END - d_final

    def path_xz(y):
        dec = 1.0 - K.ease((y - 18.0) / (y_cam_end - 4.0 - 18.0))
        return 0.75 * math.sin(y * 0.33) * dec, 0.4 * math.sin(y * 0.27 + 1.0) * dec
    rnd = random.Random(5)
    gate_ys = [4.0, 8.5, 12.5, 16.5, 20.5, 24.5, 27.2, 29.6]
    for i, gy in enumerate(gate_ys):
        px, pz = path_xz(gy)
        R = rnd.uniform(1.1, 1.9)
        side = 1 if i % 2 == 0 else -1
        ang_off = rnd.uniform(-0.5, 0.5)
        off = Vector((side * math.cos(ang_off), 0, math.sin(ang_off))) * (R * 1.07 + 0.32)
        fr = frame_empty(f'gate{i}', (px + off.x, gy, pz + off.z), Matrix.Rotation(D2R(90), 3, 'X'), C)
        t0 = int(R * 34)
        gear_chain(C, M, [{'t': t0, 'rp': R, 'thick': 0.16, 'spokes': rnd.choice([4, 5, 6]), 'mat': rnd.choice([M['brass'], M['gold'], M['rust']]), 'bend': rnd.choice([0, 0.8])},
                          {'t': rnd.randint(16, 30), 'dir': (90 if side > 0 else 270) + rnd.uniform(-40, 40), 'thick': 0.14, 'mat': M['steel'], 'spokes': 5}],
                   fr, N, side * 0.012, name=f'gt{i}_')
    # through-the-window wheel: camera passes through a spoke window at y=14.5
    wy = 14.5
    px, pz = path_xz(wy)
    big = K.gear('windowWheel', 120, 2.6, 0.18, 'round', 'spokes', spokes=5, spoke_w=0.28, rim_w=0.26, hub=0.45, coll=C, mat=M['brass_big'])
    big.location = (px, wy, pz - 1.45)
    big.rotation_mode = 'XYZ'
    big.rotation_euler = (D2R(90), 0, 0)
    # ceiling / floor gears (horizontal) + arbors + beams + posts for density (all end behind the final camera)
    for i in range(19):
        y = 2.0 + i * 1.6 + rnd.uniform(-0.4, 0.4)
        y = min(y, y_cam_end - 0.8)
        px, pz = path_xz(y)
        up = 1 if i % 2 == 0 else -1
        R = rnd.uniform(0.6, 1.6)
        fr = frame_empty(f'cf{i}', (px + rnd.uniform(-1.4, 1.4), y, pz + up * rnd.uniform(0.75, 1.1)), Matrix.Rotation(rnd.uniform(-0.2, 0.2), 3, 'Y'), C)
        gear_chain(C, M, [{'t': int(R * 40), 'rp': R, 'thick': 0.08, 'spokes': rnd.choice([4, 5, 6]), 'mat': rnd.choice([M['brass'], M['gold'], M['steel']])},
                          {'t': rnd.randint(14, 36), 'dir': rnd.uniform(0, 360), 'thick': 0.08, 'mat': rnd.choice([M['brass'], M['steel']]), 'dz': up * 0.12}],
                   fr, N, rnd.choice([-1, 1]) * 0.02, name=f'cf{i}_')
        zz = fr.location.z; K.arbor(f'cfa{i}', fr.location.x, fr.location.y, min(zz, zz + up * 2.2), max(zz, zz + up * 2.2), 0.035, C, M)
    # beams and posts: low-frequency materials (Geneve stripes / mirror posts broke into a knitted ladder under
    # vector motion blur at flight speed)
    for i in range(9):
        y = 3.0 + i * 3.3
        px, pz = path_xz(y)
        z = pz + (1.35 if i % 2 else -1.35)
        b = K.slab(f'beam{i}', K.stadium((-3.5, 0), (3.5, 0), 0.16, 0.16), -0.05, 0.05, C, M['brass'], 0.015)
        b.location = (px, y, z)
        b.rotation_euler = (D2R(90), 0, 0)
        for k in range(4):
            K.jewel((px - 2.4 + 1.6 * k, y - 0.06, z), 0.045, C, M, normal_rot=(D2R(90), 0, 0))
    for i in range(12):
        y = 2.5 + i * 2.5
        px, pz = path_xz(y)
        x = px + (1 if i % 2 else -1) * rnd.uniform(1.0, 1.6)
        K.cyl(f'post{i}', 0.06, 5.0, (x, y, pz), coll=C, mat=M['steel'])
    for i in range(4):
        K.motes(f'motes{i}', 900, (0, 4 + i * 7, 0), (4, 7, 3), (0.0015, 0.005), 20 + i, C, M['mote'])
    K.haze('corridorHaze', (0, 15.5, 0), (9.0, 31.0, 6.0), 0.03, (0.5, 0.72, 0.95), 0.5, 3.0)
    # walls: side walls run to y~33 (out of the 28 mm frustum at the end), ceiling/floor walls to y~36
    for sx in (-1, 1):
        K.gear_wall(f'wall1E{sx}', M, 1, N, (sx * 3.6, 16.5, 0.0), (0.8, 33.0, 5.0), 55, seed=50 + sx, facing=(0, D2R(90), 0), coll=C, radii=(0.5, 1.5))
    for sz in (-1, 1):
        K.gear_wall(f'wallV1E{sz}', M, 1, N, (0.0, 26.0, sz * 2.9), (6.0, 18.0, 0.6), 20, seed=60 + sz, facing=(0, 0, 0), coll=C, radii=(0.5, 1.3))
    # ---- camera path (speed ramp: cruise -> fast -> brake from t~0.8 into the head-on hold)
    vel = []
    for f in range(1, END_FLY + 1):
        if f <= 44:
            v = 0.4 + 1.0 * K.ease((f - 12) / 32.0)
        else:
            v = 1.4 * (1.0 - K.ease((f - 44) / 10.0))
        vel.append(max(v, 0.0))
    s = [0.0]
    for v in vel[1:]:
        s.append(s[-1] + v)
    scale = (y_cam_end - 0.0) / s[-1]
    ys = {f: s[f - 1] * scale for f in range(1, END_FLY + 1)}

    def ypos(f):
        if f <= 1:
            return ys[1] + (f - 1) * vel[0] * scale
        if f >= END_FLY:
            return y_cam_end
        a = int(math.floor(f)); b = a + 1
        return ys[a] + (ys[b] - ys[a]) * (f - a)

    def pos(f):
        y = ypos(f)
        x, z = path_xz(y)
        return Vector((x, y, z))
    fpass = min(range(1, END_FLY), key=lambda f: abs(ypos(f) - wy))

    def cam_fn(f):
        p = pos(f)
        fwd = (pos(f + 1.0) - pos(f - 1.0))
        if fwd.length < 1e-4:
            fwd = Vector((0, 1, 0))
        fwd.normalize()
        blend = K.ease((f - (END_FLY - 11)) / 10.0)
        fwd = (fwd * (1 - blend) + Vector((0, 1, 0)) * blend).normalized()
        acc = pos(f + 1.5) - 2 * pos(f) + pos(f - 1.5)
        roll = max(-0.45, min(0.45, -acc.x * 2.2)) * (1 - blend)
        q = K.look_quat(p, p + fwd, roll)
        if f >= END_FLY:
            q = K.look_quat(p, p + Vector((0, 1, 0)))
        return p, q
    cam = cam_basic('Cam1E', pos(1), pos(2), LENS, 2.8, 3.0)
    K.key_cam_path(cam, list(range(-2, N + 4)), cam_fn)
    big.rotation_mode = 'XYZ'
    fc_key(big, 'rotation_euler', 1, [(f, -(D2R(90) + 0.012 * (f - fpass))) for f in (-2, N + 3)], interp='LINEAR')
    K.key_focus(cam, [(1, 2.5), (END_FLY - 12, 3.0), (END_FLY - 2, d_final - 0.1), (N, d_final - 0.1)])
    for f in (30, 40, 44, 48, 52, 54):
        dist = Y_END - ypos(f)
        print(f'[1E] f{f} y {ypos(f):.2f} hero height {D_tip * LENS / (dist * 20.25) * 100:.0f}%')
    # ---- lights: warm practical pools along the corridor (dimmer, softer), cyan haze from the sides, hero key
    for i in range(7):
        y = 3 + i * 4.2
        px, pz = path_xz(y)
        K.vol(light('POINT', f'warm{i}', (px + (1.7 if i % 2 else -1.7), y + 0.5, pz + 1.5), energy=150, color=(1.0, 0.62, 0.32), shadow_soft=0.8, coll=C), 0.4)
    for i in range(5):
        y = 4 + i * 6.5
        hl = light('SPOT', f'haze{i}', ((-7 if i % 2 else 7), y - 0.5, 4.0), energy=30000, color=(0.5, 0.78, 1.0), spot=26, blend=0.6, coll=C, target=(0, y, 0))
        hl.data.use_shadow = False      # gear-wall teeth shadows in the haze aliased into a blocky froxel 'knit' pattern
    hk = light('AREA', 'HeroKey', (-2.8, Y_END - 2.2, 2.6), energy=600, color=(1.0, 0.66, 0.36), size=1.0, coll=C, target=(0, Y_END, 0))
    hr = light('AREA', 'HeroRim', (2.6, Y_END + 1.2, 1.8), energy=700, color=(1.0, 0.75, 0.45), size=0.6, coll=C, target=(0, Y_END, 0))
    hc = light('AREA', 'HeroCool', (1.5, Y_END - 2.0, -2.6), energy=200, color=(0.5, 0.75, 1.0), size=1.0, coll=C, target=(0, Y_END, 0))
    hs_ = light('AREA', 'HeroSheen', (0.0, Y_END - d_final - 1.5, 1.2), energy=260, color=(1.0, 0.78, 0.55), size=2.5, size_y=0.6, coll=C, target=(0, Y_END, 0))
    for lt in (hk, hr, hc, hs_):
        K.vol(lt, 0.0)
    # two faint warm vertical haze strips behind the hero at screen x ~25% / 75% (pre-echo 2A's strip lights)
    ys_ = Y_END + 2.5
    xs_ = 0.5 * (ys_ - y_cam_end) * (18.0 / LENS)
    for sx in (-1, 1):
        K.haze(f'strip{sx}', (sx * xs_, ys_, 0.0), (0.22, 0.22, 6.0), 0.35, (1.0, 0.8, 0.6), 0.3, 6.0, contrast=(0.25, 0.7))
        st = light('SPOT', f'stripL{sx}', (sx * xs_, ys_, 4.5), energy=900, color=(1.0, 0.62, 0.32), spot=6, blend=0.3, coll=C, target=(sx * xs_, ys_, -3.0))
        K.vol_only(st)
    sc.camera = cam
    print('[1E] d_final', d_final, 'D_tip', D_tip, 'fpass', fpass)


# ============================================================================ 6A  title
def shot_6A():
    sc, M, C = base('6A', fog=0.003, aniso=0.6, vol_end=40)
    N = SL['6A']['render_frames']
    cu = bpy.data.curves.new('TitleCurve', 'FONT')
    cu.body = 'ESCAPEMENT'
    cu.font = bpy.data.fonts.load(r'C:/Windows/Fonts/bahnschrift.ttf', check_existing=True)
    cu.size = 0.15
    cu.space_character = 1.6
    cu.extrude = 0.035
    cu.offset = 0.0035         # heavier strokes (Bahnschrift Regular read as a thin flat 2D font)
    cu.bevel_depth = 0.0       # curve bevel mitres the acute V of the M into a light spike -> mesh bevel instead
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    tcu = bpy.data.objects.new('TitleCurve', cu)
    link(tcu, C)
    bpy.context.view_layer.update()
    tme = bpy.data.meshes.new_from_object(tcu.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    cu.offset = 0.0012
    bpy.context.view_layer.update()
    tme_thin = bpy.data.meshes.new_from_object(tcu.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tcu)
    import bmesh as _bm

    def islands(bm):
        bm.faces.ensure_lookup_table()
        seen, out = set(), []
        for f0 in bm.faces:
            if f0.index in seen:
                continue
            stack, isl = [f0], []
            seen.add(f0.index)
            while stack:
                f = stack.pop()
                isl.append(f)
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index not in seen:
                            seen.add(g.index); stack.append(g)
            out.append(isl)
        out.sort(key=lambda isl: sum(f.calc_center_median().x for f in isl) / len(isl))
        return out

    def keep_letters(me, keep):
        b2 = _bm.new(); b2.from_mesh(me)
        _bm.ops.remove_doubles(b2, verts=b2.verts, dist=1e-6)
        isl = islands(b2)
        kill = [f for i, fs in enumerate(isl) if not keep(i, len(isl)) for f in fs]
        _bm.ops.delete(b2, geom=kill, context='FACES')
        b2.to_mesh(me); b2.free()
    M_IDX = 6     # E S C A P E [M] E N T
    keep_letters(tme, lambda i, n: not (n == 10 and i == M_IDX))
    keep_letters(tme_thin, lambda i, n: (n == 10 and i == M_IDX))
    bm = _bm.new(); bm.from_mesh(tme); bm.from_mesh(tme_thin)
    bm.to_mesh(tme); bm.free()
    title = bpy.data.objects.new('Title', tme)
    link(title, C)
    shade(title, 30)
    tbev = bevel(title, 0.009, 4, 30)
    tbev.use_clamp_overlap = True
    title.rotation_euler = (D2R(90), 0, 0)
    tb = K.mat_brass_x('TitleBrass', (1.0, 0.74, 0.40), (0.62, 0.40, 0.16), (0.12, 0.26), 6.0, 0.1, scratch=0.2, ao=False)
    try:
        tb.node_tree.nodes['Principled BSDF'].inputs['Anisotropic'].default_value = 0.6
    except Exception:
        pass
    set_mat(title, tb)
    bpy.context.view_layer.update()
    W = title.dimensions.x
    d = W / (0.64 * 36.0 / 85.0)
    # hairline rule under the title (polished steel) + two tiny blued screws at its ends
    rule_m = K.mat_steel_x('RuleSteel', (0.62, 0.62, 0.64), (0.22, 0.3), 2.0)       # rougher: its glint stays < 0.75
    bar = K.slab('rule', [(-W * 0.3, -0.0016), (W * 0.3, -0.0016), (W * 0.3, 0.0016), (-W * 0.3, 0.0016)], -0.003, 0.003, C, rule_m, 0.0008)
    bar.rotation_euler = (D2R(90), 0, 0)
    bar.location = (0, 0.0, -0.135)
    # turning gears behind (defocused): a big wheel slightly off-centre + its train, and a far field
    K.gear_wall('wall6A', M, 1, N, (0.0, 5.5, 0.0), (9.0, 2.5, 4.5), 46, seed=66, coll=C, radii=(0.3, 0.9))
    # trains tilted off the lens axis: faces mirror darkness instead of the title key -> only edges/teeth glint
    fr = frame_empty('bgTrain', (0.75, 3.2, -0.2), Matrix.Rotation(D2R(-28), 3, 'Z') @ Matrix.Rotation(D2R(90 + 22), 3, 'X'), C)
    gear_chain(C, M, [{'t': 96, 'rp': 1.45, 'thick': 0.08, 'spokes': 6, 'mat': M['brass'], 'bend': 0.8},
                      {'t': 40, 'dir': 165, 'thick': 0.07, 'spokes': 5, 'mat': M['steel']},
                      {'t': 30, 'dir': 230, 'thick': 0.07, 'spokes': 5, 'mat': M['gold']},
                      {'t': 52, 'dir': -40, 'thick': 0.07, 'spokes': 4, 'mat': M['rust']}], fr, N, 0.003, name='tt')
    fr2 = frame_empty('bgTrain2', (-1.6, 2.6, 0.4), Matrix.Rotation(D2R(30), 3, 'Z') @ Matrix.Rotation(D2R(90 - 18), 3, 'X'), C)
    gear_chain(C, M, [{'t': 80, 'rp': 1.0, 'thick': 0.07, 'spokes': 5, 'mat': M['gold'], 'bend': 0.6},
                      {'t': 24, 'dir': -60, 'thick': 0.07, 'body': 'disk', 'mat': M['steel']}], fr2, N, -0.004, name='tu')
    bg_field(C, M, N, (0.0, 6.0, 0.0), (5.0, 1.5, 1.5), n_chains=5, seed=61, size=(1.0, 2.2))
    K.haze('haze', (0.0, 6.5, 0.0), (14.0, 7.0, 6.0), 0.08, (0.45, 0.7, 0.95), 0.5, 2.0)
    m1 = K.motes('motes', 60, (0, -0.12, 0.02), (W * 1.2, 0.35, 0.28), (0.0004, 0.0012), 61, C, M['mote'], cool_frac=0.1)
    K.drift(m1, 1, N, (0.0012, 0.0, 0.0012), 0.02)
    K.motes('motesFar', 700, (0, 3.5, 0.3), (8, 4, 3), (0.004, 0.01), 62, C, M['mote'], cool_frac=0.6)
    # ---- lights (everything dies over the last 16 cut frames: 51 -> 66)
    # 1) reflected sweep: a tall thin area light BEHIND the camera travels L->R; the mirror-like letter faces
    #    reflect it as a bright band crossing the word (analytic light specular, no screen-space limits)
    k_ = (2 * d + 1.2) / d
    strip = light('AREA', 'SweepStrip', (-W * 0.62 * k_, -d - 1.2, 0.05), energy=0, color=(1.0, 0.82, 0.6), size=0.22, size_y=3.0, coll=C)
    K.vol(strip, 0.0)
    try:
        strip.data.diffuse_factor = 0.25
    except Exception:
        pass
    track_to(strip, empty('stripT', (0, 0, 0), C))
    key_vec(strip, 'location', [(16, (-W * 0.62 * k_, -d - 1.2, 0.05)), (40, (W * 0.62 * k_, -d - 1.2, 0.05))], interp='BEZIER')
    K.key_energy(strip, [(12, 0.0), (16, 140.0), (40, 140.0), (44, 110.0), (56, 110.0), (64, 0.0)])
    # 2) raking sweep: steep top-down spot travelling with the strip; grazes the letter tops/bevels and its beam
    #    goes down past the title (never onto the gear world behind)
    tgt = empty('sweepT', (0, 0, 0), C)
    sw = light('SPOT', 'Sweep', (-W, -0.1, 0.7), energy=0, color=(1.0, 0.68, 0.36), spot=26, blend=0.7, shadow_soft=0.02, coll=C)
    K.vol(sw, 0.1)
    track_to(sw, tgt)
    key_vec(sw, 'location', [(16, (-W * 0.65, -0.12, 0.7)), (40, (W * 0.65, -0.12, 0.7))], interp='BEZIER')
    key_vec(tgt, 'location', [(16, (-W * 0.55, 0.03, -0.1)), (40, (W * 0.55, 0.03, -0.1))], interp='BEZIER')
    K.key_energy(sw, [(13, 0.0), (18, 120.0), (40, 120.0), (46, 30.0), (56, 30.0), (64, 0.0)])
    hold = K.vol(light('AREA', 'HoldCard', (0.0, -d - 1.6, 0.25), energy=0, color=(1.0, 0.8, 0.56), size=2.2, size_y=0.5, coll=C,
                       target=(0, 0, 0)), 0.0)
    try:
        hold.data.diffuse_factor = 0.2
    except Exception:
        pass
    K.key_energy(hold, [(36, 0.0), (44, 42.0), (56, 42.0), (64, 0.0)])
    # 3) soft warm key from top-left front (faces read as warm metal) + cool rim on the top edges
    key = K.vol(light('AREA', 'Key', (-1.2, -d * 0.7, 1.6), energy=0, color=(1.0, 0.64, 0.32), size=1.2, coll=C, target=(0, 0, 0)), 0.0)
    K.key_energy(key, [(10, 0.0), (24, 30.0), (40, 60.0), (56, 60.0), (64, 0.0)])
    rim = K.vol(light('AREA', 'RimCool', (0.0, 0.8, 1.0), energy=0, color=(0.45, 0.75, 1.0), size=2.5, size_y=0.3, coll=C, target=(0, 0, 0)), 0.0)
    K.key_energy(rim, [(1, 25.0), (56, 50.0), (64, 0.0)])
    # 4) gear world behind: warm raking key + cyan haze shaft from the side (never into the lens)
    # gear world lit from BEHIND-left, grazing: only tooth edges / rims glint, faces stay dark
    gk = K.vol(light('SPOT', 'GearKey', (-3.2, 5.0, 2.0), energy=500, color=(1.0, 0.58, 0.27), spot=50, blend=0.5, coll=C, target=(0.5, 2.4, -0.2)), 0.1)
    K.key_energy(gk, [(1, 700.0), (20, 500.0), (56, 450.0), (66, 0.0)])
    # warm edge rim on the gear world from behind-right/top: teeth and rims glint, faces stay dark
    grim = K.vol(light('AREA', 'GearRim', (2.6, 4.6, 2.4), energy=260, color=(1.0, 0.62, 0.3), size=1.2, coll=C, target=(0.2, 2.2, -0.2)), 0.0)
    K.key_energy(grim, [(1, 260.0), (20, 200.0), (56, 200.0), (66, 0.0)])
    hz = K.vol_only(light('SPOT', 'HazeShaft', (5.0, 6.0, 6.0), energy=80000, color=(0.5, 0.78, 1.0), spot=34, blend=0.5, coll=C, target=(-1.0, 5.0, -0.5)))
    # cool haze sheet between the title and the gear world -> atmospheric separation behind the letters
    K.haze('hazeMid', (0.0, 1.6, 0.0), (8.0, 1.2, 5.0), 0.05, (0.45, 0.7, 0.95), 0.5, 2.5)
    K.vol_only(light('SPOT', 'HazeMidLight', (-4.0, 1.6, 3.0), energy=6000, color=(0.5, 0.78, 1.0), spot=40, blend=0.6, coll=C, target=(0.5, 1.6, 0.0)))
    K.key_energy(hz, [(1, 60000.0), (56, 60000.0), (66, 0.0)])
    # exposure also dies in the last 16 cut frames (belt and braces: fully black by cut out 66)
    vs = sc.view_settings
    for f, v in ((1, 0.0), (56, 0.0), (66, -8.0)):
        vs.exposure = v
        vs.keyframe_insert('exposure', frame=f)
    # camera: frontal, slow push + drift; opens focused on the gears (T5 macro gears), racks to the title
    # yaw drift (~7 deg -> ~2 deg) so the extruded sides and bevels catch the strip as it crosses
    p0, p1 = Vector((-0.62, -d - 0.35, 0.03)), Vector((0.2, -d, 0.0))
    cam = cam_basic('Cam6A', p0, (0, 0, 0), 85, 2.0, d)
    key_cam(cam, [(1, p0), (N, p1)], [(1, Vector((-0.03, 0, -0.01))), (N, Vector((0.0, 0, 0)))])
    dt = lambda f: (p0 + (p1 - p0) * ((f - 1) / (N - 1))).length
    K.key_focus(cam, [(1, d + 1.9), (8, d + 1.85), (18, dt(18)), (N, dt(N))])
    # after the rack the aperture opens up: the gear world behind the word melts into soft shapes
    cd_ = cam.data.dof
    for f, v in ((1, 2.0), (16, 2.0), (26, 1.4), (N, 1.4)):
        cd_.aperture_fstop = v
        cd_.keyframe_insert('aperture_fstop', frame=f)
    sc.camera = cam
    print('[6A] title width', W, 'cam dist', d)


SHOTS = {'1A': shot_1A, '1B': shot_1B, '1C': shot_1C, '1D': shot_1D, '1E': shot_1E, '6A': shot_6A}

if __name__ == '__main__':
    ids = str(arg('--shot', '1A')).split(',')
    for sid in ids:
        import time
        t0 = time.time()
        SHOTS[sid]()
        print(f'[act1] built {sid} in {time.time() - t0:.1f}s', flush=True)
        ov = arg(f'--st{sid}', None)          # per-shot stills override when several shots run together
        if ov and '--stills' in sys.argv:
            sys.argv[sys.argv.index('--stills') + 1] = str(ov)
        finish(sid)
        print(f'[act1] {sid} total {time.time() - t0:.1f}s', flush=True)
