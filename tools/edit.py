"""Conform + finishing engine for ESCAPEMENT.

Reads film/edit/edl.json, pulls 16-bit PNG frames from film/renders/<shot>/, applies retiming,
transitions, per-act grade, halation, grain, vignette, chroma aberration, letterbox, and
encodes H.264 (BT.709) via ffmpeg. Run with Blender's bundled python (has numpy):

  py film/tools/edit.py [edl.json] [--out film/out/escapement.mp4] [--audio mix.wav]
                        [--range a b] [--preview] [--stills 10,200]
"""
import json, os, sys, subprocess, math
import numpy as np

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1920, 1080


# ----------------------------------------------------------------------------- io

class ShotCache:
    """Decodes a shot's PNG frames on demand (whole shot at once via one ffmpeg call)."""

    def __init__(self, scale=1.0):
        self.cache = {}
        self.order = []
        self.scale = scale

    def _load(self, shot):
        d = os.path.join(FILM, 'renders', shot)
        files = sorted(f for f in os.listdir(d) if f.lower().endswith(('.png', '.jpg')))
        if not files:
            raise FileNotFoundError(d)
        first = int(os.path.splitext(files[0])[0])
        ext = os.path.splitext(files[0])[1]
        w, h = int(W * self.scale), int(H * self.scale)
        cmd = ['ffmpeg', '-v', 'error', '-start_number', str(first), '-i', os.path.join(d, '%04d' + ext),
               '-vf', f'scale={w}:{h}:flags=lanczos', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-']
        raw = subprocess.run(cmd, capture_output=True).stdout
        n = len(raw) // (w * h * 6)
        arr = np.frombuffer(raw, dtype=np.uint16)[: n * w * h * 3].reshape(n, h, w, 3)
        frames = {first + i: arr[i] for i in range(n)}
        return frames

    def get(self, shot, f):
        if shot not in self.cache:
            self.cache[shot] = self._load(shot)
            self.order.append(shot)
            while len(self.order) > 3:
                old = self.order.pop(0)
                self.cache.pop(old, None)
        fr = self.cache[shot]
        keys = sorted(fr)
        f = int(round(f))
        f = min(max(f, keys[0]), keys[-1])
        return fr[f].astype(np.float32) / 65535.0


# ----------------------------------------------------------------------------- fx primitives

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def ease(t, kind='inout'):
    t = min(max(t, 0.0), 1.0)
    if kind == 'in':
        return t ** 3
    if kind == 'out':
        return 1 - (1 - t) ** 3
    return t * t * (3 - 2 * t)


def luma(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def box_blur(img, r, axis):
    if r < 1:
        return img
    c = np.cumsum(img, axis=axis, dtype=np.float32)
    pad = [(0, 0)] * img.ndim
    pad[axis] = (r + 1, r)
    c = np.pad(c, pad, mode='edge')
    sl_hi = [slice(None)] * img.ndim
    sl_lo = [slice(None)] * img.ndim
    n = img.shape[axis]
    sl_hi[axis] = slice(2 * r + 1, 2 * r + 1 + n)
    sl_lo[axis] = slice(0, n)
    return (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1)


def blur(img, r, passes=2):
    for _ in range(passes):
        img = box_blur(box_blur(img, r, 0), r, 1)
    return img


def down(img, k):
    h, w = img.shape[0] // k * k, img.shape[1] // k * k
    return img[:h, :w].reshape(h // k, k, w // k, k, -1).mean(axis=(1, 3))


def up(img, k, shape):
    u = np.repeat(np.repeat(img, k, axis=0), k, axis=1)
    out = np.zeros(shape, np.float32)
    out[:u.shape[0], :u.shape[1]] = u[:shape[0], :shape[1]]
    if u.shape[0] < shape[0]:
        out[u.shape[0]:] = out[u.shape[0] - 1]
    if u.shape[1] < shape[1]:
        out[:, u.shape[1]:] = out[:, u.shape[1] - 1:u.shape[1]]
    return out


def glow(img, threshold=0.75, radius=24, strength=0.25, tint=(1.0, 0.45, 0.25)):
    """Halation/bloom: blurred highlights added back, tinted (film halation is red-orange)."""
    k = 4
    hl = np.clip(img - threshold, 0, None) / (1 - threshold)
    small = down(hl, k)
    small = blur(small, max(1, radius // k), passes=3)
    g = up(small, k, img.shape) * np.array(tint, np.float32)
    return img + g * strength


_grid_cache = {}


def _grid(h, w):
    key = (h, w)
    if key not in _grid_cache:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _grid_cache[key] = (yy, xx)
    return _grid_cache[key]


def scale_about_center(img, s, cx=None, cy=None):
    h, w = img.shape[:2]
    yy, xx = _grid(h, w)
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    sx = np.clip(((xx - cx) / s + cx).astype(np.int32), 0, w - 1)
    sy = np.clip(((yy - cy) / s + cy).astype(np.int32), 0, h - 1)
    return img[sy, sx]


def chroma_ab(img, amount=0.0015):
    if amount <= 0:
        return img
    out = img.copy()
    out[..., 0] = scale_about_center(img[..., 0:1], 1 + amount)[..., 0]
    out[..., 2] = scale_about_center(img[..., 2:3], 1 - amount)[..., 0]
    return out


def zoom_blur(img, amount=0.08, samples=8, cx=None, cy=None):
    acc = np.zeros_like(img)
    for i in range(samples):
        s = 1 + amount * i / max(1, samples - 1)
        acc += scale_about_center(img, s, cx, cy)
    return acc / samples


def whip(img, px, axis=1):
    r = int(abs(px) / 2)
    return box_blur(img, r, axis) if r >= 1 else img


_vig = {}


def vignette(img, strength=0.35, softness=0.8):
    h, w = img.shape[:2]
    key = (h, w, strength, softness)
    if key not in _vig:
        yy, xx = _grid(h, w)
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
        _vig[key] = (1 - strength * smoothstep(1 - softness, 1.05, d))[..., None].astype(np.float32)
    return img * _vig[key]


def grain(img, amount=0.035, seed=0, size=1.3):
    h, w = img.shape[:2]
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((h, w, 1)).astype(np.float32)
    if size > 1.0:
        n = box_blur(box_blur(n, 1, 0), 1, 1) * 1.8
    lum = luma(img)[..., None]
    weight = 0.35 + 0.65 * (4 * lum * (1 - lum))  # strongest in mid-tones
    colored = n * np.array([1.0, 0.92, 1.08], np.float32)
    return img + colored * amount * weight


def letterbox(img, ratio):
    if not ratio or ratio <= 16 / 9 + 1e-3:
        return img
    h, w = img.shape[:2]
    bar = int(round((h - w / ratio) / 2))
    if bar > 0:
        img = img.copy()
        img[:bar] = 0
        img[h - bar:] = 0
    return img


def light_leak(img, t, strength=0.5, color=(1.0, 0.35, 0.12), x=0.85, seed=0):
    """Warm vertical leak drifting across the frame (like the car film's red flares)."""
    h, w = img.shape[:2]
    yy, xx = _grid(h, w)
    cx = (x + 0.15 * math.sin(t * 2.3 + seed)) * w
    band = np.exp(-((xx - cx) / (w * 0.06)) ** 2) * (0.6 + 0.4 * np.exp(-((yy - h * 0.3) / (h * 0.7)) ** 2))
    leak = band[..., None] * np.array(color, np.float32) * strength
    return 1 - (1 - np.clip(img, 0, 1)) * (1 - np.clip(leak, 0, 1))


# ----------------------------------------------------------------------------- grade

GRADES = {
    # lift/gamma/gain per channel (display referred), split-tone, saturation, contrast
    'neutral': dict(lift=(0, 0, 0), gamma=(1, 1, 1), gain=(1, 1, 1), sh=(0, 0, 0), hi=(0, 0, 0), sat=1.0, con=0.0),
    'act1': dict(lift=(0.0, 0.004, 0.012), gamma=(1.0, 1.0, 1.02), gain=(1.04, 1.0, 0.95), sh=(-0.01, 0.015, 0.03), hi=(0.03, 0.01, -0.03), sat=1.08, con=0.12),
    'act2': dict(lift=(0.0, 0.006, 0.012), gamma=(1.0, 1.0, 1.02), gain=(1.0, 1.0, 1.0), sh=(-0.015, 0.012, 0.025), hi=(0.015, 0.005, -0.01), sat=1.05, con=0.14),
    'act3': dict(lift=(0.0, 0.012, 0.014), gamma=(1.0, 1.02, 1.0), gain=(1.06, 0.98, 0.96), sh=(-0.02, 0.025, 0.03), hi=(0.04, -0.005, -0.02), sat=1.06, con=0.12),
    'act4': dict(lift=(0.0, 0.003, 0.01), gamma=(1.0, 1.0, 1.0), gain=(1.03, 1.0, 0.98), sh=(-0.01, 0.01, 0.03), hi=(0.03, 0.015, -0.015), sat=1.12, con=0.08),
    # 4B cloud punch-through: the new cumulus deck renders bright and flat -> darker, punchier, cooler shadows
    'act4b': dict(lift=(-0.03, -0.025, -0.01), gamma=(1.0, 1.0, 1.03), gain=(0.86, 0.88, 0.92), sh=(-0.01, 0.0, 0.035), hi=(0.03, 0.015, -0.01), sat=1.2, con=0.3),
    'act5': dict(lift=(0.0, 0.004, 0.012), gamma=(1.0, 1.0, 1.0), gain=(1.04, 1.0, 0.96), sh=(-0.01, 0.01, 0.03), hi=(0.03, 0.01, -0.02), sat=1.05, con=0.12),
    'act6': dict(lift=(0.0, 0.0, 0.005), gamma=(1.0, 1.0, 1.0), gain=(1.04, 1.0, 0.95), sh=(0, 0.005, 0.015), hi=(0.03, 0.01, -0.03), sat=1.05, con=0.1),
}


def grade(img, g):
    lift = np.array(g['lift'], np.float32)
    gain = np.array(g['gain'], np.float32)
    gam = np.array(g['gamma'], np.float32)
    x = np.clip(img, 0, None)
    x = x * gain + lift * (1 - x)
    x = np.power(np.clip(x, 0, None), 1.0 / gam)
    if g.get('con'):
        c = g['con']
        x = np.clip(x, 0, 1)
        s = x * x * (3 - 2 * x)
        x = x + (s - x) * c
    lum = luma(x)[..., None]
    x = x + np.array(g['sh'], np.float32) * (1 - smoothstep(0.0, 0.5, lum)) + np.array(g['hi'], np.float32) * smoothstep(0.45, 1.0, lum)
    if g.get('sat', 1.0) != 1.0:
        lum = luma(x)[..., None]
        x = lum + (x - lum) * g['sat']
    return x


def blend_grades(a, b, t):
    out = {}
    for k in a:
        if isinstance(a[k], tuple):
            out[k] = tuple(a[k][i] * (1 - t) + b[k][i] * t for i in range(3))
        else:
            out[k] = a[k] * (1 - t) + b[k] * t
    return out


# ----------------------------------------------------------------------------- timeline

def build_timeline(edl):
    """Expands clips into per-output-frame records: (clip_idx, src_frame_float)."""
    tl = []
    for ci, c in enumerate(edl['clips']):
        n = c['out'] - c['in'] + 1 if 'len' not in c else c['len']
        remap = c.get('remap')  # [[out_local(0..n-1), src_frame], ...]
        for i in range(n):
            if remap:
                xs = [p[0] for p in remap]
                ys = [p[1] for p in remap]
                src = float(np.interp(i, xs, ys))
            else:
                src = c['in'] + i * c.get('speed', 1.0)
            tl.append((ci, src, i, n))
    return tl


def render_frame(edl, tl, k, cache, scale=1.0):
    ci, src, i, n = tl[k]
    clips = edl['clips']
    c = clips[ci]
    img = cache.get(c['shot'], src)
    # transitions overlapping into neighbours
    tr_in = c.get('tr_in')    # transition from previous clip into this one
    tr_out = None
    if ci + 1 < len(clips):
        tr_out = clips[ci + 1].get('tr_in')
    if tr_in and tr_in['type'] in ('dissolve', 'luma', 'diag', 'whiteout') and i < tr_in['frames'] // 2:
        p = clips[ci - 1]
        half = tr_in['frames'] // 2
        other = cache.get(p['shot'], p['out'] + 1 + i)  # previous clip continues into its tail handle
        t = (half + i + 0.5) / tr_in['frames']
        img = mix_transition(other, img, t, tr_in, k)
    elif tr_out and tr_out['type'] in ('dissolve', 'luma', 'diag', 'whiteout') and i >= n - tr_out['frames'] // 2:
        nx = clips[ci + 1]
        half = tr_out['frames'] // 2
        j = i - (n - half)
        other = cache.get(nx['shot'], nx['in'] - half + j)  # next clip's head handle
        t = (j + 0.5) / tr_out['frames']
        img = mix_transition(img, other, t, tr_out, k)
    # per-frame fx windows on this clip
    for fx in c.get('fx', []):
        a, b = fx.get('from', 0), fx.get('to', n - 1)
        if not (a <= i <= b):
            continue
        u = (i - a) / max(1, b - a)
        env = fx.get('env', 'tri')
        e = {'tri': 1 - abs(2 * u - 1), 'up': u, 'down': 1 - u, 'flat': 1.0}[env]
        e = ease(e, 'inout') if fx.get('smooth', True) else e
        kind = fx['type']
        if kind == 'flash':
            col = np.array(fx.get('color', (1, 1, 1)), np.float32)
            img = img + col * fx.get('amount', 1.0) * e
        elif kind == 'zoom':
            img = zoom_blur(img, fx.get('amount', 0.1) * e, samples=fx.get('samples', 8))
        elif kind == 'whip':
            img = whip(img, fx.get('px', 120) * e * scale, axis=fx.get('axis', 1))
        elif kind == 'leak':
            img = light_leak(img, k / 24.0, fx.get('amount', 0.5) * e, tuple(fx.get('color', (1, 0.35, 0.12))), fx.get('x', 0.85), fx.get('seed', 0))
        elif kind == 'exposure':
            img = img * (2 ** (fx.get('stops', 1.0) * e))
        elif kind == 'black':
            img = img * (1 - e * fx.get('amount', 1.0))
        elif kind == 'shake':
            # camera bump: crop in slightly and offset the crop centre (no wrapped edges)
            rng = np.random.default_rng(k * 7 + 3)
            px = fx.get('px', 12) * e * scale
            dx, dy = (rng.random(2) - 0.5) * 2 * px
            h_, w_ = img.shape[:2]
            s = 1.0 + 2.2 * px / min(w_, h_) + 0.004
            img = scale_about_center(img, s, w_ / 2 + dx, h_ / 2 + dy)
        elif kind == 'cloudify':
            # the 4A/4B cloud deck reads as beige sand: soften, cool and whiten only the bright,
            # low-saturation areas so they read as backlit cumulus, leaving the temple untouched
            lum = luma(img)
            mx, mn = img.max(axis=2), img.min(axis=2)
            sat = (mx - mn) / np.maximum(mx, 1e-3)
            m = smoothstep(fx.get('lo', 0.25), fx.get('hi', 0.6), lum) * (1 - smoothstep(0.12, 0.35, sat))
            m = blur(m[..., None], int(6 * scale), 1) * fx.get('amount', 0.8) * e
            soft = up(blur(down(img, 4), max(1, int(3 * scale)), 2), 4, img.shape)
            tint = np.array(fx.get('tint', (0.97, 1.0, 1.04)), np.float32)
            lifted = (lum[..., None] * 0.35 + soft * 0.65) * tint * fx.get('gain', 1.08)
            img = img * (1 - m) + lifted * m
        elif kind == 'rgbsplit':
            px = int(fx.get('px', 8) * e * scale)
            if px:
                img = img.copy()
                img[..., 0] = np.roll(img[..., 0], px, axis=1)
                img[..., 2] = np.roll(img[..., 2], -px, axis=1)
    return img


def mix_transition(a, b, t, tr, k):
    kind = tr['type']
    if kind == 'dissolve':
        return a * (1 - t) + b * t
    if kind == 'whiteout':
        w = 1 - abs(2 * t - 1)
        base = a if t < 0.5 else b
        return base + w * tr.get('amount', 1.2)
    if kind == 'luma':
        # bright areas of B appear first (dust -> cloud)
        lb = blur(luma(b)[..., None], 6, 1)
        m = smoothstep(1.0 - t * 1.6, 1.0 - t * 1.6 + 0.35, lb)
        return a * (1 - m) + b * m
    if kind == 'diag':
        # thin bright hairline slicing diagonally; reveals B behind it (ref: room video wipes)
        h, w = a.shape[:2]
        yy, xx = _grid(h, w)
        ang = math.radians(tr.get('angle', 50))
        d = (xx * math.cos(ang) + (h - yy) * math.sin(ang))
        dmax = w * math.cos(ang) + h * math.sin(ang)
        pos = ease(t, 'inout') * dmax * 1.1 - 0.05 * dmax
        m = (d < pos).astype(np.float32)[..., None]
        out = a * (1 - m) + b * m
        line = np.exp(-((d - pos) / tr.get('width', 2.0)) ** 2)[..., None]
        glow_ = np.exp(-((d - pos) / (tr.get('width', 2.0) * 12)) ** 2)[..., None]
        return out + line * 2.5 + glow_ * 0.25
    return b


def finish_frame(edl, tl, k, img, scale=1.0):
    ci = tl[k][0]
    c = edl['clips'][ci]
    g = GRADES.get(c.get('grade', 'neutral'), GRADES['neutral'])
    img = grade(img, g)
    fin = edl.get('finish', {})
    img = glow(img, fin.get('glow_threshold', 0.72), int(fin.get('glow_radius', 28) * scale), fin.get('glow', 0.22), tuple(fin.get('glow_tint', (1.0, 0.5, 0.3))))
    img = chroma_ab(img, fin.get('chroma', 0.0012))
    img = vignette(img, fin.get('vignette', 0.3))
    img = grain(img, fin.get('grain', 0.03), seed=k)
    lb = edl.get('letterbox', [[0, 2.39]])
    frames = [p[0] for p in lb]
    ratios = [p[1] for p in lb]
    ratio = float(np.interp(k, frames, ratios))
    img = letterbox(img, ratio)
    return np.clip(img, 0, 1)


# ----------------------------------------------------------------------------- main

def main():
    a = sys.argv[1:]
    edl_path = a[0] if a and not a[0].startswith('--') else os.path.join(FILM, 'edit', 'edl.json')
    edl = json.load(open(edl_path))

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            return a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith('--') else True
        return default
    preview = bool(opt('--preview'))
    scale = 0.5 if preview else 1.0
    out = opt('--out', os.path.join(FILM, 'out', 'escapement_preview.mp4' if preview else 'escapement.mp4'))
    audio = opt('--audio')
    tl = build_timeline(edl)
    rng = opt('--range')
    k0, k1 = 0, len(tl)
    if rng:
        i = a.index('--range')
        k0, k1 = int(a[i + 1]), int(a[i + 2])
    w, h = int(W * scale), int(H * scale)
    cache = ShotCache(scale)
    stills = opt('--stills')
    if stills:
        os.makedirs(os.path.join(FILM, 'out', 'stills'), exist_ok=True)
        for k in [int(x) for x in str(stills).split(',')]:
            img = finish_frame(edl, tl, k, render_frame(edl, tl, k, cache, scale), scale)
            p = os.path.join(FILM, 'out', 'stills', f'edit_{k:04d}.jpg')
            enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-s', f'{w}x{h}', '-i', '-', '-q:v', '2', p], stdin=subprocess.PIPE)
            enc.communicate((img * 65535).astype(np.uint16).tobytes())
            print('[still]', p)
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-s', f'{w}x{h}', '-r', str(edl.get('fps', 24)), '-i', '-']
    if audio:
        cmd += ['-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '320k', '-shortest']
    if out.endswith('.mkv'):  # lossless 16-bit intermediate segment (joined + encoded once at the end)
        cmd += ['-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'rgb48le', out]
    else:
        cmd += ['-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow' if not preview else 'veryfast',
                '-crf', '14' if not preview else '20', '-tune', 'grain' if not preview else 'film',
                '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(k0, k1):
        img = finish_frame(edl, tl, k, render_frame(edl, tl, k, cache, scale), scale)
        enc.stdin.write((img * 65535 + 0.5).astype(np.uint16).tobytes())
        if k % 24 == 0:
            print(f'[edit] {k}/{k1}', flush=True)
    enc.stdin.close()
    enc.wait()
    print('[edit] wrote', out)


if __name__ == '__main__':
    main()
