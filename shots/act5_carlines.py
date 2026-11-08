"""Act V helper: render line art of the hero car (lib/car.py) for the desk blueprints.

  rb.py shots/act5_carlines.py
Renders camera-space normals (material override) from side / plan / front / 3-4 views,
edge-detects them with numpy and composes film/tex/act5_bp_car.png (blueprint) and
film/tex/act5_sk_car.png (graphite sketch). Run once; the act5 scene just loads the PNGs.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import numpy as np
import desk_tex as DT
import car as CAR

TMP = os.path.join(FILM, 'tex', '_carlines')
os.makedirs(TMP, exist_ok=True)
sc = reset()
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 8
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.render.image_settings.color_depth = '16'
world_color((0, 0, 0), 0.0)

c = CAR.build_car(name='Car')
# hide anything that is not a mesh or is an emitter-only helper
mins = Vector((1e9, 1e9, 1e9)); maxs = Vector((-1e9, -1e9, -1e9))
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.hide_render:
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
print('[carlines] bbox', mins, maxs)
L, Wd, H = maxs.y - mins.y, maxs.x - mins.x, maxs.z - mins.z

# normal material override
b = NB('NormalOverride')
geo = b.n('ShaderNodeNewGeometry')
vt = b.n('ShaderNodeVectorTransform', vector_type='NORMAL', convert_from='WORLD', convert_to='CAMERA')
b.link(geo.outputs['Normal'], vt.inputs['Vector'])
sc_ = b.n('ShaderNodeVectorMath', operation='MULTIPLY_ADD')
b.link(vt.outputs['Vector'], sc_.inputs[0]); sc_.inputs[1].default_value = (0.5, 0.5, 0.5); sc_.inputs[2].default_value = (0.5, 0.5, 0.5)
em = b.n('ShaderNodeEmission')
b.link(sc_.outputs['Vector'], em.inputs['Color'])
b.link(em.outputs[0], b.out.inputs['Surface'])
bpy.context.view_layer.material_override = b.mat

cam = camera('LineCam', (0, 0, 10), lens=50, clip=(0.05, 100))

PPM = 480.0   # px per metre on the final sheet
SS = 2        # supersample


def render_view(name, loc, rot, w_m, h_m, ortho=True, lens=50):
    cam.location = loc
    cam.rotation_euler = rot
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    cam.data.lens = lens
    rx, ry = int(w_m * PPM * SS), int(h_m * PPM * SS)
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100
    cam.data.sensor_fit = 'AUTO'
    cam.data.ortho_scale = max(w_m, h_m)
    path = os.path.join(TMP, name + '.png')
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    a = np.array(img.pixels[:], np.float32).reshape(ry, rx, 4)[::-1]
    bpy.data.images.remove(img)
    return a


def edges(a, crease=0.10):
    n = a[..., :3]; al = a[..., 3]
    gx = np.abs(np.diff(n, axis=1, append=n[:, -1:])).max(-1)
    gy = np.abs(np.diff(n, axis=0, append=n[-1:])).max(-1)
    g = np.maximum(gx, gy) * (al > 0.5)
    ag = np.maximum(np.abs(np.diff(al, axis=1, append=al[:, -1:])), np.abs(np.diff(al, axis=0, append=al[-1:])))
    e = np.clip((g - crease) / 0.15, 0, 1)
    e = np.maximum(e, np.clip(ag * 2.0, 0, 1))
    # thicken by 1px then downsample
    e = np.maximum.reduce([e, np.roll(e, 1, 0), np.roll(e, 1, 1)])
    h, w = e.shape
    e = e[:h // SS * SS, :w // SS * SS].reshape(h // SS, SS, w // SS, SS).mean((1, 3))
    return np.clip(e * 1.6, 0, 1)


cz = (mins.z + maxs.z) / 2
side = edges(render_view('side', (12, (mins.y + maxs.y) / 2, cz), (math.pi / 2, 0, math.pi / 2), L * 1.04, H * 1.1))
plan = edges(render_view('plan', (0, (mins.y + maxs.y) / 2, 12), (0, 0, math.pi / 2), L * 1.04, Wd * 1.08))
front = edges(render_view('front', (0, 12, cz), (math.pi / 2, 0, math.pi), Wd * 1.08, H * 1.1))
tq = render_view('tq', (7.2, 7.8, 3.6), (math.radians(70), 0, math.radians(137)), 4.6, 2.6, ortho=False, lens=50)
tq_e = edges(tq, 0.08)


def paste(cv, e, x, y, val=1.0):
    h, w = e.shape
    x, y = int(x), int(y)
    sub = cv.ink[y:y + h, x:x + w]
    np.maximum(sub, e[:sub.shape[0], :sub.shape[1]] * val, out=sub)

# ---------------------------------------------------------------- blueprint sheet
W_, H_ = 3508, 2480
cv = DT.Canvas(W_, H_)
DT.sheet_border(cv, 70)
sx, sy = 180, 300
paste(cv, side, sx, sy)
px, py = 180, 300 + side.shape[0] + 260
paste(cv, plan, px, py)
fx, fy = 180 + side.shape[1] + 200, 300
paste(cv, front, fx, fy)
gy_side = sy + side.shape[0] - (H * 0.05) * PPM          # ground line (bbox bottom)
cv.poly([(110, gy_side), (fx + front.shape[1] + 60, gy_side)], 1.6, 0.8, dash=(40, 10, 6, 10))
x0 = sx + L * 0.02 * PPM
cv.dim((x0, gy_side), (x0 + L * PPM, gy_side), 110, f"{L * 1000:.0f}")
wb0 = x0 + (CAR.YR - mins.y) * PPM
cv.dim((wb0, gy_side - CAR.WR * PPM), (wb0 + CAR.WB * PPM, gy_side - CAR.WR * PPM), 230, f"{CAR.WB * 1000:.0f}")
for xw in (wb0, wb0 + CAR.WB * PPM):
    DT.centre_mark(cv, (xw, gy_side - CAR.WR * PPM), CAR.WR * PPM * 1.4, 0.8)
cv.dim((fx - 40, gy_side), (fx - 40, gy_side - H * PPM), 1, f"{H * 1000:.0f}")
cv.dim((fx + front.shape[1] * 0.04, gy_side + 20), (fx + front.shape[1] * 0.96, gy_side + 20), 90, f"{Wd * 1000:.0f}")
pcy = py + plan.shape[0] / 2
cv.poly([(110, pcy), (px + plan.shape[1] + 40, pcy)], 1.3, 0.8, dash=(30, 8, 4, 8))
cv.text("ELEVATION", sx + side.shape[1] / 2, sy - 50, 34, 3.0, 1.0, align='center')
cv.text("PLAN", px + plan.shape[1] / 2, py - 40, 34, 3.0, 1.0, align='center')
cv.text("FRONT", fx + front.shape[1] / 2, fy - 50, 34, 3.0, 1.0, align='center')
DT.title_block(cv, W_ - 70 - 1050, H_ - 70 - 330, 1050, 330,
               [("TITLE", "ESCAPEMENT"), ("DRAWING", "CHASSIS 01 - GENERAL ARRANGEMENT"),
                ("SCALE  1:10     SHEET 1/7", "DWG C-0101   REV F")], 1.0, 44)
notes = ["NOTES:", "1. CARBON TUB - SEE C-0140", "2. CENTRE-LOCK 6-SPOKE FORGED", "3. PANEL GAP 3.5 +-0.3"]
for i, s in enumerate(notes):
    cv.text(s, W_ - 70 - 1050, H_ - 70 - 330 - 220 + i * 46, 22, 2.0, 0.95)
fw_c = (wb0 + CAR.WB * PPM, gy_side - CAR.WR * PPM)
DT.markup(cv, [('circle', fw_c, CAR.WR * PPM * 1.45), ('text', "-5 MM RIDE", fw_c[0] - 120, fw_c[1] - CAR.WR * PPM * 1.7, 46),
               ('arrow', (fw_c[0] + 260, fw_c[1] - 300), (fw_c[0] + 60, fw_c[1] - 120))], seed=5)
DT.save_png(os.path.join(FILM, 'tex', 'act5_bp_car.png'), DT.finish_blueprint(cv, 31))

# ---------------------------------------------------------------- graphite 3/4 sketch
W2, H2 = 3508, 2480
cv2 = DT.Canvas(W2, H2)
h, w = tq_e.shape
ox, oy = (W2 - w) // 2, 380
for k, (dx, dy, v) in enumerate(((0, 0, 0.55), (2, 1, 0.3), (-1, 2, 0.22))):
    sub = cv2.ink[oy + dy:oy + dy + h, ox + dx:ox + dx + w]
    sub[...] = 1 - (1 - sub) * (1 - tq_e[:sub.shape[0], :sub.shape[1]] * v)
# construction lines + hatching + notes
cv2.poly([(150, oy + h * 0.86), (W2 - 150, oy + h * 0.80)], 1.4, 0.3, mode='screen')
cv2.poly([(300, oy + h * 0.95), (W2 * 0.55, oy + h * 0.30), (W2 - 250, oy + h * 0.92)], 1.2, 0.18, mode='screen')
for i in range(70):
    x = ox + w * 0.15 + i * 26
    cv2.seg((x, oy + h * 0.9), (x + 44, oy + h * 0.93), 1.3, 0.22, mode='screen')
cv2.text("PROPORTION STUDY 03", 160, 240, 70, 3.6, 0.65, mode='screen', jitter=1.2)
cv2.text("LOW - WIDE - CAB FWD", 160, 330, 38, 2.4, 0.5, mode='screen', jitter=0.9)
DT.draw_wheel(cv2, (3050, 2050), 230, 0.45, 2.4, mode='screen')
cv2.text("6-SPOKE - CENTRE LOCK", 2780, 2340, 30, 2.2, 0.5, mode='screen', jitter=0.8)
img = DT.finish_graphite(cv2, 51, tint=(0.90, 0.88, 0.83))
img = DT.coffee_ring(img, (W2 * 0.18, H2 * 0.72), W2 * 0.07, 0.5)
DT.save_png(os.path.join(FILM, 'tex', 'act5_sk_car.png'), img)
print('[carlines] done')
