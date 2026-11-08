"""ACT V - THE DESK (shots 5A 5B 5C). Real scale (meters), desk top z = 0.

  rb.py shots/act5_desk.py -- --shot 5A --stills 7,20,40 --pct 50 --samples 16
  (--shot may be a comma list, e.g. 5A,5B,5C, to render the same still frames for several shots in one build)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from desk import *
import json, time

T0 = time.time()
from desk_more import install_lock_fix
install_lock_fix()
SHOTS = {s['id']: s for s in json.load(open(os.path.join(FILM, 'shotlist.json')))['shots'] if s['script'] == 'act5_desk.py'}
SHOT_ARG = str(arg('--shot', '5A'))
SHOT_LIST = [s.strip() for s in SHOT_ARG.split(',') if s.strip()]

sc = reset()
setup_render(1, 84, samples=48, vol_tile='4', vol_samples=48, vol_start=0.003, vol_end=3.0, shutter=0.5,
             look='AgX - Medium High Contrast')
ee = sc.eevee
for attr, val in (('fast_gi_distance', 0.25), ('fast_gi_thickness_near', 0.004), ('fast_gi_thickness_far', 0.02)):
    try:
        setattr(ee, attr, val)
    except Exception as e:
        print('[act5] eevee', attr, e)
try:
    ee.ray_tracing_options.screen_trace_thickness = 0.004
    ee.ray_tracing_options.screen_trace_quality = 0.5
except Exception as e:
    print('[act5] rt opts', e)
try:
    ee.light_threshold = 0.001
except Exception:
    pass
compositor(bloom=0.28, threshold=1.2, bloom_size=0.7, dispersion=0.004)
world = world_color((0.0016, 0.0022, 0.0036), 1.0)
FOG_D = 0.07          # CLIENT RULE: haze must not lift the blacks (was 0.11)
FOG = add_world_fog(world, FOG_D, (0.82, 0.86, 0.95), 0.6)

C = collection('Desk')
rng = random.Random(11)

# ----------------------------------------------------------------------------- materials
M = {}
M['walnut'] = mat_walnut()
M['gold'] = mat_gold('CaseGold', base=(1.0, 0.70, 0.30), rough=(0.06, 0.2), scale=300.0)
M['wbrass'] = mat_brass('WatchBrass', base=(0.85, 0.60, 0.28), dark=(0.45, 0.28, 0.10), rough=(0.12, 0.38), scale=900.0, worn=0.3)
M['perlage'] = mat_perlage('Perlage', base=(0.58, 0.60, 0.64))     # v5: rhodium plate/bridges (cool) vs brass wheels (warm)
M['wheel'] = mat_wheel('WheelBrass')                                  # v13: circular-grained gilt wheels
M['wsteel'] = mat_metal('WatchSteel', base=(0.70, 0.71, 0.72), rough=(0.06, 0.18), scale=800.0, bump=0.02)
M['blued'] = mat_blued()
M['ruby'] = mat_ruby()
M['enamel'] = mat_enamel()
M['crystal'] = mat_crystal()
M['dark'] = mat_principled('Ink', (0.01, 0.01, 0.012), rough=0.4)
M['lens'] = mat_lens_glass()
M['loupe_brass'] = mat_brass('LoupeBrass', base=(0.72, 0.50, 0.24), dark=(0.30, 0.18, 0.07), rough=(0.18, 0.45), scale=2500.0, worn=0.25)   # v13: 250 -> 'fur' at macro distance
M['steel'] = mat_steel_brushed()
M['caliper'] = mat_caliper()
M['chrome'] = mat_metal('Chrome', base=(0.85, 0.86, 0.88), rough=(0.03, 0.08), scale=200.0, bump=0.01)
M['blackgrip'] = mat_rubber('Grip', (0.012, 0.012, 0.014), 0.55)
M['cedar'] = mat_cedar()
M['cedar_shv'] = mat_cedar('CedarShaving', scallop=False)
M['graphite'] = mat_graphite()
M['ferrule'] = mat_metal('Ferrule', base=(0.80, 0.68, 0.40), rough=(0.15, 0.35), scale=600.0, bump=0.05)
M['eraser'] = mat_principled('EraserPink', (0.72, 0.30, 0.30), rough=0.85)
M['eraserblock'] = mat_principled('EraserBlock', (0.80, 0.80, 0.76), rough=0.8)
M['crumb'] = mat_principled('Crumbs', (0.42, 0.40, 0.40), rough=0.9)
M['dust'] = mat_principled('Dust', (0.55, 0.52, 0.48), rough=0.95)
M['mote'] = mat_principled('Mote', (0.85, 0.80, 0.72), rough=0.45)     # CLIENT RULE: real dust, no emissive bits
M['enamel_lamp'] = mat_paint('LampEnamel', (0.015, 0.05, 0.035), rough=0.3)
M['lamp_inner'] = mat_principled('LampInner', (0.42, 0.40, 0.36), rough=0.45)   # v13: was 0.85 - mirrored as white 'cards' in crystal/lid
M['bulb'] = mat_emission('Bulb', (1.0, 0.62, 0.32), 6.0)          # CLIENT RULE 2: practicals at moderate intensity
M['mug'] = mat_ceramic('Mug', (0.025, 0.045, 0.055))
M['coffee'] = mat_principled('Coffee', (0.03, 0.012, 0.004), rough=0.05)
M['wall'] = mat_plaster()
M['sky'] = mat_emission('NightSky', (0.25, 0.42, 0.9), 1.2)

print('[t] desk + mat %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- desk + mat
desk = box('Workbench', (1.6, 1.05, 0.045), loc=(0, 0.06, -0.0225), coll=C, bev=0.004, seg=3)
set_mat(desk, M['walnut'])

def make_mat_plane(name, w, h, loc, yaw, mat):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UV')
    vs = [bm.verts.new((sx * w / 2, sy * h / 2, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[uvl].uv = uv
    o = from_bmesh(name, bm, C, smooth=False)
    s = o.modifiers.new('Solid', 'SOLIDIFY'); s.thickness = 0.002; s.offset = -1
    bevel(o, 0.0006, 2, 30)
    set_mat(o, mat)
    place(o, loc, yaw)
    return o

cutmat = make_mat_plane('CuttingMat', 0.60, 0.45, (0.0, 0.0, 0.002), math.radians(-3), mat_cutmat())

SHEETS = [  # name, image, w, h, center, yaw_deg, z
    ('BP_Car', 'act5_bp_car.png', 0.297, 0.210, (-0.22, -0.13), 25, 0.0024),
    ('SK_Gears', 'act5_sk_gears.png', 0.210, 0.297, (-0.31, 0.12), -10, 0.0026),
    ('BP_Watch', 'act5_bp_watch.png', 0.297, 0.210, (0.17, 0.11), -8, 0.0028),
    ('SK_Car', 'act5_sk_car.png', 0.297, 0.210, (0.17, -0.17), 6, 0.0030),
]
sheets = {}
for i, (nm, img, w, h, c, yaw, z) in enumerate(SHEETS):
    # v9 (CLIENT RULE never too bright): cyanotype paper is deep Prussian blue, sketch paper a warm mid-tone
    # v13: cyanotypes re-coloured (Prussian ground, pale lines, kept red markup) + fold creases that catch the lamp
    if nm.startswith('BP'):
        _m = mat_sheet(nm + 'M', os.path.join(TEXD, img), rough=0.82, tint='cyan', folds=((0, 0.004), (1, -0.021)) if nm == 'BP_Car' else ((0, -0.002),))
    else:
        _m = mat_sheet(nm + 'M', os.path.join(TEXD, img), albedo=0.56, folds=((1, 0.003),))
    sheets[nm] = make_sheet(nm, os.path.join(TEXD, img), w, h, (c[0], c[1], z), math.radians(yaw), C, curl=(0.0008 if nm == 'BP_Car' else 0.003 + 0.002 * (i % 2)), seed=i,
                            mat=_m)

print('[t] photo print (T4) %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- photo print (T4)
PH_C = Vector((-0.088, 0.066, 0.0046))
PH_YAW = math.radians(10)
IMG_W, IMG_H = 0.144, 0.081
PR_W, PR_H = 0.152, 0.100
IMG_OFF = Vector((0.0, PR_H / 2 - 0.004 - IMG_H / 2, 0.0))   # image centre in print-local coords
photo_path = PHOTO if os.path.exists(PHOTO) else PHOTO_FALLBACK
print('[act5] photo texture:', photo_path)

def make_photo():
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UV')
    nx, ny = 24, 16
    vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = (i / nx - 0.5) * PR_W
            y = (j / ny - 0.5) * PR_H
            # slight curl only on the bottom border strip (outside the image area)
            z = 0.0
            if y < -PR_H / 2 + 0.012:
                z = 0.0012 * ((-PR_H / 2 + 0.012 - y) / 0.012) ** 2
            u = (x - IMG_OFF.x + IMG_W / 2) / IMG_W
            v = (y - IMG_OFF.y + IMG_H / 2) / IMG_H
            row.append((bm.verts.new((x, y, z)), (u, v)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i][0], vs[j][i + 1][0], vs[j + 1][i + 1][0], vs[j + 1][i][0]))
            for l, (jj, ii) in zip(f.loops, ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))):
                l[uvl].uv = vs[jj][ii][1]
    o = from_bmesh('PhotoPrint', bm, C, smooth=True)
    s = o.modifiers.new('Solid', 'SOLIDIFY'); s.thickness = 0.0003; s.offset = -1
    b = NB('PhotoMat')
    tex = b.n('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(photo_path, check_existing=True)
    tex.extension = 'EXTEND'; tex.interpolation = 'Cubic'
    uv = b.coord('UV')
    b.link(uv, tex.inputs['Vector'])
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(uv, sep.inputs[0])
    inside = b.math('MULTIPLY', b.math('MULTIPLY', b.math('GREATER_THAN', sep.outputs['X'], 0.0), b.math('LESS_THAN', sep.outputs['X'], 1.0)),
                    b.math('MULTIPLY', b.math('GREATER_THAN', sep.outputs['Y'], 0.0), b.math('LESS_THAN', sep.outputs['Y'], 1.0)))
    paper = b.noise(b.coord('Object', 1.0), 3000.0, 3, 0.6)
    col = b.mix((0.70, 0.69, 0.65), tex.outputs['Color'], inside)      # v13: border 0.86 -> 0.70 (white smear in the whip)
    # v13: lustre print (coat 0.1, base rough 0.42-0.55, spec 0.3) + a touch of saturation on the lit print - the
    # glossy coat at grazing view under the overhead lamp made the hero print milky/faded through the 5A hold
    hs = b.n('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 1.1
    b.link(col, hs.inputs['Color'])
    b.set('Base Color', hs.outputs['Color'])
    b.set('Roughness', b.maprange(paper.outputs['Fac'], 0.3, 0.7, 0.42, 0.55))
    b.set('Coat Weight', 0.1).set('Coat Roughness', 0.12)
    try:
        b.set('Specular IOR Level', 0.3)
    except Exception:
        pass
    b.set('Normal', b.bump(paper.outputs['Fac'], 0.04, 0.0001))
    # v5 T4: boost=1 -> the image area is a pure emitter of the image (no lamp glint / coat veil / bloom), crossfading
    # to the lit print as the whip starts. v13: only the image area emits (the white border stayed a 1.0 emitter and
    # smeared white across the whip frames); emission 1.0 under the Standard view on f1-9 (see t4_view below)
    boost = b.n('ShaderNodeValue'); boost.outputs[0].default_value = 0.0; boost.name = 'PhotoBoost'
    em = b.n('ShaderNodeEmission'); b.link(tex.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    msh = b.n('ShaderNodeMixShader')
    b.link(b.math('MULTIPLY', boost.outputs[0], inside), msh.inputs[0]); b.link(b.bsdf.outputs[0], msh.inputs[1]); b.link(em.outputs[0], msh.inputs[2])
    b.link(msh.outputs[0], b.out.inputs['Surface'])
    set_mat(o, b.mat)
    o.location = PH_C
    o.rotation_euler = (0, 0, PH_YAW)
    return o, boost

photo, photo_boost = make_photo()
IMG_C = PH_C + Matrix.Rotation(PH_YAW, 3, 'Z') @ IMG_OFF

print('[t] watch %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- watch
W = Vector((0.17, 0.10, 0.0031))
W_YAW = math.radians(-20)
watch, wgears, balance = make_watch('PW', C, M, rng, lid_angle=30.0)
watch.location = W
watch.rotation_euler = (0, 0, W_YAW)
for g, teeth, rate, d, ph in wgears:
    spin_gear(g, teeth, 1, 90, turns_per_sec=rate * 3.0, direction=d, phase=ph)     # v7: x3 - the 5C end must visibly turn
# v13 T5 mesh geometry (watch-local, mirrors make_watch): centre wheel r 7.2 mm at z 6.0, third pinion on the -39 deg line
TH3, RC, ZC = math.radians(-39.0), 0.0072, 0.0060
_MF = Vector(((RC + 0.0004) * math.cos(TH3), (RC + 0.0004) * math.sin(TH3), ZC - 0.0001))     # local T5 focus point

def _hdir(deg, r):
    a = TH3 + math.radians(deg)
    return (Vector((r * math.cos(a), r * math.sin(a), 0)) - Vector((_MF.x, _MF.y, 0))).normalized()

def _sph(hd, dist, el):
    return _MF + (hd * math.cos(math.radians(el)) + Vector((0, 0, math.sin(math.radians(el))))) * dist
# T5 end camera (local): looks down 35-40 deg onto the centre-wheel / third-pinion engagement from outside the rim;
# warm + cool practicals behind the mesh (warm glints on the teeth tops, cool backlight through the haze slab)
END_CAM_LOCAL = (_sph(_hdir(62.0, 0.0105), 0.0085, 40.0), _sph(_hdir(50.0, 0.0105), 0.0060, 35.0))
_BDIR = -_hdir(50.0, 0.0105)
# v17: warm practical moved out of the wheel-face mirror direction (35 deg) to a 14 deg grazing rim light from the
# left-behind (the v14-v16 position lit the whole face cream: YAVG 72 vs 6A's 27)
_ang = math.atan2(_BDIR.y, _BDIR.x) - math.radians(35.0)
WARM_LOCAL = _sph(Vector((math.cos(_ang), math.sin(_ang), 0.0)), 0.0075, 14.0)
COOL_LOCAL = _sph(_BDIR, 0.0060, 8.0)
for f in range(1, 91):  # balance oscillation 2.5 Hz
    fc_key(balance, 'rotation_euler', 2, [(f, math.radians(200) * math.sin(2 * math.pi * 2.5 * f / FPS))], interp='LINEAR')
# chain from the bow curving across the bp sheet
Wm = Matrix.Translation(W) @ Matrix.Rotation(W_YAW, 4, 'Z')
chain_pts = [Wm @ Vector((0, 0.025 + 0.020, 0.0008)), Wm @ Vector((0.006, 0.055, 0.0008)), Wm @ Vector((0.025, 0.07, 0.0008)),
             Wm @ Vector((0.05, 0.066, 0.0008)), Wm @ Vector((0.072, 0.05, 0.0008)), Wm @ Vector((0.085, 0.022, 0.0008)), Wm @ Vector((0.09, -0.01, 0.0008))]
for p in chain_pts:
    p.z = 0.0036
make_chain('Chain', C, chain_pts, M['gold'])

# 5C-only (keyed in apply_shot_state): haze + glowing specks inside the case once the lens is under the crystal
# v13: a thin cool slab between the plate and the wheels (local z 4.45-6.65 mm), not a column between lens and subject:
# it glows blue behind the teeth (6A's cool-haze background) without veiling them
haze = cyl('WatchHaze', 0.0212, 0.0022, loc=W + Vector((0, 0, 0.00555)), segs=48, coll=C)
set_mat(haze, mat_volume('WatchHazeVol', density=45.0, color=(0.45, 0.65, 1.0), anisotropy=0.55))
haze.visible_shadow = False
_sb = bmesh.new()
_sr = random.Random(21)
_Rw0 = Matrix.Rotation(W_YAW, 3, 'Z')
_endcam = [W + _Rw0 @ v for v in END_CAM_LOCAL]
_k = 0
while _k < 40:
    a = _sr.uniform(0, 2 * math.pi); rr = 0.019 * math.sqrt(_sr.random())
    p = W + Vector((rr * math.cos(a), rr * math.sin(a), _sr.uniform(0.0058, 0.0114)))
    from desk_more import seg_dist as _sd
    if _sd(p, _endcam[0], _endcam[1]) < 0.003:
        continue          # v13: nothing within 3 mm of the T5 creep (giant bokeh discs)
    _k += 1
    bmesh.ops.create_icosphere(_sb, subdivisions=1, radius=_sr.uniform(0.000010, 0.000024), matrix=Matrix.Translation(p))
specks = from_bmesh('WatchSpecks', _sb, C)
# CLIENT RULE: no emissive "magic" bits - a few real dust specks that only catch the lamp (bokeh when out of focus)
set_mat(specks, mat_principled('Speck', (0.85, 0.80, 0.72), rough=0.35))
specks.visible_shadow = False
for o in (haze, specks):
    o.hide_render = True

print('[t] pencils %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- pencils
pmats = (M['cedar'], M['graphite'], M['ferrule'], M['eraser'])
from desk_more import mat_pencil_paint
_foil = os.path.join(TEXD, 'act5_pencil_foil.png')
if os.path.exists(_foil):
    mat_pencil_paint(_foil)          # registers 'PencilPaint' -> make_pencil picks it up
PENCILS = [  # name, color, tip(x,y), tip-direction deg, sharpened, eraser, z-surface
    ('PencilGreen', (0.015, 0.10, 0.04), (-0.1735, -0.081), 210, True, False, 0.0026),
    ('PencilBlack', (0.008, 0.008, 0.010), (-0.1250, -0.079), 195, True, True, 0.0026),     # v18: tip out of the 5B track (flew over the cone = 'finger')
    ('PencilRed', (0.32, 0.018, 0.012), (-0.36, -0.03), 250, True, False, 0.0028),
    ('PencilOchre', (0.50, 0.30, 0.03), (0.30, 0.045), 120, True, True, 0.0030),
    ('PencilBlue', (0.010, 0.035, 0.12), (-0.02, 0.165), 165, True, False, 0.0022),
]
RH = 0.0037
for nm, col, tip, deg, sh, er, zs in PENCILS:
    root = make_pencil(nm, col, coll=C, eraser=er, sharpen=sh, mats=pmats)
    d = Vector((math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0))
    L = 0.165
    ctr = Vector((tip[0], tip[1], 0)) - d * (L / 2)
    root.location = (ctr.x, ctr.y, zs + RH * math.cos(math.radians(30)))
    root.rotation_euler = (math.radians(30), 0, math.radians(deg))
SHAVINGS = [((-0.176, -0.128), 'PencilGreen'),      # v22: was right under the 5B lens at f28 (blurred flesh-coloured blob) ((-0.152, -0.118), 'PencilBlack'), ((-0.205, -0.085), 'PencilGreen'),
            ((-0.118, -0.098), 'PencilRed'), ((-0.33, -0.06), 'PencilRed'), ((0.262, 0.03), 'PencilOchre')]
for i, ((x, y), pn) in enumerate(SHAVINGS):
    shv = make_shaving(f'Shaving{i}', C, bpy.data.materials.get('PencilPaint'), M['cedar_shv'], seed=i)
    shv.color = (*[p for p in PENCILS if p[0] == pn][0][1], 1.0)
    shv.location = (x, y, 0.0028)
    shv.rotation_euler = (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0, 6.28))
    s_ = rng.uniform(0.8, 1.2); shv.scale = (s_, s_, s_)
# steel rule lying across the top of the mat
rule = box('SteelRule', (0.30, 0.025, 0.0009), loc=(0.02, 0.20, 0.0026), rot=(0, 0, math.radians(-4)), coll=C, bev=0.0002)
set_mat(rule, mat_caliper('RuleSteel', band_y=0.0125, face_z=0.0004, x0=-0.148, x1=0.148))
mp = make_mech_pencil('MechPencil', C, (M['chrome'], M['blackgrip'], M['chrome']))
mp.location = (-0.20, 0.185, 0.0026 + 0.0042)
mp.rotation_euler = (0, 0, math.radians(160))

print('[t] tools %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- tools
cal = make_calipers('Calipers', C, M['caliper'], M['dark'])
cal.location = (0.005, -0.075, 0.0032)
cal.rotation_euler = (0, 0, math.radians(18))
tw = make_tweezers('Tweezers', C, M['steel'])
tw.location = (0.085, 0.175, 0.0030)
tw.rotation_euler = (0, 0, math.radians(200))
LOUPE_C = Vector((0.036, 0.024, 0.0040))
loupe = make_loupe('Loupe', C, M['loupe_brass'], M['lens'], M['dark'])
loupe.location = LOUPE_C
loupe.rotation_euler = (0, 0, math.radians(26))
eraser = box('EraserBlock', (0.042, 0.019, 0.011), loc=(-0.205, 0.0, 0.0024 + 0.0055), rot=(0, 0, math.radians(-30)), coll=C, bev=0.0015, seg=3)
set_mat(eraser, M['eraserblock'])
sleeve = box('EraserSleeve', (0.026, 0.0196, 0.0116), loc=(-0.205 - 0.006 * math.cos(math.radians(-30)), -0.006 * math.sin(math.radians(-30)), 0.0024 + 0.0055), rot=(0, 0, math.radians(-30)), coll=C, bev=0.0006)
set_mat(sleeve, mat_paint('Sleeve', (0.02, 0.10, 0.30), 0.35))

# coffee mug (background left)
mug = revolve('Mug', [(0.0, 0.0), (0.040, 0.0), (0.043, 0.004), (0.044, 0.095), (0.041, 0.096), (0.038, 0.090), (0.037, 0.008), (0.0, 0.008)], 64, C)
set_mat(mug, M['mug']); mug.location = (-0.50, 0.33, 0.0)
handle = prim('torus', 'MugHandle', loc=(-0.50 + 0.048, 0.33, 0.05), rot=(math.pi / 2, 0, 0), coll=C, R=0.024, r=0.006, su=48, sv=12)
handle.scale = (0.8, 1.0, 1.0)
set_mat(handle, M['mug'])
coffee = cyl('Coffee', 0.038, 0.001, loc=(-0.50, 0.33, 0.078), segs=64, coll=C)
set_mat(coffee, M['coffee'])

# v4 background depth props (out-of-focus shapes behind the work in 5A, silhouettes in 5B)
from desk_more import make_books, make_pencil_cup, make_parts_tray, mat_cloth, mat_pages
covers = [mat_cloth('ClothGreen', (0.018, 0.045, 0.03)), mat_cloth('ClothRed', (0.13, 0.021, 0.012)), mat_cloth('ClothNavy', (0.012, 0.018, 0.054))]   # v13 x0.6
make_books('Books', C, (0.20, 0.45, 0.0), math.radians(-12), [(0.24, 0.17, 0.032, 0, 0.0), (0.22, 0.155, 0.026, 1, 0.08), (0.20, 0.14, 0.030, 2, -0.05)],
           covers, mat_pages())
make_pencil_cup('PencilCup', C, (-0.25, 0.40, 0.0), M['mug'],
                [(0.32, 0.018, 0.012), (0.015, 0.10, 0.04), (0.50, 0.30, 0.03), (0.008, 0.008, 0.01), (0.01, 0.035, 0.12), (0.62, 0.58, 0.52)], pmats, rng)

print('[t] scattered parts (instanced) %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- scattered parts (instanced)
screw_src = []
for k, (hm, r) in enumerate(((M['blued'], 0.0008), (M['wsteel'], 0.0011), (M['wbrass'], 0.0009))):
    s = cyl(f'ScrewSrc{k}', r, r * 0.7, loc=(0, 0, -1), segs=20, coll=C, bev=r * 0.18)
    shaft = cyl(f'ScrewShaft{k}', r * 0.45, r * 3.2, loc=(0, 0, -1 - r * 1.8), segs=12, coll=C)
    set_mat(s, hm); set_mat(shaft, hm)
    shaft.parent = s; shaft.location = (0, 0, -r * 1.8)
    screw_src.append((s, shaft))
gear_src = []
for k, (t, r) in enumerate(((12, 0.0022), (18, 0.0032), (24, 0.0045), (30, 0.0058), (10, 0.0016))):
    g = make_gear(f'LooseGear{k}', teeth=t, r=r, depth=r * 0.12, thick=0.0005, hole=0.0003, spokes=4 + k % 2, coll=C,
                  mat=M['wbrass'] if k % 3 else M['wsteel'], bevel_w=0.00006)
    g.location = (0, 0, -1)
    gear_src.append(g)
# bake the bevels into the shared source meshes once, so ~500 instances don't each evaluate a Bevel modifier
for _o in [g for g in gear_src] + [s for s, sh in screw_src] + [sh for s, sh in screw_src]:
    apply_mods(_o)
print('[t] part sources baked %.1f' % (time.time() - T0))

def surf_z(x, y):
    """Approximate surface height at (x,y): sheets/mat/desk."""
    best = 0.0
    if abs(x) < 0.3 and abs(y) < 0.225:
        best = 0.002
    for nm, img, w, h, c, yaw, z in SHEETS:
        a = -math.radians(yaw)
        lx = (x - c[0]) * math.cos(a) - (y - c[1]) * math.sin(a)
        ly = (x - c[0]) * math.sin(a) + (y - c[1]) * math.cos(a)
        if abs(lx) < w / 2 - 0.01 and abs(ly) < h / 2 - 0.01:
            best = max(best, z + 0.00025)
    return best

# 5B FPV path (frame, (x, y, z)). v13: a lateral S over the blueprint (f1-24) so the bank fires, lower (more ground
# rush), and the end keeps its speed: skims past the case rim at ~7 mm and whips up over the lid (cut lands mid-move)
B_PTS = [
    (1, (-0.400, -0.235, 0.030)), (6, (-0.364, -0.190, 0.022)), (12, (-0.303, -0.192, 0.017)), (18, (-0.267, -0.1415, 0.014)),
    (24, (-0.215, -0.122, 0.012)), (32, (-0.170, -0.099, 0.0098)), (38, (-0.140, -0.080, 0.0088)), (44, (-0.100, -0.058, 0.0098)),
    (50, (-0.058, -0.028, 0.011)), (56, (-0.012, 0.000, 0.017)), (62, (0.030, 0.022, 0.016)), (67, (0.072, 0.036, 0.012)),
    (71, (0.112, 0.058, 0.011)), (74, (0.140, 0.064, 0.013)), (77, (0.165, 0.068, 0.020)), (80, (0.188, 0.071, 0.034)),
    (84, (0.205, 0.076, 0.052))]
_PATH_XY = [Vector((p[0], p[1], 0)) for f, p in B_PTS if f <= 62]

def keep_out(x, y):
    if (Vector((x, y, 0)) - Vector((W.x, W.y, 0))).length < 0.04:
        return True
    from desk_more import seg_dist
    if any(seg_dist(Vector((x, y, 0)), a, b) < 0.009 for a, b in zip(_PATH_XY[:-1], _PATH_XY[1:])):
        return True      # nothing directly under the 5B lens (giant out-of-focus blobs)
    if (Vector((x, y, 0)) - Vector((LOUPE_C.x, LOUPE_C.y, 0))).length < 0.04:
        return True
    a = -PH_YAW
    lx = (x - PH_C.x) * math.cos(a) - (y - PH_C.y) * math.sin(a)
    ly = (x - PH_C.x) * math.sin(a) + (y - PH_C.y) * math.cos(a)
    return abs(lx) < PR_W / 2 + 0.003 and abs(ly) < PR_H / 2 + 0.003

n_inst = 0

def put_part(kind, x, y, tag, rz=None, lying=None, z_extra=0.0, z_base=None):
    """kind: ('g', gear_src index) | ('s', screw_src index)."""
    z = (surf_z(x, y) if z_base is None else z_base) + z_extra
    rz = rng.uniform(0, 6.28) if rz is None else rz
    if kind[0] == 'g':
        o = inst(gear_src[kind[1]], tag, (x, y, z + 0.00028), (rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), rz), coll=C)
    else:
        s, sh = screw_src[kind[1]]
        ly = (rng.random() < 0.6) if lying is None else lying
        if ly:
            o = inst(s, tag, (x, y, z + 0.0009), (math.pi / 2 + rng.uniform(-0.08, 0.08), 0, rz), coll=C)
        else:
            o = inst(s, tag, (x, y, z + 0.0004), (0, 0, rz), coll=C)
        sh2 = bpy.data.objects.new(tag + 's', sh.data); link(sh2, C); sh2.parent = o; sh2.location = sh.location
    return o

# v13 (CLIENT RULE: no evenly-spread specks): the v4-v12 uniform ring scatter (170) + gaussian corridor (140) read as
# sprinkles / a laid-out runway. Now purposeful layouts: spilled piles beside the 5B path with empty paper between,
# a disassembled-movement row on a watchmaker's cloth beside the watch, a small pile under the tweezer tips.
PATH_A, PATH_B = Vector((-0.36, -0.215, 0)), Vector((0.03, 0.022, 0))
_nrm = Vector((-(PATH_B - PATH_A).y, (PATH_B - PATH_A).x, 0)).normalized()
for ci, (t, off, cnt, rad) in enumerate(((0.09, 0.028, 16, 0.008), (0.20, -0.019, 22, 0.010), (0.33, 0.016, 12, 0.006), (0.27, 0.040, 9, 0.006))):
    cc = PATH_A.lerp(PATH_B, t) + _nrm * off
    for k in range(cnt):
        a = rng.uniform(0, 2 * math.pi); d = rad * rng.random() ** 1.4
        x, y = cc.x + d * math.cos(a), cc.y + d * math.sin(a)
        if keep_out(x, y):
            continue
        kind = ('g', rng.randrange(5)) if rng.random() < 0.3 else ('s', rng.randrange(3))
        put_part(kind, x, y, f'CL{ci}_{k}', z_extra=0.0003 * (k % 3) * (d < rad * 0.5))
        n_inst += 1
# watchmaker's cloth with a disassembled movement laid out in rows (beside the watch, toward the 5B/5C cameras)
CL_C, CL_YAW = W + Vector((-0.006, -0.066, 0.0)), math.radians(-14)
CL_Z = 0.0031
from desk_more import mat_cloth as _mat_cloth
cloth = box('PartsCloth', (0.100, 0.052, 0.0012), loc=(CL_C.x, CL_C.y, CL_Z + 0.0006), rot=(0, 0, CL_YAW), coll=C, bev=0.0005)
set_mat(cloth, _mat_cloth('Chamois', (0.035, 0.06, 0.05)))
_cr = Matrix.Rotation(CL_YAW, 3, 'Z')
def cl_pt(lx, ly):
    p = CL_C + _cr @ Vector((lx, ly, 0))
    return p.x, p.y
_gx = -0.040
for k, gi in enumerate((3, 2, 1, 0, 4)):
    r_ = (0.0058, 0.0045, 0.0032, 0.0022, 0.0016)[k]
    if k:
        _gx += (0.0058, 0.0045, 0.0032, 0.0022, 0.0016)[k - 1] + 0.0022 + r_
    x, y = cl_pt(_gx, 0.011)
    put_part(('g', gi), x, y, f'CLG{k}', z_base=CL_Z + 0.0012); n_inst += 1
for k in range(9):
    x, y = cl_pt(-0.040 + k * 0.0048, -0.006)
    put_part(('s', k % 3), x, y, f'CLS{k}', rz=CL_YAW + math.pi / 2, lying=True, z_base=CL_Z + 0.0012); n_inst += 1
for k in range(6):
    x, y = cl_pt(-0.040 + k * 0.0062, -0.017)
    put_part(('s', (k + 1) % 3), x, y, f'CLT{k}', lying=False, z_base=CL_Z + 0.0012); n_inst += 1
# brass dish with the only loose jewels (4) on the cloth
_dx, _dy = cl_pt(0.030, 0.004)
dish = revolve('JewelDish', [(0.0, 0.0), (0.0095, 0.0), (0.0102, 0.0028), (0.0094, 0.0030), (0.0088, 0.0011), (0.0, 0.0011)], 64, C)
dish.location = (_dx, _dy, CL_Z + 0.0012); set_mat(dish, M['gold'])
for k in range(4):
    a = rng.uniform(0, 6.28); d = rng.uniform(0.0, 0.004)
    j = cyl(f'LooseJewel{k}', 0.0006, 0.0003, loc=(_dx + d * math.cos(a), _dy + d * math.sin(a), CL_Z + 0.0012 + 0.00125), segs=16, coll=C)
    set_mat(j, M['ruby'])
# small pile under the tweezer tips
for k in range(14):
    a = rng.uniform(0, 2 * math.pi); d = 0.006 * rng.random() ** 1.3
    x, y = 0.024 + d * math.cos(a), 0.150 + d * math.sin(a)
    put_part(('g', rng.randrange(5)) if k % 4 == 0 else ('s', rng.randrange(3)), x, y, f'TWP{k}', z_extra=0.0003 * (k % 2)); n_inst += 1
# a few strays
for k in range(8):
    for _ in range(30):
        x, y = rng.uniform(-0.27, 0.27), rng.uniform(-0.20, 0.20)
        if not keep_out(x, y) and (Vector((x, y, 0)) - CL_C).length > 0.07:
            break
    put_part(('s', rng.randrange(3)) if k % 3 else ('g', rng.randrange(5)), x, y, f'STR{k}'); n_inst += 1
# watchmaker's parts tray (hundreds of tiny parts, background right)
jewel_src = cyl('JewelSrc', 0.0006, 0.0003, loc=(0, 0, -1), segs=16, coll=C); set_mat(jewel_src, M['ruby'])
M['tray'] = mat_principled('TrayAnod', (0.05, 0.06, 0.07), rough=0.32, metal=1.0)
M['_tray_src'] = [(gear_src[0], 1.0), (screw_src[0][0], 1.0), (gear_src[2], 0.8), (jewel_src, 1.3), (screw_src[2][0], 1.0), (gear_src[4], 1.0)]
_, n_tray = make_parts_tray('PartsTray', C, (0.33, 0.30, 0.0), math.radians(8), M, rng)
n_inst += n_tray
jewel_src.hide_render = True
for s, sh in screw_src:
    s.hide_render = True; sh.hide_render = True
for g in gear_src:
    g.hide_render = True

print('[t] instanced parts + tray done %.1f' % (time.time() - T0))
# eraser crumbs + desk dust
def crumb_region(r):
    a = r.uniform(0, 2 * math.pi); d = abs(r.gauss(0, 0.03))
    return (-0.205 + d * math.cos(a) * 1.4, 0.0 + d * math.sin(a))
crumbs = scatter_mesh('EraserCrumbs', C, 420, crumb_region, (0.0003, 0.0011), surf_z, M['crumb'], seed=4)
set_mat(crumbs, M['crumb'])
print('[t] crumbs done %.1f' % (time.time() - T0))
from desk_more import fast_cubes
def _not_on_bp(x, y):
    for nm, img, w, h, c, yaw, z in SHEETS:
        if not nm.startswith('BP'):
            continue
        a = -math.radians(yaw)
        lx = (x - c[0]) * math.cos(a) - (y - c[1]) * math.sin(a)
        ly = (x - c[0]) * math.sin(a) + (y - c[1]) * math.cos(a)
        if abs(lx) < w / 2 and abs(ly) < h / 2:
            return False
    return True
# v13: grime, not glitter - none on the cyanotypes, darker
dust = fast_cubes('DeskDust', C, 5000, (-0.30, 0.30, -0.22, 0.22), (0.00006, 0.00022), surf_z, seed=5, keep=_not_on_bp)
M['dust'] = mat_principled('Dust', (0.22, 0.21, 0.19), rough=0.95)
set_mat(dust, M['dust'])
print('[t] crumbs + dust done %.1f' % (time.time() - T0))
from desk_more import motes_avoid
_B_AVOID = [p for f, p in B_PTS]
_C_AVOID = [tuple(W + Vector(v)) for v in ((0.055, -0.07, 0.03), (0.015, -0.085, 0.075), (-0.03, -0.04, 0.075), (0.0, 0.0, 0.02), (0.0, 0.0, 0.0))]
mo = motes_avoid('Motes', C, 280, (-0.30, 0.30, -0.25, 0.45, 0.004, 0.22), (0.00003, 0.00009), M['mote'], [_B_AVOID, _C_AVOID, ([tuple(IMG_C), tuple(IMG_C + Vector((0, 0, 0.3)))], 0.095)], clear=0.03, seed=6)

print('[t] room: walls, window, lamp %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- room: walls, window, lamp
wall_x = -0.82
win = (-0.30, 0.48, 0.10, 0.92)   # y0, y1, z0, z1
def wall_box(name, y0, y1, z0, z1):
    o = box(name, (0.06, y1 - y0, z1 - z0), loc=(wall_x - 0.03, (y0 + y1) / 2, (z0 + z1) / 2), coll=C)
    set_mat(o, M['wall'])
    return o
wall_box('WallBelow', -2.0, 2.0, -1.0, win[2]); wall_box('WallAbove', -2.0, 2.0, win[3], 2.0)
wall_box('WallFront', -2.0, win[0], win[2], win[3]); wall_box('WallBack', win[1], 2.0, win[2], win[3])
frame_mat = mat_principled('WindowFrame', (0.02, 0.022, 0.025), rough=0.6)
# v13: a real 3 x 2 sash: 12 mm glazing bars + a 26 mm meeting rail -> the moon spot draws a readable window
# pattern (the v7-v12 mullions cast one thick diagonal bar that read as a beam)
_mulls = {'MullH': ((win[0] + win[1]) / 2, (win[2] + win[3]) / 2, win[1] - win[0], 0.026)}
for k in (1, 2):
    _mulls[f'MullV{k}'] = (win[0] + (win[1] - win[0]) * k / 3.0, (win[2] + win[3]) / 2, 0.012, win[3] - win[2])
for k, zz_ in enumerate((win[2] + (win[3] - win[2]) * 0.25, win[2] + (win[3] - win[2]) * 0.75)):
    _mulls[f'MullH{k + 2}'] = ((win[0] + win[1]) / 2, zz_, win[1] - win[0], 0.012)
for nm, (yy, zz, sy, sz) in _mulls.items():
    o = box(nm, (0.04, sy, sz), loc=(wall_x - 0.02, yy, zz), coll=C, bev=0.002)
    set_mat(o, frame_mat)
back = box('BackWall', (3.0, 0.06, 2.5), loc=(0, 0.62, 0.6), coll=C)
set_mat(back, M['wall'])
sky = box('Sky', (0.02, 3.0, 2.0), loc=(wall_x - 0.9, 0.0, 0.6), coll=C)
set_mat(sky, M['sky'])
sky.visible_shadow = False
# v6: EEVEE still let this backdrop shadow the moon (probe: every moon ray from the back wall hit 'Sky') and no
# shot looks out of the window -> drop it; the moonlight now actually enters.
sky.hide_render = True
# pegboard + hanging tool silhouettes on back wall (out of focus depth)
peg = box('Pegboard', (0.9, 0.012, 0.5), loc=(0.15, 0.585, 0.42), coll=C)
from desk_more import mat_pegboard
set_mat(peg, mat_pegboard())
for i in range(9):
    t = box(f'ToolSil{i}', (0.01 + 0.02 * (i % 3), 0.006, 0.12 + 0.06 * (i % 4)), loc=(-0.22 + i * 0.09, 0.575, 0.52 - 0.03 * (i % 3)), coll=C, bev=0.002)
    set_mat(t, M['steel'] if i % 2 else M['loupe_brass'])
# shelf with jars (catches window light; bokeh)
shelf = box('Shelf', (0.7, 0.12, 0.012), loc=(-0.35, 0.53, 0.55), coll=C, bev=0.002)
set_mat(shelf, M['walnut'])
glass_jar = mat_glass('JarGlass', (0.85, 0.92, 0.95), 0.05)
for i in range(5):
    jar = revolve(f'Jar{i}', [(0.0, 0.0), (0.03, 0.0), (0.032, 0.004), (0.032, 0.09 + 0.02 * (i % 2)), (0.022, 0.1 + 0.02 * (i % 2)), (0.0, 0.1 + 0.02 * (i % 2))], 32, C)
    jar.location = (-0.62 + i * 0.13, 0.53, 0.556)
    set_mat(jar, glass_jar)

# v4: lamp hangs high over the work and points nearly straight down -> from every camera we see the
# shade from the side (dark enamel + hot rim) and a light cone in the haze, never the bulb face-on.
LAMP_HEAD = Vector((0.06, 0.20, 0.36))
LAMP_TGT = Vector((0.0, 0.13, 0.0))
lamp_root, lamp_head = make_lamp('Lamp', C, M['enamel_lamp'], M['steel'], M['bulb'], M['lamp_inner'])
lamp_root.location = (0.44, 0.50, 0.0)
lamp_head.location = LAMP_HEAD
look_at(lamp_head, LAMP_TGT)
# arms: base -> elbow -> head
def rod(name, a, b, r=0.005, mat=None):
    a, b = Vector(a), Vector(b)
    d = b - a
    o = cyl(name, r, d.length, loc=(a + b) / 2, segs=16, coll=C)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    set_mat(o, mat or M['enamel_lamp'])
    return o
elbow = Vector((0.40, 0.50, 0.47))
rod('LampArm1', (0.44, 0.50, 0.03), elbow); rod('LampArm1b', (0.455, 0.505, 0.03), elbow + Vector((0.015, 0, 0)), 0.0025, M['steel'])
neck = LAMP_HEAD + (LAMP_HEAD - LAMP_TGT).normalized() * 0.07
rod('LampArm2', elbow, neck); rod('LampArm2b', elbow + Vector((0, 0.012, 0)), neck + Vector((0, 0.012, 0)), 0.0025, M['steel'])
jt = prim('sphere', 'LampElbow', loc=elbow, coll=C, r=0.011); set_mat(jt, M['steel'])
jt2 = prim('sphere', 'LampNeck', loc=neck, coll=C, r=0.009); set_mat(jt2, M['steel'])

print('[t] lights %.1f' % (time.time() - T0))
# ----------------------------------------------------------------------------- lights
lamp_spot = light('SPOT', 'LampSpot', LAMP_HEAD + (LAMP_HEAD - LAMP_TGT).normalized() * 0.03, energy=46.0, color=(1.0, 0.62, 0.34),
                  spot=95, blend=0.75, shadow_soft=0.012, target=LAMP_TGT, volume=1.1)
lamp_spot.data.spot_size = math.radians(92)
bulb_glow = light('POINT', 'BulbGlow', LAMP_HEAD + (LAMP_HEAD - LAMP_TGT).normalized() * 0.012, energy=0.25, color=(1.0, 0.6, 0.3), shadow_soft=0.02, volume=0.0)
moon = light('SUN', 'Moon', (wall_x - 0.5, 0.0, 1.0), energy=9.0, color=(0.36, 0.52, 1.0), size=0.8, volume=1.4)
mdir = Vector((0.80, 0.36, -0.48)).normalized()     # v4: rakes toward the back wall -> blue window patch behind the work
moon.rotation_euler = mdir.to_track_quat('-Z', 'Y').to_euler()
# v7: the SUN never showed up in any render (even with the backdrop gone) -> moonlight as a distant, narrow spot
# aimed through the window: hard mullion shadows, window patch on desk + back wall, shafts in the haze.
moon.data.energy = 0.0
win_c = Vector((wall_x, (win[0] + win[1]) / 2, (win[2] + win[3]) / 2))
moon_spot = light('SPOT', 'MoonSpot', win_c - mdir * 2.2, energy=420.0, color=(0.36, 0.52, 1.0), spot=34, blend=0.35,
                  shadow_soft=0.015, target=win_c + mdir * 0.8, volume=1.2)
rimL = light('AREA', 'CoolRim', (0.05, 0.56, 0.42), energy=2.0, color=(0.5, 0.65, 1.0), size=0.5, size_y=0.12, target=(0.0, 0.0, 0.0), volume=0.0)
wfill = light('AREA', 'WatchFill', (W.x - 0.01, W.y + 0.03, 0.11), energy=0.03, color=(1.0, 0.72, 0.45), size=0.03, target=W, volume=0.0)
# v13 T5: cool kicker INSIDE the case (the old one sat outside at 77 mm, 0.06 W, and the case wall shadowed it):
# grazing from the side of the centre/third mesh, above the train bridge -> blue rims on the teeth flanks + lights
# the thin haze slab behind the wheels (6A's cool backlit haze)
_Rw = Matrix.Rotation(W_YAW, 3, 'Z')
MESH_W = W + _Rw @ _MF
wcool = light('POINT', 'WatchCool', W + _Rw @ COOL_LOCAL, energy=0.02, color=(0.42, 0.62, 1.0), shadow_soft=0.0004, volume=1.0)
wwarm = light('AREA', 'WatchWarm', W + _Rw @ WARM_LOCAL, energy=0.03, color=(1.0, 0.66, 0.36), size=0.003, target=MESH_W, volume=0.0)
print('[act5] build time %.1fs, instanced parts %d, objects %d, materials %d' % (time.time() - T0, n_inst, len(bpy.data.objects), len(bpy.data.materials)))

# ----------------------------------------------------------------------------- camera helpers
SHOT_STATE = {}

def cam_obj(name, lens=24, fstop=2.8, sensor=36.0):
    """sensor < 36 = 'small-sensor macro': same FOV with a proportionally shorter lens, so EEVEE's thin-lens
    CoC (~ f/(s-f)) stays sane when the focus distance gets down to a few millimetres."""
    c = camera(name, (0, 0, 1), lens=lens * sensor / 36.0, fstop=fstop, focus=0.2, clip=(0.0004, 30.0), sensor=sensor)
    c.data.sensor_fit = 'HORIZONTAL'
    return c

def look_rot(pos, tgt, up=Vector((0, 0, 1)), roll=0.0, prev=None):
    f = (Vector(tgt) - Vector(pos)).normalized()
    up = Vector(up)
    r = f.cross(up)
    if r.length < 1e-6:
        r = f.cross(Vector((0, 1, 0)))
    r.normalize()
    u = r.cross(f).normalized()
    m = Matrix((r, u, -f)).transposed()          # columns: x=r, y=u, z=-f
    m = m @ Matrix.Rotation(roll, 3, 'Z')
    return m.to_euler('XYZ', prev) if prev is not None else m.to_euler('XYZ')

def key_cam(c, f, pos, eul):
    c.location = pos
    c.rotation_euler = eul
    c.keyframe_insert('location', frame=f)
    c.keyframe_insert('rotation_euler', frame=f)

def lin_keys(o):
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

def catmull(P, t):
    """P: list of Vectors at integer params; t in [0, len-1]."""
    n = len(P)
    i = max(0, min(n - 2, int(math.floor(t))))
    u = t - i
    p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(n - 1, i + 2)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

# ----------------------------------------------------------------------------- 5A: photo -> whip pull-back
def setup_5A():
    lens0 = 22.0
    c = cam_obj('Cam5A', lens0, 2.8)
    d0 = IMG_W * lens0 / 36.0
    P0 = IMG_C + Vector((0, 0, d0))
    E = Vector((-0.115, -0.215, 0.165))
    L1 = Vector((-0.045, 0.10, 0.035))
    py = Matrix.Rotation(PH_YAW, 3, 'Z') @ Vector((0, 1, 0))
    foc = empty('Focus5A', loc=IMG_C)
    c.data.dof.focus_object = foc
    # speed ramp: hold to f9, whip f9..f30 (fast start, settling), slow drift to f52
    fh, fw = 9, 34
    def s_of(f):
        if f <= fh:
            return 0.0
        u = (f - fh) / (fw - fh)
        if u >= 1:
            return 1.0 + 0.04 * (f - fw) / 18.0
        ramp = min(1.0, u / 0.10)
        e = (1 - 2 ** (-7 * u)) / (1 - 2 ** -7)
        return e * (0.35 + 0.65 * ramp) + (1 - (0.35 + 0.65 * ramp)) * u * u
    prev = None
    for f in range(1, 53):
        s = s_of(f)
        sp = min(s, 1.0)
        mid = IMG_C + Vector((0, 0, 0.30))
        pos = (1 - sp) ** 2 * P0 + 2 * (1 - sp) * sp * mid + sp ** 2 * E
        if s > 1:
            pos = E + (E - L1).normalized() * (s - 1) * 0.5 + Vector((0.03, 0, 0)) * (s - 1) * 26     # slow lateral slide = parallax on the hold
        # v13: the hold is no longer static - a slow 4 cm push-in toward the work over f24-46
        pos = pos + (L1 - pos).normalized() * 0.04 * smooth((f - 24) / 22.0) * (1.0 if f > 24 else 0.0)
        tgt = IMG_C.lerp(L1, smooth(sp * 1.1))
        up = py.lerp(Vector((0, 0, 1)), smooth(sp * 1.4)).normalized()
        roll = math.radians(14) * math.sin(math.pi * min(1, sp)) * (1 - sp) * 2.2
        eul = look_rot(pos, tgt, up, roll, prev)
        prev = eul
        key_cam(c, f, pos, eul)
        fl = IMG_C.lerp(PH_C + Vector((0.01, 0.015, 0)), smooth(sp))
        # v13: late rack from the print toward the loupe (centre of the work) - hands the eye to 5B's run
        foc.location = fl.lerp(LOUPE_C + Vector((0.0, 0.0, 0.012)), 0.75 * smooth((f - 30) / 10.0))
        foc.keyframe_insert('location', frame=f)
        # T4: print reads like the source image through f10, lit print by f13 (v13: was f9-15 -> lamp glint in the
        # coat on the third cut frame + white smear)
        SHOT_STATE.setdefault('photo_boost', []).append((f, 1.0 - smooth((f - 10) / 3.0)))
        c.data.dof.aperture_fstop = 5.6 if f <= fh else 3.2
        c.data.dof.keyframe_insert('aperture_fstop', frame=f)
    lin_keys(c)
    return c

# ----------------------------------------------------------------------------- 5B: low FPV run
def setup_5B():
    c = cam_obj('Cam5B', 15.0, 5.0, sensor=8.0)     # small-sensor FPV: deeper, controllable macro DOF
    frames = [f for f, p in B_PTS]
    P = [Vector(p) for f, p in B_PTS]
    def pos_at(f):
        # piecewise param from frame
        for k in range(len(frames) - 1):
            if frames[k] <= f <= frames[k + 1]:
                return catmull(P, k + (f - frames[k]) / (frames[k + 1] - frames[k]))
        return P[-1]
    prev = None
    vel_prev = None
    for f in range(1, 85):
        p = pos_at(f)
        ahead = pos_at(min(84.0, f + 3)) if f < 82 else p + (P[-1] - P[-2]).normalized() * 0.01
        fwd = (ahead - p)
        if fwd.length < 1e-6:
            fwd = Vector((0.85, 0.5, 0))
        fwd.normalize()
        # gaze slightly down + toward the watch near the end
        gaze = p + fwd * 0.05 + Vector((0, 0, -0.012))
        # approaching the loupe: tip the nose up so the lens (and what it refracts) rides across the top of frame
        lw = smooth((f - 46) / 8.0) * (1 - smooth((f - 58) / 6.0))
        gaze = gaze.lerp(LOUPE_C + Vector((0, 0, 0.046)), 0.55 * lw)
        wt = smooth((f - 60) / 10.0) * (1 - smooth((f - 72) / 4.0))
        gaze = gaze.lerp(W + Vector((0, 0, 0.006)), wt * 0.75)
        # v13: whip up over the lid at the end (the cut at f78 lands mid-motion, no static low watch frame)
        gaze = gaze.lerp(W + Vector((0.045, 0.010, 0.022)), smooth((f - 72) / 9.0))      # across the rim onto the open lid
        # bank from lateral acceleration
        a = pos_at(min(84.0, f + 1)) - 2 * p + pos_at(max(1.0, f - 1))
        lat = a.dot(Vector((-fwd.y, fwd.x, 0)))
        roll = max(-0.38, min(0.38, -lat * 420.0))
        eul = look_rot(p, gaze, Vector((0, 0, 1)), roll, prev)
        prev = eul
        key_cam(c, f, p, eul)
        # rack focus along the run: lines ahead -> pencil tips beside -> loupe frame -> the watch
        fd = 0.04
        fd += (0.028 - fd) * smooth((f - 22) / 8.0)
        # v13: f44-58 lands on the loupe's front base bar (v12's 5 cm landed on nothing at f48)
        fd += (max(0.02, (LOUPE_C - p).length - 0.022) - fd) * smooth((f - 42) / 6.0)
        fd += (max(0.025, (W - p).length - 0.02) - fd) * smooth((f - 60) / 8.0)
        c.data.dof.focus_distance = fd
        c.data.dof.keyframe_insert('focus_distance', frame=f)
    lin_keys(c)
    sc.frame_set(1)
    shake(c, amp=0.0003, rot_amp=0.006, scale=5.0, seed=3)
    return c

# ----------------------------------------------------------------------------- 5C: rise over watch -> dive into gears
C_SENS = 4.0          # small-sensor macro camera for the dive (see cam_obj)

def macro_fstop(c, s, blur=0.022, lo=0.6, hi=48.0):
    """f-number that gives a constant CoC (fraction of frame width) for objects at twice the focus distance."""
    fl = c.data.lens / 1000.0
    sw = c.data.sensor_width / 1000.0
    s = max(s, fl * 1.25)
    coc = fl * fl / (s - fl) * 0.5 / sw      # * 1/N
    return max(lo, min(hi, coc / blur))

def watch_local(v):
    return W + Matrix.Rotation(W_YAW, 3, 'Z') @ Vector(v)

def crystal_z(r):
    """Approximate inner surface height of the watch crystal (watch-local) at radius r."""
    return 0.0121 - 0.0022 * (min(r, 0.0222) / 0.0222) ** 2

def setup_5C():
    c = cam_obj('Cam5C', 26.0, 4.0, sensor=C_SENS)
    foc = empty('Focus5C', loc=W)
    c.data.dof.focus_object = foc
    # v13 T5: the end frame looks ALONG the centre wheel rim at the real centre-wheel / third-pinion engagement:
    # near teeth march toward the lens (out of focus), the pinion mesh is sharp mid-ground, third wheel + plate below
    mesh_pt = watch_local(_MF)
    # v13: starts front-RIGHT and higher (5B arrives low from the front-left and whips up over the lid)
    A = W + Vector((0.055, -0.070, 0.030))
    Bp = W + Vector((-0.030, -0.040, 0.075))
    Cp, Dp = END_CAM_LOCAL
    Cp, Dp = watch_local(Cp), watch_local(Dp)                 # 35-40 deg above the mesh, outside the centre-wheel rim
    up_end = Vector((0, 0, 1))
    SHOT_STATE['5C_end'] = (Cp, Dp)
    prev = None
    hid = None
    hid_hands = None
    crys = bpy.data.objects.get('PWCrystal')
    for f in range(1, 49):
        if f <= 14:
            u = smooth((f - 1) / 13.0)
            mid = W + Vector((0.015, -0.085, 0.075))
            pos = (1 - u) ** 2 * A + 2 * (1 - u) * u * mid + u ** 2 * Bp
            tgt = (W + Vector((0, 0, 0.008))).lerp(W + Vector((0.002, -0.003, 0.005)), u)
            up = Vector((0, 0, 1)).lerp(Vector((0.3, 0.8, 0)), u).normalized()
        elif f <= 38:
            u = (f - 14) / 24.0
            # v5: accelerate into the dive, brake hard onto the teeth (smootherstep skewed late) - the v4 curve
            # did 60 % of the distance in 5 frames = pure motion-blur mush mid-dive
            uu = u ** 1.25
            e = uu * uu * uu * (uu * (uu * 6 - 15) + 10)
            mid = Cp + Vector((0, 0, 0.016))
            pos = (1 - e) ** 2 * Bp + 2 * (1 - e) * e * mid + e ** 2 * Cp
            tgt = (W + Vector((0.002, -0.003, 0.005))).lerp(mesh_pt, smooth(u * 1.3))
            up = Vector((0.3, 0.8, 0)).normalized().lerp(up_end, smooth((u - 0.45) / 0.55)).normalized()
        else:
            u = (f - 38) / 10.0
            pos = Cp.lerp(Dp, u)
            tgt = mesh_pt
            up = up_end
        sdist = (tgt - pos).length
        eul = look_rot(pos, tgt, up, 0.0, prev)
        prev = eul
        key_cam(c, f, pos, eul)
        foc.location = tgt
        foc.keyframe_insert('location', frame=f)
        c.data.dof.aperture_fstop = macro_fstop(c, sdist, blur=0.02 if f < 23 else (0.011 if f < 35 else 0.03))
        c.data.dof.keyframe_insert('aperture_fstop', frame=f)
        # the camera passes through the crystal: drop it the moment the lens is within 2 mm of the glass
        loc_ = Matrix.Rotation(-W_YAW, 3, 'Z') @ (pos - W)
        if hid is None and loc_.z < crystal_z(loc_.xy.length) + 0.0025:
            hid = f
        if hid_hands is None and loc_.z < 0.0108:
            hid_hands = f
    SHOT_STATE['5C_crystal_hide'] = hid
    SHOT_STATE['5C_hands_hide'] = hid_hands
    lin_keys(c)
    for fc in fcurves(c.data):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    sc.frame_set(1)
    shake(c, amp=0.00012, rot_amp=0.003, scale=7.0, seed=9)
    return c

if arg('--probe'):
    # debug: what blocks the moon? cast from sample points toward the sun
    dg = bpy.context.evaluated_depsgraph_get()
    sun_dir = -(moon.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    print('[probe] moon light travel dir', -sun_dir, 'energy', moon.data.energy)
    for p in [(-0.25, 0.575, 0.30), (0.2, 0.575, 0.25), (0.0, 0.3, 0.001), (0.2, 0.45, 0.10), (-0.1, 0.1, 0.006), (0.0, -0.1, 0.004)]:
        hit, loc, nrm, idx, ob, mtx = sc.ray_cast(dg, Vector(p) + sun_dir * 0.002, sun_dir)
        print('[probe] from', p, '->', (ob.name if hit else 'SKY (lit)'), tuple(round(v, 3) for v in loc) if hit else '')
    sys.exit(0)

SETUP = {'5A': setup_5A, '5B': setup_5B, '5C': setup_5C}
cams = {}
for sid in SHOT_LIST:
    cams[sid] = SETUP[sid]()

# per-shot exposure: constant, or a list of (frame, EV) keys
# CLIENT RULE (never too bright): exposure_check.py medians 0.50 (5B) / 0.66 (5C f16) -> pulled down
# v13: 5A whip f10-14 was a white wash (p50 0.66) -> pulled down hard on the blur frames; 5B's last frames darker to
# meet 5C; 5C ends at -0.7 to sit with 6A's dark, cool opening (was -0.15: YAVG 59 vs 30)
EXPOSURE = {'5A': [(1, 0.0), (9, 0.0), (10, -0.8), (12, -1.2), (14, -1.0), (18, -0.4), (24, -0.15), (52, -0.15)],
            '5B': [(1, -0.3), (66, -0.3), (76, -0.45), (84, -0.45)],
            '5C': [(1, -1.15), (22, -1.1), (26, -1.4), (30, -1.6), (33, -1.3), (36, -1.15), (48, -1.6)]}   # v23/24: f27-29 whoosh was p50 0.45-0.52

# v13 T4: frames 1-9 of 5A show 4F's display-referred frame. Running it through AgX + the compositor shoulder a
# second time crushed shadows and rolled off whites (YLOW 43 vs 54, YHIGH 183 vs 192) -> Standard view, no look,
# compositor bypassed (raw render layer) on f<=9; AgX + shoulder/bloom from f10, inside the whip blur.
_ct = sc.compositing_node_group
T4_MIX = None
try:
    _out = [n for n in _ct.nodes if n.type == 'GROUP_OUTPUT'][0]
    _rl = [n for n in _ct.nodes if n.type == 'R_LAYERS'][0]
    _cur = _out.inputs[0].links[0].from_socket
    T4_MIX = _ct.nodes.new('ShaderNodeMix'); T4_MIX.data_type = 'RGBA'; T4_MIX.name = 'T4Bypass'
    T4_MIX.inputs['Factor'].default_value = 0.0
    _ct.links.new(_cur, T4_MIX.inputs[6]); _ct.links.new(_rl.outputs['Image'], T4_MIX.inputs[7])
    _ct.links.new(T4_MIX.outputs[2], _out.inputs[0])
except Exception as e:
    print('[act5] T4 bypass node failed', e)
FRAME_RULES = {'sid': None}

def _act5_frame(scene, *_a):
    sid = FRAME_RULES['sid']
    f = scene.frame_current
    vs = scene.view_settings
    t4 = (sid == '5A' and f <= 9)
    want = 'Standard' if t4 else 'AgX'
    if vs.view_transform != want:
        vs.view_transform = want
        vs.look = 'None' if t4 else 'AgX - Medium High Contrast'
    if T4_MIX is not None:
        T4_MIX.inputs['Factor'].default_value = 1.0 if t4 else 0.0
    ee_ = scene.eevee
    whip = (sid == '5A' and 9 <= f <= 18)
    ee_.motion_blur_steps = 4 if whip else 1
    # final-quality default (48 spp) gets 64 spp on the whip frames (smoother accumulated blur); explicit test
    # sample counts (--samples 8/16/...) are left alone
    if ee_.taa_render_samples in (48, 64):
        ee_.taa_render_samples = 64 if whip else 48
    # 5C inside the movement: fine froxels for the mm-scale haze slab (3 mm..3 m slices were far too coarse)
    vs0, ve0 = (0.0004, 0.12) if (sid == '5C' and f >= 30) else (0.003, 3.0)
    if abs(ee_.volumetric_start - vs0) > 1e-7:
        ee_.volumetric_start, ee_.volumetric_end = vs0, ve0
bpy.app.handlers.frame_change_pre.append(_act5_frame)

def apply_shot_state(sid):
    """Scene-level animation that belongs to one shot only (exposure ramp, crystal drop-out)."""
    FRAME_RULES['sid'] = sid
    if sc.animation_data:
        sc.animation_data_clear()
    sc.render.motion_blur_shutter = {'5A': 0.5, '5B': 0.25, '5C': 0.3}[sid]
    # lamp: no specular on the T4/whip-start frames (the coat mirrored it as a 'sun' in 4F's sky); no volume
    # in-scatter inside the watch for 5C (warm milky veil bottom-left of the T5 frame)
    ld = lamp_spot.data
    ld.animation_data_clear()
    ld.specular_factor = 1.0
    ld.volume_factor = 0.0 if sid == '5C' else 1.1
    ld.energy = 46.0
    if sid == '5A':
        for f, v in ((1, 0.0), (11, 0.0), (16, 1.0)):
            ld.specular_factor = v
            ld.keyframe_insert('specular_factor', frame=f)
    if sid == '5C':
        # T5: inside the movement the practicals carry the frame; the overhead lamp eases off so the wheel faces sit
        # darker and the cool backlit haze reads (6A opens dark + blue with warm rims)
        for f, v in ((1, 46.0), (32, 46.0), (40, 12.0)):
            ld.energy = v
            ld.keyframe_insert('energy', frame=f)
    wd = wcool.data
    wd.animation_data_clear()
    wd.energy = 0.0
    wwd = wwarm.data
    wwd.animation_data_clear()
    wwd.energy = 0.0
    # world haze: none on the T4 handoff frames (froxel grid + lamp in-scatter veiled the photo), fades in with the whip
    wnt = world.node_tree
    wnt.animation_data_clear()
    FOG.inputs['Density'].default_value = FOG_D
    if sid == '5A':
        for f, v in ((1, 0.0), (9, 0.0), (17, FOG_D)):
            FOG.inputs['Density'].default_value = v
            FOG.inputs['Density'].keyframe_insert('default_value', frame=f)
    pnt = photo.active_material.node_tree
    pnt.animation_data_clear()
    photo_boost.outputs[0].default_value = 0.0
    if sid == '5A':
        for f, v in SHOT_STATE.get('photo_boost', []):
            photo_boost.outputs[0].default_value = v
            photo_boost.outputs[0].keyframe_insert('default_value', frame=f)
    ex = EXPOSURE[sid]
    if isinstance(ex, list):
        for f, v in ex:
            sc.view_settings.exposure = v
            sc.keyframe_insert('view_settings.exposure', frame=f)
    else:
        sc.view_settings.exposure = ex
    crys = bpy.data.objects.get('PWCrystal')
    hid = SHOT_STATE.get('5C_crystal_hide') if sid == '5C' else None
    if crys is not None:
        crys.animation_data_clear()
        crys.hide_render = False
        if hid:
            crys.keyframe_insert('hide_render', frame=max(1, hid - 1))
            crys.hide_render = True
            crys.keyframe_insert('hide_render', frame=hid)
            print('[act5] 5C crystal hidden from frame', hid)
    for o in (haze, specks):        # inner haze appears as the crystal goes
        o.animation_data_clear()
        o.hide_render = True
        if hid:
            o.keyframe_insert('hide_render', frame=max(1, hid - 1))
            o.hide_render = False
            o.keyframe_insert('hide_render', frame=hid)
    # v13: hands, cap + centre arbor drop out once the lens is below the dial (they drew a vertical streak through T5)
    hh = SHOT_STATE.get('5C_hands_hide') if sid == '5C' else None
    for nm_ in ('PWHourHand', 'PWMinHand', 'PWHandCap', 'PWCentreArbor'):
        o = bpy.data.objects.get(nm_)
        if o is None:
            continue
        o.animation_data_clear()
        o.hide_render = False
        if hh:
            o.keyframe_insert('hide_render', frame=max(1, hh - 1))
            o.hide_render = True
            o.keyframe_insert('hide_render', frame=hh)
    if sid == '5C' and hid:
        for (light_d, e1) in ((wd, 0.085), (wwd, 0.032)):
            for f, v in ((1, 0.0), (hid, 0.0), (hid + 6, e1)):
                light_d.energy = v
                light_d.keyframe_insert('energy', frame=f)
    if sid == '5C':
        print('[act5] 5C crystal hide f%s, hands hide f%s' % (hid, hh))
    if arg('--nocrystal') and crys is not None:      # debug: what is the light polygon in the crystal at 5C f10-22?
        crys.animation_data_clear(); crys.hide_render = True

if arg('--probe2'):
    # debug: which objects sit in the lower-right of 5B f8..f16 (the big blurred disc)?
    from bpy_extras.object_utils import world_to_camera_view
    cb = cams.get('5B')
    for fr in (8, 12, 16):
        sc.frame_set(fr)
        dg = bpy.context.evaluated_depsgraph_get()
        mw = cb.matrix_world
        fr_pts = cb.data.view_frame(scene=sc)
        hits = {}
        for u in (0.45, 0.55, 0.65, 0.75, 0.85):
            for v in (0.08, 0.18, 0.28, 0.38):
                # interpolate the camera frame corners (tr, br, bl, tl)
                tr, br, bl, tl = fr_pts
                p = bl.lerp(br, u).lerp(tl.lerp(tr, u), v)
                d = (mw.to_3x3() @ p).normalized()
                hit, loc, nrm, idx, ob, mtx = sc.ray_cast(dg, mw.translation, d)
                if hit:
                    hits.setdefault(ob.name, []).append(round((loc - mw.translation).length, 4))
        print('[probe2] f%d cam %s' % (fr, tuple(round(c, 3) for c in mw.translation)), {k: min(v) for k, v in hits.items()})
    if not arg('--stills'):
        sys.exit(0)

for sid in SHOT_LIST:
    shot = SHOTS[sid]
    sc.camera = cams[sid]
    sc.frame_start, sc.frame_end = 1, shot['render_frames']
    apply_shot_state(sid)
    print(f"[act5] shot {sid}: frames 1..{shot['render_frames']} cut {shot['cut_in_local']}..{shot['cut_out_local']}  (t={time.time() - T0:.1f}s)")
    st = arg('--st' + sid, None)
    if st and st is not True and '--stills' in sys.argv:
        # per-shot still frames in a multi-shot build: --stills 8 --st5A 8,22,40 --st5B 12,40
        sys.argv[sys.argv.index('--stills') + 1] = str(st)
    if '--outdir' in sys.argv:      # make a relative --outdir absolute (relative to film/)
        k = sys.argv.index('--outdir') + 1
        if k < len(sys.argv) and not os.path.isabs(sys.argv[k]):
            sys.argv[k] = os.path.join(FILM, sys.argv[k])
    if arg('--anim') and len(SHOT_LIST) > 1 and '--outdir' in sys.argv:
        # several shots in one build: give each its own motion-test folder
        k = sys.argv.index('--outdir') + 1
        sys.argv[k] = os.path.join(FILM, 'tests', f"{sid}_motion{arg('--tag', '')}")
    finish(sid)
