"""ACT IV - THE SANCTUM. Shots 4A 4B 4C 4D 4E 4F.

  --shot 4F --stills 7,40,72            normal (finish(shot))
  --multi "4F:40,72;4B:10,60"           several shots in one Blender session (same build)
"""
import sys, os, time
try:
    sys.stdout.reconfigure(line_buffering=True)     # progress visible through rb.py's pipe
except Exception:
    pass
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import numpy as np
import tmat, temple, tclouds, tbillow
from tgeo import *

T0 = time.time()
SHOTS = {'4A': 72, '4B': 72, '4C': 28, '4D': 28, '4E': 28, '4F': 78}
# per-shot sun: (elevation, azimuth [0 = sun in -Y, 90 = sun in -X], energy, color, sky strength)
GOLD = (1.0, 0.64, 0.36)
GLOW = {'4A': 1.1, '4B': 0.7, '4F': 0.45, '4C': 0.5, '4E': 0.5}
_cur_shot = ['4F']
COVER = {'4A': 0.0, '4B': 0.35, '4F': 0.5, '4C': 0.45, '4D': 0.45, '4E': 0.5}
# revision r1 (director QC: every still WASHED OUT): sky fill roughly halved, sun +20% -> key:fill ~6:1
SUNS = {'4F': (12.0, 62.0, 7.2, (1.0, 0.55, 0.28), 0.35), '4B': (16.0, 42.0, 7.8, (1.0, 0.56, 0.27), 0.35),
        '4A': (8.0, 25.0, 5.5, (1.0, 0.5, 0.2), 0.22),
        '4C': (9.0, 122.0, 7.8, GOLD, 0.35), '4D': (14.0, 50.0, 7.8, GOLD, 0.35), '4E': (30.0, 172.0, 7.8, GOLD, 0.35)}
CLOUD_SHADOW = (0.10, 0.12, 0.30)
EXPO = {'4A': -0.6, '4B': -0.8, '4D': -0.15}

# sun: low golden hour from the south-west (behind-left of the axial camera)
SUN_EL = 14.0
SUN_OFF = 40.0
_el, _az = math.radians(SUN_EL), math.radians(SUN_OFF)
SUN_DIR = Vector((-math.sin(_az) * math.cos(_el), -math.cos(_az) * math.cos(_el), math.sin(_el)))
SKY_ROT = math.degrees(math.atan2(-SUN_DIR.y, SUN_DIR.x))

shot_arg = arg('--shot', '4F')
multi = arg('--multi', None)
need = set(s.split(':')[0] for s in multi.split(';')) if multi else {shot_arg}
want_clouds_a = '4A' in need
want_temple = bool(need & {'4B', '4C', '4D', '4E', '4F', 'SUNCHECK'})

reset()
sc = setup_render(1, 78, samples=24, vol_tile='8', vol_samples=64, vol_end=600.0, vol_start=0.5,
                  look='AgX - Medium High Contrast')
sc.eevee.use_shadows = True
try:
    sc.eevee.shadow_resolution_scale = 1.0
except Exception:
    pass
compositor(bloom=0.28, threshold=1.2, bloom_size=0.7, dispersion=0.004)

# art-directed sky (the physical sky read pale/overcast): deep zenith blue, warm horizon, sun glow + cumulus
world, sky, bg = tmat.world_sky_clouds(sun_elev=SUN_EL, sun_az=SKY_ROT, strength=1.0, cloud_cover=0.5, cloud_scale=1.4,
                                       sun_dir=tuple(SUN_DIR), fog=None, haze=0.0, cloud_gain=1.9,
                                       gradient=((0.035, 0.11, 0.42), (0.42, 0.5, 0.62), (1.0, 0.55, 0.22)))
# NOTE: EEVEE world volumes are infinite and swallow sky + sun -> use a bounded haze box instead
C_H = collection('HAZE')
haze_mat = mat_volume('T_Haze', density=0.00055, color=(0.85, 0.9, 1.0), anisotropy=0.6)
haze_box = prim('cube', 'HazeBox', loc=(0, 0, 60), scale=(1400, 1400, 280), coll=C_H, smooth=False)
set_mat(haze_box, haze_mat)
# low courtyard mist (4F): makes the cypress/colonnade shadows read as sun shafts
mist_mat = mat_volume('T_Mist', density=0.0013, color=(1.0, 0.95, 0.88), anisotropy=0.35)
mist_box = prim('cube', 'MistBox', loc=(0, -40, 7), scale=(130, 170, 14), coll=C_H, smooth=False)
set_mat(mist_box, mist_mat)
sun = light('SUN', 'Sun', tuple(SUN_DIR * 100), energy=7.5, color=(1.0, 0.72, 0.45), size=0.6, target=(0, 0, 0))
try:
    sun.data.shadow_maximum_resolution = 0.002
except Exception:
    pass


def set_haze(d, aniso=None):
    vp = [n for n in haze_mat.node_tree.nodes if n.type == 'PRINCIPLED_VOLUME'][0]
    vp.inputs['Density'].default_value = d
    if aniso is not None:
        vp.inputs['Anisotropy'].default_value = aniso


def sun_vec(el, az):
    e, a = math.radians(el), math.radians(az)
    return Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def set_sun(el, az, energy=None, color=None, sky=None, cover=None):
    """Per-shot sun (a dream may cheat continuity): light, sky glow, cloud-layer shading, cloud materials."""
    d = sun_vec(el, az)
    sun.location = tuple(d * 100)
    look_at(sun, (0, 0, 0))
    if energy is not None:
        sun.data.energy = energy
    if color is not None:
        sun.data.color = color
    nt = world.node_tree
    n = nt.nodes.get('SunDot')
    if n:
        n.inputs[1].default_value = tuple(d)
    nrm = math.hypot(d.x, d.y) or 1.0
    for nm, comp in (('SunOffX', d.x), ('SunOffY', d.y)):
        n = nt.nodes.get(nm)
        if n:
            n.inputs[1].default_value = 0.06 * comp / nrm
    if sky is not None:
        bg.inputs['Strength'].default_value = sky
    n = nt.nodes.get('GlowWide')
    if n:
        n.inputs[1].default_value = GLOW.get(_cur_shot[0], 0.6)
    n = nt.nodes.get('CloudMask')
    if n and cover is not None:
        thr = 0.66 - cover * 0.2
        n.inputs['From Min'].default_value = thr
        n.inputs['From Max'].default_value = thr + 0.12
    for m in bpy.data.materials:
        if m.node_tree:
            n = m.node_tree.nodes.get('CloudSunDot')
            if n:
                n.inputs[1].default_value = tuple(-x for x in d)
            n = m.node_tree.nodes.get('CloudSunN')
            if n:
                n.inputs[1].default_value = tuple(d)
    return d

C_T = collection('TEMPLE')
C_A = collection('DECK4A')
C_B = collection('DECK4B')

mats = temple.make_materials()
mats['htile'] = tmat.m_attr_tiles('T_HeroTileMat')
_sd = sun_vec(*SUNS['4B'][:2])
mats['cloud'] = tmat.m_cloud_surface2('T_CloudSea', sun_dir=tuple(_sd), lit=(0.86, 0.85, 0.84), shadow=CLOUD_SHADOW,
                                      haze_cool=(0.36, 0.46, 0.66), haze_warm=(0.9, 0.62, 0.4), fog_d=3200.0, emit=0.03,
                                      soft=False, bump=0.1, rim=1.0, wrap=0.25, base_dark=(0.5, -32.0, 6.0))
mats['cloudt'] = tmat.m_cloud_surface2('T_CloudTow', sun_dir=tuple(_sd), lit=(0.96, 0.94, 0.9), shadow=CLOUD_SHADOW,
                                       haze_cool=(0.36, 0.46, 0.66), haze_warm=(0.9, 0.62, 0.4), fog_d=3600.0, emit=0.03,
                                       soft=True, bump=0.8, rim=1.6, wrap=0.25, base_dark=(0.5, -90.0, 40.0))

rings = []
if want_temple:
    T, objs = temple.build_complex(C_T, mats, hero=True)
    rings = T.rings
    temple.plateau(C_T, mats['terrain'])
    tclouds.cloud_field(C_T, mats['cloud'], center=(0, 0), z0=-34.0, rmin=150.0, rmax=7000.0, n_ang=360, n_rad=150, small=(3500, (8.0, 26.0)),
                        heads=1500, head_r=(25, 120), height=(0.25, 0.5), seed=2, name='CloudSea', head_rmin=150.0,
                        bumps=[(r_ * math.cos(a_), r_ * math.sin(a_), rb_, hb_) for (r_, rb_, hb_, n_) in ((192, 50, 26, 26), (208, 55, 36, 30), (250, 75, 40, 22))
                               for a_ in np.arange(n_) / n_ * TAU + 0.1 * n_])   # cloud collar lapping the plateau rim
    tclouds.towers(C_T, mats['cloudt'], [(-1500, 2600, -90, 300, 600), (1500, 2600, -90, 300, 600), (-2300, 1700, -90, 280, 460),
                                         (2100, 1500, -90, 250, 420), (150, 3600, -90, 380, 760), (-1900, -700, -90, 300, 520),
                                         (1700, -1300, -90, 260, 420), (2600, 400, -90, 300, 560), (-1400, 900, -90, 200, 380),
                                         (-720, 620, -90, 210, 500), (640, 780, -90, 250, 580), (-950, -180, -90, 190, 400),
                                         (900, 120, -90, 220, 480), (-260, 1250, -90, 300, 680)],
                   name='CumulusT')
    # sheer rock pinnacles rising out of the cloud sea around the plateau (scale + depth)
    if False:   # v8: read as factory chimneys - removed
      tclouds.pinnacles(C_T, mats['terrain'], mats['terrain'],
                      [(-420, 380, -170, 40, 270), (-560, 120, -170, 55, 220), (480, 420, -170, 45, 310),
                       (620, -60, -170, 38, 190), (-300, 760, -170, 70, 340), (260, 900, -170, 60, 290),
                       (-560, 960, -170, 50, 260), (980, 420, -170, 65, 250), (-650, -420, -170, 42, 210),
                       (540, -480, -170, 36, 180), (150, 520, -170, 30, 200)], name='Pinnacles')
    # planar reflection for the pool
    try:
        if not arg('--planar', False):
            raise RuntimeError('planar probe disabled: in this EEVEE it KILLS the pool reflection (SSR works)')
        pd = bpy.data.lightprobes.new('PoolProbe', 'PLANE')
        po = bpy.data.objects.new('PoolProbe', pd)
        C_T.objects.link(po)
        po.location = (0, -53, -0.12)
        po.scale = (5.2, 21.5, 1)
    except Exception as e:
        print('[probe] failed', e)
    print(f'[build] temple done {time.time() - T0:.1f}s')

# ----------------------------------------------------------------------------- hero finial (4C) on gate apex
HERO_C = np.array([0.0, -87.25, 21.55])
if want_temple:
    B = MB(); G = MB()
    c = HERO_C
    prof = [(0.55, 0), (0.6, 0.08), (0.48, 0.16), (0.52, 0.22, 0.05), (0.44, 0.34, 0.05), (0.3, 0.42), (0.34, 0.5), (0.22, 0.58)]
    B.add(lathe(prof, teeth=16, tooth_shape=(0.0, 0.25, 0.5, 0.75)), M=mat4(c))
    B.add(lathe([(0.2, 0.58), (0.24, 0.62), (0.16, 0.7), (0.17, 0.95), (0.25, 1.0), (0.18, 1.06)], seg=40), M=mat4(c))
    # four spiral horns around the stem + a ring of twelve small filigree curls
    for k in range(4):
        a = k / 4 * TAU + math.pi / 4
        d = np.array([math.cos(a), math.sin(a), 0.0])
        B.add(temple.horn_curl(c + d * 0.2 + (0, 0, 0.5), d, size=0.5, turns=1.5, r0=0.055, n=64, seg=20))
    for k in range(12):
        a = k / 12 * TAU
        d = np.array([math.cos(a), math.sin(a), 0.0])
        B.add(temple.horn_curl(c + d * 0.3 + (0, 0, 0.44), d, size=0.2, turns=1.7, r0=0.022, n=48, seg=14))
    # jewel collar: vermilion + teal enamel cabochons in gold bezels
    J1, J2 = MB(), MB()
    for k in range(12):
        a = k / 12 * TAU
        p = c + (0.205 * math.cos(a), 0.205 * math.sin(a), 1.0)
        M = mat4(tuple(p), (0, math.pi / 2, a), (0.03, 0.03, 0.045))
        (J1 if k % 2 == 0 else J2).add(uvsphere(1.0, 16, 8), M=mat4(tuple(p), (0, 0, a)) @ mat4(rot=(0, math.pi / 2, 0), scale=(0.045, 0.03, 0.022)))
        B.add(lathe([(0.03, -0.01), (0.042, -0.01), (0.042, 0.012), (0.03, 0.012)], seg=16, closed=True),
              M=mat4(tuple(p), (0, 0, a)) @ mat4(rot=(0, math.pi / 2, 0)) @ mat4(scale=(1.0, 0.75, 1.0)))
    J1.build('HeroJewelR', [mats['verm']], C_T)
    J2.build('HeroJewelT', [mats['enamel']], C_T)
    # lotus crown: sixteen curling flame petals
    fl = temple.flame_geo(h=0.32, w=0.09, t=0.025, curl=0.08, n=8)
    pm = []
    for k in range(16):
        a = k / 16 * TAU
        d = np.array([math.cos(a), math.sin(a), 0.0]); tng = np.array([-math.sin(a), math.cos(a), 0.0])
        up = np.array([0, 0, 1.0]) * math.cos(0.75) + d * math.sin(0.75)
        x = np.cross(tng, up) * -1
        pm.append(frame_mat(c + d * 0.13 + (0, 0, 1.07), tng, np.cross(up, tng), up))
    B.inst(fl, pm)
    B.add(lathe([(0.12, 1.04), (0.17, 1.08), (0.12, 1.12)], seg=32), M=mat4(c))
    B.add(lathe([(0.08, 1.3), (0.1, 1.5), (0.18, 1.62), (0.1, 1.74), (0.05, 2.3), (0.08, 2.36), (0.03, 2.42), (0.001, 2.9)], seg=32), M=mat4(c))
    B.add(lathe([(0.07, 1.1), (0.075, 1.2), (0.065, 1.33)], seg=24), M=mat4(c))                       # spindle crown -> top gear
    B.add(lathe([(0.095, 1.335), (0.135, 1.355, 0.01), (0.135, 1.445, 0.01), (0.095, 1.465)], seg=32), M=mat4(c))   # hub boss
    _d3 = np.array([-0.64, -0.08, 0.0]); _d3 /= np.linalg.norm(_d3)
    B.add(sweep(np.array([c + _d3 * 0.2 + (0, 0, 0.64), c + _d3 * 0.8 + (0, 0, 0.64), c + _d3 * 0.8 + (0, 0, 0.82)]),
                rect_prof(0.045, 0.03), up=(0, 0, 1)))                                                       # bracket arm
    B.add(lathe([(0.026, 0.0), (0.026, 0.2)], seg=16).xf(frame_mat(c + _d3 * 0.58 + (0, 0, 0.82), np.cross((0, 0, 1), _d3), (0, 0, 1), _d3)))
    B.add(lathe([(0.001, -0.02), (0.05, -0.02, 0.01), (0.05, 0.04, 0.01), (0.03, 0.06)], seg=24).xf(
        frame_mat(c + _d3 * 0.78 + (0, 0, 0.82), np.cross((0, 0, 1), _d3), (0, 0, 1), _d3)))               # hub boss on the arm
    B.add(uvsphere(0.11, 32, 16), M=mat4(c + (0, 0, 1.62)))
    B.add(uvsphere(0.055, 24, 12), M=mat4(c + (0, 0, 2.18)))
    # bead strings around the base and the stem
    B.inst(uvsphere(1.0, 12, 6), [mat4(c + (0.5 * math.cos(a), 0.5 * math.sin(a), 0.12), scale=0.026) for a in np.arange(40) / 40 * TAU])
    B.inst(uvsphere(1.0, 10, 6), [mat4(c + (0.235 * math.cos(a), 0.235 * math.sin(a), 0.6), scale=0.016) for a in np.arange(36) / 36 * TAU])
    hero_static = B.build('HeroFinial', [mats['gold']], C_T, sharp=30, bevel_w=0.006)
    # rotating gear rings of the finial (main ring: 48 teeth, 12 windows, bead rim on top)
    gr = lathe([(0.26, -0.05), (0.27, -0.06), (0.48, -0.06, 0.06), (0.48, 0.06, 0.06), (0.27, 0.06), (0.26, 0.05)], teeth=48, closed=True)
    holes = instances(lathe([(0.035, -0.07), (0.045, -0.07), (0.045, 0.07), (0.035, 0.07)], seg=14, closed=True),
                      [mat4((0.375 * math.cos(a), 0.375 * math.sin(a), 0)) for a in np.arange(12) / 12 * TAU])
    beads = instances(uvsphere(1.0, 8, 5), [mat4((0.43 * math.cos(a), 0.43 * math.sin(a), 0.065), scale=0.012) for a in np.arange(48) / 48 * TAU])
    g1 = MB().add(merge([gr, holes, beads])).build('HeroGear1', [mats['gold']], C_T, sharp=30, bevel_w=0.005)
    g1.location = tuple(c + (0, 0, 0.82))
    rings.append((g1, 0.9))
    g2 = MB().add(lathe([(0.1, -0.03), (0.2, -0.03, 0.03), (0.2, 0.03, 0.03), (0.1, 0.03)], teeth=20, closed=True)).build(
        'HeroGear2', [mats['gold']], C_T, sharp=30, bevel_w=0.004)
    g2.location = tuple(c + (0, 0, 1.4))
    g2.rotation_euler = (0.0, 0.0, 0.0)
    rings.append((g2, -1.6))
    # a tilted pinion meshing with ring 1 for "clockwork" read
    g3 = MB().add(lathe([(0.03, -0.04), (0.1, -0.04, 0.03), (0.1, 0.04, 0.03), (0.03, 0.04)], teeth=10, closed=True)).build(
        'HeroGear3', [mats['gold']], C_T, sharp=30, bevel_w=0.004)
    g3.rotation_mode = 'ZXY'
    g3.rotation_euler = (math.pi / 2, 0, 0)
    g3p = empty('HeroGear3Pivot', tuple(c + (-0.64, -0.08, 0.82)), C_T)
    g3p.rotation_euler = (0, 0, math.pi / 2 + 0.12)
    g3.parent = g3p
    g3.location = (0, 0, 0)
    rings.append((g3, -0.9 * 36 / 10))

    # dust motes (client rule: real dust, sparse, NOT emissive): ~20 per macro, sunlit, defocused by the macro lenses
    mote = ico(1.0, 2)
    rngm = np.random.default_rng(5)
    mm = []
    for k in range(18):     # 4C: between lens and finial
        mm.append(mat4(tuple(HERO_C + (rngm.uniform(-0.6, 1.6), rngm.uniform(-3.3, -1.4), rngm.uniform(0.2, 1.8))), scale=rngm.uniform(0.003, 0.006)))
    for k in range(8):      # 4D: just in front of the lens
        mm.append(mat4((rngm.uniform(-25.9, -24.9), rngm.uniform(-54.5, -53.4), rngm.uniform(9.9, 10.5)), scale=rngm.uniform(0.002, 0.004)))
    motes = MB().inst(mote, mm).build('Motes', [mat_principled('T_Mote', (0.85, 0.8, 0.72), 0.5)], C_T, smooth=True)
    try:
        motes.visible_shadow = False
    except Exception:
        pass
    fc_key(motes, 'location', 2, [(1, 0.0), (80, 0.12)], interp='LINEAR')
    fc_key(motes, 'location', 0, [(1, 0.0), (80, 0.1)], interp='LINEAR')

    # 4C foreground occluder: a big toothed gear-ring arc of the gate crest, dark (backlit), deep out of focus
    occ_g = merge([lathe([(0.3, -0.03), (0.36, -0.03, 0.035), (0.36, 0.03, 0.035), (0.3, 0.03)], teeth=44, closed=True),
                   instances(box((0.3, 0.035, 0.03), (0.15, 0, 0)), [mat4(rot=(0, 0, a)) for a in np.arange(6) / 6 * TAU])])
    occ4c = MB().add(occ_g).build('Occl4C', [tmat.m_gold('T_GoldDark', base=(0.22, 0.13, 0.05), dark=(0.05, 0.03, 0.01), rough=(0.25, 0.45))], C_T, sharp=30, bevel_w=0.003)
    occ4c.hide_render = True
    # 4E foreground occluder: a shadowed meridian strap of the orrery cage, very close to the lens
    strap = []
    for k in range(25):
        a = -0.5 + k / 24 * 1.0
        strap.append((1.6 * math.sin(a), 0.0, 1.6 * math.cos(a) - 1.6))
    occ_e = merge([sweep(np.array(strap), rect_prof(0.075, 0.02), up=(0, 1, 0)),
                   instances(box((0.012, 0.03, 0.03), (0, 0, 0.02)), [mat4((1.6 * math.sin(a), 0.0, 1.6 * math.cos(a) - 1.6), (0, a, 0)) for a in np.linspace(-0.48, 0.48, 30)])])
    occ4e = MB().add(occ_e).build('Occl4E', [bpy.data.materials['T_GoldDark']], C_T, sharp=30, bevel_w=0.002)
    occ4e.hide_render = True

# ----------------------------------------------------------------------------- 4A cloud deck (separate set)
A_C = Vector((6000.0, 0.0, 0.0))
def build_deck_a():
    sd = sun_vec(*SUNS['4A'][:2])
    # r1: darker violet shadows, almost no self-emission / wrap (director QC: pastel, washed out)
    mat_deck = tmat.m_cloud_surface2('T_CloudDeck', sun_dir=tuple(sd), lit=(0.98, 0.9, 0.88), shadow=CLOUD_SHADOW,
                                     haze_cool=(0.3, 0.36, 0.56), haze_warm=(0.95, 0.6, 0.34), fog_d=3600.0, emit=0.03,
                                     soft=False, bump=0.3, rim=1.2, wrap=0.22, base_dark=(0.4, 285.0, 335.0), fog_max=0.6,
                                     wrap_col=(1.0, 0.62, 0.5))
    mat_tow = tmat.m_cloud_surface2('T_CloudTower', sun_dir=tuple(sd), lit=(0.98, 0.9, 0.88), shadow=CLOUD_SHADOW,
                                    haze_cool=(0.3, 0.36, 0.56), haze_warm=(0.95, 0.6, 0.34), fog_d=4200.0, emit=0.03,
                                    soft=True, bump=0.5, rim=2.0, wrap=0.22, base_dark=(0.4, 300.0, 420.0), fog_max=0.6,
                                    wrap_col=(1.0, 0.62, 0.5))
    ax, ay = A_C.x, A_C.y

    def _clamp4a(X, Y, H):
        # deck stays well under the path except the glide corridor (f26-f50), where cloud heads come
        # up to ~25 m under the lens (higher on the flanks); dive head rises under the dive volume
        xs = np.clip(X, ax - 250, ax + 650)
        dist = np.hypot(X - xs, Y - ay)
        cap = 46.0 + 0.3 * np.maximum(0.0, dist - 110.0)
        inx = np.clip(1 - np.maximum(0, np.maximum(ax + 30 - X, X - (ax + 340))) / 70.0, 0, 1)
        side = np.clip((np.abs(Y - ay) - 30) / 60, 0, 1)
        cap = np.maximum(cap, inx * (96 + 30 * side))
        dd = np.hypot(X - (ax - 115), Y - ay)
        cap = np.maximum(cap, 82.0 * np.clip(1 - dd / 190.0, 0, 1) ** 0.5)
        return cap * (1.0 - np.exp(-np.maximum(H, 0.0) / cap)) * 1.15   # soft clamp keeps the bulge relief
    # cloudfix: billowy deck (round puffs on puffs, baked soft self-shadow + cavity, emission shading, gaps to the
    # ground ~1.3 km below) instead of the old dune-like cloud_field
    mat_deck = tbillow.m_cloud_deck3('T_Billow4A', tuple(sd), z0=285.0, sun_s=3.0, sky_s=0.22, sun_col=(1.0, 0.85, 0.66),
                                     haze_cool=(0.3, 0.36, 0.56), haze_warm=(0.95, 0.6, 0.34), fog_d=3600.0, fog_max=0.6)
    mat_tow = tbillow.m_cloud_deck3('T_BillowTow4A', tuple(sd), z0=300.0, sun_s=3.1, sky_s=0.26, baked=False,
                                    sun_col=(1.0, 0.85, 0.66),
                                    low_fade=None, fine=(12.0, 4.5), fine_h=(3.0, 1.2), fine_fade=(200.0, 2500.0),
                                    haze_cool=(0.3, 0.36, 0.56), haze_warm=(0.95, 0.6, 0.34), fog_d=4200.0, fog_max=0.6,
                                    sil=(0.72, 0.97))
    tbillow.billow_field(C_A, mat_deck, center=(ax + 120, ay), z0=285.0, rmin=20.0, rmax=9000.0, n_ang=1080, seed=9,
                         name='Deck4A', head_r=(30.0, 150.0), head_h=(0.35, 0.62), grow=1500.0, cover=2.2,
                         puffs=((0.2, 0.4, 0.6, 2600.0, 3.0), (0.07, 0.15, 0.65, 1100.0, 3.0)), base=6.0,
                         gaps=(1500.0, 0.62, 30.0, 900.0), sun=tuple(sd),
                         bumps=[(ax - 115, ay, 150, 72), (ax - 60, ay + 150, 90, 50), (ax + 30, ay - 170, 110, 56),
                                (ax + 250, ay + 70, 75, 190), (ax + 175, ay - 75, 85, 200), (ax + 95, ay + 85, 70, 180),
                                (ax + 300, ay - 60, 60, 160), (ax + 140, ay + 10, 70, 150), (ax + 60, ay - 40, 80, 150)],
                         clamp=_clamp4a)
    tbillow.far_ground(C_A, tbillow.m_ground_far('T_GroundFar4A'), 285.0 - 1300.0, center=(ax, ay), name='GroundFar4A')
    tclouds.towers(C_A, mat_tow, [(ax - 1700, ay - 900, 300, 260, 520), (ax - 2600, ay + 700, 300, 330, 700),
                                  (ax - 1100, ay + 1050, 300, 170, 330), (ax - 3600, ay - 200, 300, 450, 820),
                                  (ax - 900, ay - 1150, 300, 160, 280), (ax - 4200, ay - 2200, 300, 420, 650),
                                  (ax - 2000, ay + 2300, 300, 380, 600), (ax + 600, ay + 1900, 300, 300, 520),
                                  (ax - 950, ay + 620, 290, 230, 470), (ax - 760, ay - 760, 290, 190, 360)],
                   name='Cumulus4A')
    # sunlit tower heads close beside the glide path (near parallax, 15-35 m from the lens)
    tclouds.towers(C_A, mat_tow, [(ax + 240, ay + 62, 330, 24, 96), (ax + 165, ay - 58, 330, 28, 104),
                                  (ax + 100, ay + 70, 325, 26, 92), (ax + 30, ay - 66, 320, 30, 88)],
                   seed=4, name='Near4A', blobs=18)
    # start cloud: denser billows / darker pockets (noise_k 3), low self-emission; exit is gradual f15-f22
    vS = tmat.m_cloud_vol2('T_VolA', density=0.09, scale=9.0, emit_s=0.35, emit=(0.85, 0.72, 0.6), seed=1.0, shape_k=1.3,
                           noise_k=3.2, thr=0.4)
    vp = [n for n in vS.node_tree.nodes if n.type == 'PRINCIPLED_VOLUME'][0]
    for f, col, alb in ((1, (0.85, 0.66, 0.5, 1), (0.92, 0.8, 0.68, 1)), (18, (1.0, 0.9, 0.8, 1), (1.0, 0.97, 0.93, 1))):
        # T3: 3E's tan dust hue (212,186,167) -> warm white cloud by f18 (emission AND scattering albedo)
        vp.inputs['Emission Color'].default_value = col
        vp.inputs['Emission Color'].keyframe_insert('default_value', frame=f)
        vp.inputs['Color'].default_value = alb
        vp.inputs['Color'].keyframe_insert('default_value', frame=f)
    tclouds.vol_blob(C_A, 'VolStart', A_C + Vector((467, 0, 425)), (340, 400, 230), vS)
    vD = tmat.m_cloud_vol2('T_VolDive', density=0.45, scale=3.4, emit_s=0.3, emit=(1.0, 0.88, 0.74), seed=4.0, shape_k=1.9,
                           noise_k=3.0, thr=0.4)
    # r4: at (-100, 326) the lens skimmed the deck MESH before the volume closed in (tan streaks / flat tan f64-f70);
    # back near the original spot and taller so the camera is wrapped in white vapour from ~f62 to the cut
    tclouds.vol_blob(C_A, 'VolDive', A_C + Vector((-88, 0, 334)), (240, 220, 150), vD)
    vW = tmat.m_cloud_vol2('T_VolWisp', density=0.022, scale=4.5, emit_s=0.03, emit=(1.0, 0.9, 0.76), shape_k=1.2,
                           noise_k=1.8, thr=0.35, seed=7.0)
    rngw = np.random.default_rng(12)
    for k in range(4):
        loc = A_C + Vector((rngw.uniform(-40, 200), rngw.choice([-1, 1]) * rngw.uniform(70, 160), rngw.uniform(362, 392)))
        tclouds.vol_blob(C_A, f'Wisp{k}', loc, (rngw.uniform(160, 260), rngw.uniform(120, 200), rngw.uniform(30, 50)), vW)
    # thicker wisps flanking the glide path (the lens tears past them)
    vW2 = tmat.m_cloud_vol2('T_VolWisp2', density=0.08, scale=4.0, emit_s=0.03, emit=(1.0, 0.9, 0.76), shape_k=1.3,
                            noise_k=2.2, thr=0.35, seed=3.0)
    for k, (x, y, z, sx_, sy_, sz_) in enumerate(((235, 38, 420, 120, 46, 26), (150, -40, 424, 110, 44, 24), (70, 34, 408, 110, 50, 30))):
        tclouds.vol_blob(C_A, f'WispN{k}', A_C + Vector((x, y, z)), (sx_, sy_, sz_), vW2)
    print(f'[build] deck4A done {time.time() - T0:.1f}s')


if want_clouds_a:
    try:
        build_deck_a()
    except Exception:
        import traceback; traceback.print_exc()

if want_temple and '4B' in need:
    # the deck the camera punches down through (camera starts inside it)
    vB = tmat.m_cloud_vol2('T_VolB', density=0.3, scale=2.8, emit_s=0.15, emit=(1.0, 0.9, 0.76), seed=2.0, noise_k=2.5)
    tclouds.vol_blob(C_B, 'Deck4B', (-140, -342, 318), (420, 380, 150), vB)
    # torn sheets right on the descent path f12-f19: the lens tears through them (parallax instead of a pop)
    vBt = tmat.m_cloud_vol2('T_VolBt', density=0.08, scale=3.6, emit_s=0.05, emit=(1.0, 0.9, 0.76), shape_k=1.3,
                            noise_k=2.2, thr=0.35, seed=9.0)
    for k, (c_, sz_) in enumerate((((-123, -306, 214), (95, 75, 22)), ((-108, -289, 197), (85, 65, 18)), ((-140, -296, 205), (70, 60, 16)))):
        tclouds.vol_blob(C_B, f'Tear4B_{k}', c_, sz_, vBt)
    # vapour sheets lying on the sea along the island rim: soft the hard 'hole' edge, read as vapour (not snow)
    # cloudfix: the vapour now sits in the breach (cliff contact zone under the plateau rim), denser + lit
    vR = tmat.m_cloud_vol2('T_VolRim', density=0.06, scale=3.0, emit_s=0.05, emit=(1.0, 0.9, 0.78), shape_k=1.4,
                           noise_k=2.0, thr=0.35, seed=11.0, stretch=(1.0, 1.0, 2.5))
    for k in range(7):
        a_ = math.radians(-150 + k * 52)
        tclouds.vol_blob(C_B, f'Rim4B_{k}', (200 * math.cos(a_), 188 * math.sin(a_), -16.0), (200, 160, 40), vR,
                         rot=(0, 0, a_ + math.pi / 2))
    # cloudfix: billowy cloud sea for 4B (replaces CloudSea/CumulusT in this shot only; 4C-4F keep theirs)
    _sdB = sun_vec(*SUNS['4B'][:2])
    mat_b3 = tbillow.m_cloud_deck3('T_Billow4B', tuple(_sdB), z0=-34.0, sun_s=2.6, sky_s=0.24, sun_col=(1.0, 0.87, 0.68),
                                   haze_cool=(0.36, 0.46, 0.66), haze_warm=(0.9, 0.62, 0.4), fog_d=3200.0, fog_max=0.6,
                                   breach=(0.0, 0.0, 4.0, 75.0, 70.0))
    mat_t3 = tbillow.m_cloud_deck3('T_BillowTow4B', tuple(_sdB), z0=-90.0, sun_s=2.6, sky_s=0.24, baked=False,
                                   sun_col=(1.0, 0.87, 0.68),
                                   low_fade=None, fine=(14.0, 5.0), fine_h=(3.0, 1.2), fine_fade=(300.0, 3000.0),
                                   haze_cool=(0.36, 0.46, 0.66), haze_warm=(0.9, 0.62, 0.4), fog_d=3600.0, fog_max=0.6,
                                   sil=(0.72, 0.97))
    tbillow.billow_field(C_B, mat_b3, center=(0.0, 0.0), z0=-34.0, rmin=150.0, rmax=7000.0, n_ang=1024, seed=2,
                         name='Billow4B', head_r=(28.0, 110.0), head_h=(0.28, 0.5), grow=1800.0, cover=2.2,
                         head_rmin=150.0, puffs=((0.2, 0.4, 0.6, 2600.0, 3.0), (0.07, 0.15, 0.65, 1100.0, 3.0)),
                         base=6.0, undulate=6.0, gaps=(1400.0, 0.62, 30.0, 600.0), taper=(200.0, 520.0, 0.55),
                         sun=tuple(_sdB),
                         bumps=[(r_ * math.cos(a_), r_ * math.sin(a_), rb_, hb_) for (r_, rb_, hb_, n_) in ((205, 45, 18, 26), (245, 60, 26, 22))
                                for a_ in np.arange(n_) / n_ * TAU + 0.1 * n_])
    tbillow.far_ground(C_B, tbillow.m_ground_far('T_GroundFar4B'), -1400.0, name='GroundFar4B')
    # thin drifting stratus veils over the deck (soft alpha cards, kept outside the island)
    wsp = tbillow.wisp_cards(C_B, tbillow.m_wisp('T_Wisp4B', tuple(_sdB)), [
        (-80, -330, 46, 420, 170, 0.4), (170, -300, 40, 320, 150, -0.3), (-330, -60, 44, 280, 360, 0.2),
        (330, 60, 50, 280, 380, -0.2), (0, 360, 55, 460, 200, 0.1), (-420, -420, 70, 520, 220, 0.6),
        (380, -500, 75, 540, 210, -0.5), (-560, 360, 85, 720, 300, 0.3), (520, 480, 90, 720, 300, -0.4),
        (-120, -620, 80, 600, 240, 0.15)], name='Wisp4B')
    fc_key(wsp, 'location', 0, [(1, 0.0), (72, 7.0)], interp='LINEAR')
    fc_key(wsp, 'location', 1, [(1, 0.0), (72, 3.0)], interp='LINEAR')
    # torn wisps hanging under the deck: parallax while descending
    vBw = tmat.m_cloud_vol2('T_VolBw', density=0.05, scale=3.2, emit_s=0.05, emit=(1.0, 0.9, 0.76), shape_k=1.4,
                            noise_k=1.8, thr=0.35, seed=5.0)
    rngb = np.random.default_rng(31)
    for k in range(7):
        side = 1 if k % 2 else -1
        loc = (-120 + side * rngb.uniform(45, 110), rngb.uniform(-330, -230), rngb.uniform(175, 240))
        tclouds.vol_blob(C_B, f'Frag4B_{k}', loc, (rngb.uniform(70, 130), rngb.uniform(60, 110), rngb.uniform(25, 45)), vBw)
    # a few small sunlit cumulus heads off the flight path (scale + parallax)
    tclouds.towers(C_B, mat_t3, [(-260, -300, 95, 38, 60), (60, -330, 120, 30, 45), (-330, -120, 60, 45, 70),
                                         (190, -160, 70, 35, 55)], seed=8, name='Puffs4B', blobs=16)
    # camera-invisible shadow casters west of the temple -> god-ray shafts in the haze (sun from the west)
    cast_mat = mat_principled('T_Caster', (0.5, 0.5, 0.5), 0.9)
    tclouds.ray_casters(C_B, cast_mat, [(-640, y, rngb.uniform(150, 200), rngb.uniform(50, 80), rngb.uniform(28, 46))
                                        for y in (-300, -205, -120, -30, 180, 265)], name='Casters4B')
    # god rays: emissive volume shafts along the light direction (art-directed; shadow casters alone were invisible)
    beam_mat = tclouds.beam_material('T_Beam4B', color=(1.0, 0.8, 0.55), strength=0.006)
    tclouds.light_beams(C_B, beam_mat, tuple(-sun_vec(*SUNS['4B'][:2])),
                        [((-120, -150, 90), 700, 40), ((-60, -60, 110), 700, 52), ((40, -200, 70), 600, 34),
                         ((-200, -30, 140), 800, 58), ((60, 40, 120), 700, 44), ((-20, -260, 140), 700, 36),
                         ((120, -100, 60), 500, 28), ((-160, -250, 170), 800, 50)], name='Beam4B')
    # a flock of white birds crossing below the camera (scale cue)
    bird_mat = mat_principled('T_Bird', (0.72, 0.68, 0.62), 0.7)
    tclouds.birds(C_B, bird_mat, n=30, center=(-18, -128, 52), spread=(30, 22, 5), heading=(1.0, 0.3, 0.05),
                  speed=0.45, frames=(1, 72), size=0.6)

# ----------------------------------------------------------------------------- animation of rings
RING_BASE = {o.name: o.rotation_euler[2] for o, sp in rings}


def key_rings(orrery_mult=1.0, mult=1.0):
    for o, sp in rings:
        if o.animation_data:
            o.animation_data_clear()
        m = orrery_mult if o.name.startswith('orrery_ring') else mult
        rate = sp * m / FPS
        base = RING_BASE[o.name]
        o.rotation_euler[2] = base
        fc_key(o, 'rotation_euler', 2, [(1, base), (101, base + rate * 100)], interp='LINEAR')
        for fc in fcurves(o):
            if fc.data_path == 'rotation_euler':
                fc.extrapolation = 'LINEAR'


key_rings()

# ----------------------------------------------------------------------------- cameras

def cam_path(name, keys, lens=24, fstop=None, focus=None, shift=(0, 0), interp='BEZIER', clip=(0.1, 9000)):
    c = camera(name, keys[0][1], lens=lens, fstop=fstop, focus=focus, clip=clip)
    c.data.shift_x, c.data.shift_y = shift
    for f, loc, tgt in keys:
        c.location = loc
        look_at(c, tgt)
        c.keyframe_insert('location', frame=f)
        c.keyframe_insert('rotation_euler', frame=f)
    set_interp(c, interp)
    # IMPORTANT: common.shake() keys the CURRENT value at frame_start; without this the f1 key was overwritten
    # with the LAST key's pose (camera started at its end position - broke 4A/4B openings and the macros)
    bpy.context.scene.frame_set(keys[0][0])
    return c


def bake_roll(c, roll, f0, f1):
    """Evaluate the camera (incl. shake modifiers) per frame, add a roll about its view axis, re-key per frame."""
    scn = bpy.context.scene
    Ms = []
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        Ms.append(c.matrix_world.copy())
    c.animation_data_clear()
    prev = None
    for i, f in enumerate(range(f0, f1 + 1)):
        M = Ms[i] @ Matrix.Rotation(roll(f), 4, 'Z')
        loc, q, _s = M.decompose()
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        c.location = loc
        c.rotation_euler = e
        c.keyframe_insert('location', frame=f)
        c.keyframe_insert('rotation_euler', frame=f)
        prev = e
    for fc in fcurves(c):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    scn.frame_set(f0)


def shot_setup(sid):
    for o in [o for o in bpy.data.objects if o.name.startswith('ShotLight')]:
        o.hide_render = True
    C_A.hide_render = sid != '4A'
    C_B.hide_render = sid != '4B'
    C_T.hide_render = sid == '4A'
    _o = bpy.data.objects.get('CloudSea')          # cloudfix: 4B uses Billow4B (C_B) instead
    if _o is not None:
        _o.hide_render = sid == '4B'
    _o = bpy.data.objects.get('CumulusT')          # cloudfix: 4B re-shades the towers (4C-4F keep T_CloudTow)
    _m = bpy.data.materials.get('T_BillowTow4B' if sid == '4B' else 'T_CloudTow')
    if _o is not None and _m is not None:
        _o.data.materials[0] = _m
    haze_box.hide_render = sid in ('4A', '4F')     # 4F: the courtyard mist carries the atmosphere; saves a full-screen volume
    haze_box.location = (0, 0, 60)
    mist_box.hide_render = sid != '4F'
    set_haze({'4F': 0.00018, '4C': 0.0002, '4D': 0.0002, '4E': 0.0002}.get(sid, 0.00055))
    pp = bpy.data.objects.get('PoolProbe')
    if pp is not None:
        pp.hide_render = sid not in ('4F',)
    # local reflection sphere probes for the macro shots (gold reflects the temple, not just the world)
    for o in [o for o in bpy.data.objects if o.name.startswith('ShotProbe')]:
        o.hide_render = True
    probe_at = {'4C': (tuple(HERO_C + (0, 0, 1.0)), 8.0), '4E': ((0.0, 16.0, 40.9), 14.0), '4D': ((-31.0, -48.0, 9.0), 12.0)}
    if sid in probe_at and want_temple and not arg('--noprobe'):
        try:
            pdat = bpy.data.lightprobes.new('ShotProbe' + sid, 'SPHERE')
            po = bpy.data.objects.new('ShotProbe' + sid, pdat)
            C_T.objects.link(po)
            po.location = probe_at[sid][0]
            pdat.influence_distance = probe_at[sid][1]
        except Exception as e:
            print('[probe] sphere failed', e)
    ee = sc.eevee
    ee.volumetric_tile_size = '8'; ee.volumetric_samples = 48; ee.volumetric_start = 0.5
    # render budget (laptop iGPU): 1 shadow ray / 6 steps is visually identical at these sizes
    ee.shadow_ray_count = 1; ee.shadow_step_count = 6
    # screen-space horizon-scan GI drew a dark mirrored 'ghost' of the island into the cloud sea -> off in the aerials
    ee.use_fast_gi = sid not in ('4A', '4B')
    mo = bpy.data.objects.get('Motes')
    if mo is not None:
        mo.hide_render = sid != '4D'      # 4C: backlit principled motes read as dark specks -> off
    for nm in ('Occl4C', 'Occl4E'):
        o = bpy.data.objects.get(nm)
        if o is not None:
            o.hide_render = nm[-2:] != sid
    key_rings(orrery_mult=6.0 if sid == '4E' else 1.0, mult=1.2 if sid == '4C' else 1.0)
    _cur_shot[0] = sid
    sc.view_settings.exposure = EXPO.get(sid, 0.0)
    sc.eevee.taa_render_samples = {'4F': 20}.get(sid, 24)   # final defaults (CLI --samples overrides in finish())
    el, az, en, col, skys = SUNS.get(sid, SUNS['4F'])
    set_sun(el, az, en, col, skys, COVER.get(sid, 0.5))
    n = SHOTS.get(sid, 78)
    sc.frame_start, sc.frame_end = 1, n
    if sid == 'SUNCHECK':
        sky.sun_disc = True
        c = camera('CamSun', (0, -150, 60), target=tuple(Vector((0, -150, 60)) + SUN_DIR * 100), lens=35)
        return c
    if sid == '4F':
        ee.volumetric_end = 400.0
        # glide through the gate, settle at the pool head low over the water (more mirror in frame), lens 21->26
        # r1: starts 26 m outside the gate looking UP at its tiered roofs/spires, momentum from cut frame 1,
        # tilts down while it speeds through the passage (f10-f32), eases out into the pool head by f55, holds f55-78
        c = cam_path('Cam4F', [(1, (0, -112, 2.6), (0, 0, 10.5)), (30, (0, -85.5, 2.25), (0, 0, 3.2)),
                               (55, (0, -74, 1.9), (0, 0, 1.9)), (78, (0, -74, 1.9), (0, 0, 1.9))],
                     lens=26, shift=(0, 0.15))
        for f, v in ((1, 20.0), (30, 22.5), (55, 26.0)):
            c.data.lens = v
            c.data.keyframe_insert('lens', frame=f)
        c.data.dof.use_dof = True
        c.data.dof.aperture_fstop = 8.0
        c.data.dof.focus_distance = 70.0
        for fc in list(fcurves(c)) + list(fcurves(c.data)):
            kps = fc.keyframe_points
            if len(kps) >= 3:
                kps[0].handle_right_type = 'VECTOR'          # linear-ish start: already moving on cut frame 1
                for kp in kps:
                    kp.interpolation = 'BEZIER'
            if len(kps) >= 4 and abs(kps[-2].co[0] - 55) < 0.5:   # location/rotation only (lens has 3 keys, last = f55)
                kps[-2].handle_left_type = 'AUTO_CLAMPED'
                kps[-2].interpolation = 'CONSTANT'            # f55 -> f78 locked (T4 photo hold)
            fc.update()
        return c
    if sid == '4B':
        ee.volumetric_end = 1400.0
        ee.volumetric_start = 1.0
        ee.volumetric_tile_size = '8'
        ee.volumetric_samples = 64
        set_haze(0.0005)
        c = cam_path('Cam4B', [(1, (-150, -350, 300), (-40, -80, 0)), (12, (-128, -318, 226), (-20, -10, 0)),
                               (30, (-92, -250, 148), (-4, 50, 0)), (50, (-60, -188, 94), (-5, 10, 8)),
                               (72, (-26, -122, 46), (0, -5, 14))], lens=20)
        c.rotation_mode = 'XYZ'
        shake(c, amp=0.05, rot_amp=0.002, scale=12, seed=11)
        return c
    if sid == '4C':
        ee.volumetric_end = 300.0
        tgt = HERO_C + (0, 0, 0.95)

        def P4c(adeg, r, dz):
            a = math.radians(adeg)
            return tuple(HERO_C + (r * math.cos(a), r * math.sin(a), dz))
        # orbit centred on the hall axis (view dir 105 -> 80 deg) so the shadowed hall roofs sit behind the finial
        keys = [(1, P4c(-76, 3.9, 0.86), tuple(tgt + (0.05, 0, -0.04))), (14, P4c(-88, 3.55, 0.9), tuple(tgt + (0.02, 0, -0.03))),
                (28, P4c(-100, 3.2, 0.94), tuple(tgt + (0, 0, -0.02)))]
        c = cam_path('Cam4C', keys, lens=85, fstop=1.4)
        c.data.dof.focus_object = None
        # rack: foreground gear ring (~1.0 m) -> cabochon collar
        for f, v in ((1, 1.05), (7, 1.1), (15, 3.45), (28, 3.15)):
            c.data.dof.focus_distance = v
            c.data.keyframe_insert('dof.focus_distance', frame=f)
        shake(c, amp=0.004, rot_amp=0.0015, scale=18, seed=3)
        o = bpy.data.objects.get('Occl4C')
        if o is not None:     # camera-held foreground ring arc, lower-left, drifting slowly (parallax vs the orbit)
            o.parent = c
            o.matrix_parent_inverse.identity()
            o.rotation_euler = (0.25, -0.2, 0.3)
            fc_key(o, 'location', 0, [(1, -0.42), (28, -0.36)], interp='LINEAR')
            fc_key(o, 'location', 1, [(1, -0.29), (28, -0.31)], interp='LINEAR')
            fc_key(o, 'location', 2, [(1, -1.05), (28, -1.05)], interp='LINEAR')
            fc_key(o, 'rotation_euler', 2, [(1, 0.3), (28, 0.55)], interp='LINEAR')
        return c
    if sid == '4D':
        ee.volumetric_end = 300.0
        # hero tile roof on left pavilion (x=-34, y=-45, eave z~7.8)
        # hero tile roof on left pavilion (x=-34, y=-45): look along the +x slope from its front corner
        c = cam_path('Cam4D', [(1, (-24.8, -55.0, 10.2), (-29.2, -44.0, 9.2)),
                               (28, (-25.2, -54.0, 10.35), (-29.4, -43.2, 9.3))], lens=65, fstop=2.0)
        c.data.dof.focus_distance = 6.5
        P = Vector((-28.6, -47.0, 8.9)); Cc = Vector((-25.0, -54.5, 10.3))
        d = (P - Cc).normalized(); nrm = Vector((0.5, 0, 0.866))
        r = d - 2 * d.dot(nrm) * nrm
        lp = P + r * 28
        L = light('AREA', 'ShotLight4D', tuple(lp), energy=1600, color=(1.0, 0.66, 0.36), size=5.0, size_y=0.5, target=tuple(P))
        fc_key(L, 'location', 0, [(1, lp.x - 8), (28, lp.x + 8)], interp='LINEAR')
        L.hide_render = False
        return c
    if sid == '4E':
        ee.volumetric_end = 300.0
        # orrery close-up: the camera sits between the rings, which sweep through the foreground (6x speed)
        oc = Vector((0.0, 16.0, 24.0 + 9.9 + 7.0))
        def P(a_deg, r, dz):
            a = math.radians(a_deg)
            return tuple(oc + Vector((r * math.cos(a), r * math.sin(a), dz)))
        c = cam_path('Cam4E', [(1, P(-118, 5.6, 2.1), tuple(oc + Vector((0.25, 0, 0.1)))),
                               (28, P(-100, 5.1, 1.7), tuple(oc + Vector((0.0, 0, 0.05))))], lens=50, fstop=1.4)
        for f, v in ((1, 5.0), (28, 4.35)):
            c.data.dof.focus_distance = v
            c.data.keyframe_insert('dof.focus_distance', frame=f)
        shake(c, amp=0.008, rot_amp=0.0015, scale=14, seed=5)
        o = bpy.data.objects.get('Occl4E')
        if o is not None:
            o.parent = c
            o.matrix_parent_inverse.identity()
            o.rotation_euler = (math.radians(90), 0.0, math.radians(-38))
            fc_key(o, 'location', 0, [(1, 0.16), (28, 0.2)], interp='LINEAR')
            fc_key(o, 'location', 1, [(1, 0.12), (28, 0.1)], interp='LINEAR')
            fc_key(o, 'location', 2, [(1, -0.55), (28, -0.55)], interp='LINEAR')
        return c
    if sid == '4A':
        ee.volumetric_end = 900.0
        ee.volumetric_start = 0.5
        ee.volumetric_tile_size = '8'
        ee.volumetric_samples = 64
        P = lambda x, y, z: tuple(A_C + Vector((x, y, z)))
        # inside the start cloud (cut frames 1-12 = local 7-18 pure cloud) -> exit ~f26 above the sea,
        # glide toward the low sun, pitch down and dive into a cloud head (white by f70)
        c = cam_path('Cam4A', [(1, P(440, 0, 425), P(-400, -70, 409)), (24, P(292, 0, 428), P(-500, -90, 403)),
                               (36, P(195, 0, 430), P(-700, -110, 360)), (50, P(70, 0, 418), P(-500, -50, 296)),
                               (60, P(0, 4, 392), P(-150, 0, 255)), (72, P(-92, 0, 336), P(-170, 0, 232))], lens=22)
        shake(c, amp=0.08, rot_amp=0.0035, scale=9, seed=7)

        def _roll(f):
            t = min(1.0, max(0.0, (f - 26) / 24.0))
            t2 = min(1.0, max(0.0, (f - 50) / 14.0))
            return math.radians(7.0) * (3 * t * t - 2 * t ** 3) * (1 - (3 * t2 * t2 - 2 * t2 ** 3) * 0.6)
        bake_roll(c, _roll, 1, 72)
        return c
    raise SystemExit('unknown shot ' + sid)


def _dbg_cam(scene, *a):
    c = scene.camera
    if c is not None and arg('--dbgcam'):
        print(f'[cam] f{scene.frame_current} {tuple(round(v, 1) for v in c.matrix_world.translation)}', flush=True)


bpy.app.handlers.frame_change_post.append(_dbg_cam)


def debug_pool():
    """--dbgpool: render the 4F end frame with parts of the scene switched off to find what kills SSR."""
    c = shot_setup('4F')
    sc.camera = c
    sc.frame_set(72)
    sc.render.resolution_percentage = 20
    sc.render.image_settings.file_format = 'JPEG'
    sc.eevee.taa_render_samples = 8
    groups = {
        'vols': [o for o in bpy.data.objects if o.name in ('HazeBox', 'MistBox')],
        'clouds': [o for o in bpy.data.objects if o.name.startswith(('CloudSea', 'CumulusT', 'Pinnacles'))],
        'terrain': [o for o in bpy.data.objects if o.name.startswith('Plateau')],
        'gold': [o for o in bpy.data.objects if o.name in ('T_gold', 'T_gold2')],
    }
    def render(tag):
        sc.render.filepath = os.path.join(FILM, 'tests', f'dbg_pool_{tag}.jpg')
        bpy.ops.render.render(write_still=True)
        print('[dbgpool]', tag, flush=True)
    render('all')
    for g, objs in groups.items():
        for o in objs:
            o.hide_render = True
        render('no_' + g)
        for o in objs:
            o.hide_render = False
    sc.eevee.use_fast_gi = False
    render('no_fastgi')
    sc.eevee.use_fast_gi = True
    sc.render.use_motion_blur = False
    render('no_mblur')


if arg('--dbgpool'):
    debug_pool()
    raise SystemExit(0)


def run(sid):
    c = shot_setup(sid)
    sc.camera = c
    print(f'[shot] {sid} ready at {time.time() - T0:.1f}s')
    finish(sid)


if multi:
    base = sys.argv[:sys.argv.index('--') + 1]
    rest = sys.argv[sys.argv.index('--') + 1:]
    keep = []
    i = 0
    while i < len(rest):
        if rest[i] in ('--multi', '--shot', '--stills', '--still'):
            i += 2
            continue
        keep.append(rest[i]); i += 1
    manim = arg('--multianim', None)
    keep = [k for k in keep if k not in ('--multianim',)] if not manim else \
        [k for i, k in enumerate(keep) if k != '--multianim' and not (i > 0 and keep[i - 1] == '--multianim')]
    for spec in multi.split(';'):
        sid, fr = spec.split(':')
        if manim:
            od = os.path.join(FILM, 'tests', f'{sid}_motion')
            sys.argv = base + keep + ['--anim', '--jpg', '--overwrite', '--step', str(manim), '--outdir', od]
        else:
            sys.argv = base + keep + ['--stills', fr]
        run(sid)
else:
    run(shot_arg)
print(f'[act4] total {time.time() - T0:.1f}s')
