"""Sound mixer for ESCAPEMENT (numpy, offline).

  py film/tools/mix.py film/edit/cues.json [--out film/out/mix.wav]

cues.json:
{ "fps": 24, "length_frames": 986, "sr": 48000,
  "music": [{"file": "audio/music/x.wav", "start_frame": 0, "offset_s": 12.0, "gain_db": -3,
             "fade_in_s": 0.0, "fade_out_s": 1.5, "end_frame": 986, "duck": [[frame, db], ...]}],
  "cues": [{"file": "audio/sfx/a.wav", "frame": 12, "gain_db": -6, "offset_s": 0, "dur_s": null,
            "fade_in_s": 0, "fade_out_s": 0.05, "rate": 1.0, "reverse": false, "pan": 0.0,
            "lp": null, "hp": null, "reverb": 0.0, "align": "start"|"peak"|"end"}],
  "master": {"gain_db": 0, "ceiling_db": -1.0, "reverb_size_s": 2.2} }
"align": "peak" places the loudest point of the sound on the given frame (great for impacts and
whooshes whose peak should hit the cut); "end" ends the sound on the frame (risers into a cut).
"""
import json, os, sys, subprocess
import numpy as np

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cache = {}


def load(path, sr):
    p = path if os.path.isabs(path) else os.path.join(FILM, path)
    if p not in _cache:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(sr), '-'],
                             capture_output=True).stdout
        _cache[p] = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    return _cache[p].copy()


def db(x):
    return 10 ** (x / 20.0)


def fft_filter(x, sr, lp=None, hp=None):
    n = len(x)
    if n < 16 or (not lp and not hp):
        return x
    N = 1 << int(np.ceil(np.log2(n * 2)))
    X = np.fft.rfft(x, N, axis=0)
    f = np.fft.rfftfreq(N, 1 / sr)
    g = np.ones_like(f)
    if lp:
        g *= 1 / np.sqrt(1 + (f / lp) ** 8)   # ~48 dB/oct-ish
    if hp:
        g *= 1 / np.sqrt(1 + (hp / np.maximum(f, 1e-3)) ** 8)
    return np.fft.irfft(X * g[:, None], N, axis=0)[:n].astype(np.float32)


def reverb_ir(sr, size_s=2.2, seed=1):
    rng = np.random.default_rng(seed)
    n = int(sr * size_s)
    t = np.arange(n) / sr
    env = np.exp(-6.9 * t / size_s)
    ir = rng.standard_normal((n, 2)).astype(np.float32) * env[:, None]
    ir = fft_filter(ir, sr, lp=6000, hp=120)
    ir[: int(sr * 0.012)] *= np.linspace(0, 1, int(sr * 0.012))[:, None]
    return ir / np.sqrt((ir ** 2).sum(axis=0, keepdims=True) + 1e-9)


def convolve(x, ir):
    n = len(x) + len(ir) - 1
    N = 1 << int(np.ceil(np.log2(n)))
    y = np.fft.irfft(np.fft.rfft(x, N, axis=0) * np.fft.rfft(ir, N, axis=0), N, axis=0)[:n]
    return y.astype(np.float32)


def resample(x, rate):
    if rate == 1.0:
        return x
    n = int(len(x) / rate)
    src = np.arange(n) * rate
    i = np.arange(len(x))
    return np.stack([np.interp(src, i, x[:, c]) for c in range(2)], axis=1).astype(np.float32)


def fades(x, sr, fi, fo):
    n = len(x)
    a = int(fi * sr)
    b = int(fo * sr)
    if a > 0:
        x[:a] *= np.linspace(0, 1, min(a, n))[:, None]
    if b > 0 and n > 0:
        b = min(b, n)
        x[n - b:] *= np.linspace(1, 0, b)[:, None] ** 2
    return x


def place(bus, x, start):
    if start < 0:
        x = x[-start:]
        start = 0
    end = min(len(bus), start + len(x))
    if end > start:
        bus[start:end] += x[: end - start]


def limiter(x, sr, ceiling_db=-1.0, block=64, lookahead_blocks=4, release_ms=150.0):
    """Block-based look-ahead peak limiter + soft clip safety."""
    c = db(ceiling_db) * 0.97
    n = len(x)
    nb = (n + block - 1) // block
    pad = np.zeros((nb * block - n, 2), np.float32)
    peak = np.abs(np.concatenate([x, pad])).max(axis=1).reshape(nb, block).max(axis=1)
    target = np.minimum(1.0, c / np.maximum(peak, 1e-9))
    # look-ahead: each block also respects the next few blocks' needs
    look = target.copy()
    for k in range(1, lookahead_blocks + 1):
        look[:-k] = np.minimum(look[:-k], target[k:])
    rel = np.exp(-block / (sr * release_ms / 1000))
    g = np.empty(nb)
    cur = 1.0
    for i in range(nb):
        t = look[i]
        cur = t if t < cur else t + (cur - t) * rel
        g[i] = cur
    gs = np.interp(np.arange(nb * block), np.arange(nb) * block + block / 2, g)[:n]
    y = x * gs[:, None].astype(np.float32)
    # soft knee only near the ceiling (a plain tanh would squash every peak ~2.5 dB below it)
    lim = db(ceiling_db)
    k = 0.85 * lim
    ay = np.abs(y)
    over = ay > k
    ay[over] = k + (lim - k) * np.tanh((ay[over] - k) / (lim - k))
    return (np.sign(y) * ay).astype(np.float32)


def main():
    a = sys.argv[1:]
    cues_path = a[0] if a else os.path.join(FILM, 'edit', 'cues.json')
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(FILM, 'out', 'mix.wav')
    C = json.load(open(cues_path))
    sr = C.get('sr', 48000)
    fps = C.get('fps', 24)
    L = int(C['length_frames'] / fps * sr) + int(sr * 1.5)
    sfx = np.zeros((L, 2), np.float32)
    wet = np.zeros((L, 2), np.float32)
    mus = np.zeros((L, 2), np.float32)
    for m in C.get('music', []):
        x = load(m['file'], sr)
        o = int(m.get('offset_s', 0) * sr)
        start = int(m.get('start_frame', 0) / fps * sr)
        end = int(m.get('end_frame', C['length_frames']) / fps * sr)
        x = x[o: o + (end - start)].copy() * db(m.get('gain_db', 0))
        x = fades(x, sr, m.get('fade_in_s', 0), m.get('fade_out_s', 0))
        if m.get('duck'):
            fr = np.array([p[0] for p in m['duck']], float) / fps * sr - start
            g = np.array([db(p[1]) for p in m['duck']])
            env = np.interp(np.arange(len(x)), fr, g)
            x *= env[:, None].astype(np.float32)
        place(mus, x, start)
    for c in C.get('cues', []):
        x = load(c['file'], sr)
        o = int(c.get('offset_s', 0) * sr)
        x = x[o:]
        if c.get('dur_s'):
            x = x[: int(c['dur_s'] * sr)]
        x = x.copy()
        if c.get('reverse'):
            x = x[::-1].copy()
        x = resample(x, c.get('rate', 1.0))
        x = fft_filter(x, sr, c.get('lp'), c.get('hp'))
        x = fades(x, sr, c.get('fade_in_s', 0.0), c.get('fade_out_s', 0.02))
        x *= db(c.get('gain_db', 0))
        pan = c.get('pan', 0.0)
        if pan:
            x[:, 0] *= np.sqrt(0.5 * (1 - pan)) * 1.414
            x[:, 1] *= np.sqrt(0.5 * (1 + pan)) * 1.414
        t = int(c['frame'] / fps * sr)
        align = c.get('align', 'start')
        if align == 'peak':
            t -= int(np.argmax(np.abs(x).max(axis=1)))
        elif align == 'end':
            t -= len(x)
        place(sfx, x, t)
        if c.get('reverb', 0) > 0:
            place(wet, x * c['reverb'], t)
    M = C.get('master', {})
    if np.any(wet):
        sfx += convolve(wet, reverb_ir(sr, M.get('reverb_size_s', 2.2)))[:L] * 0.6
    if '--stems' in sys.argv:  # per-act level report for balancing music vs sound design
        n = int(C['length_frames'] / fps * sr)
        edl = json.load(open(os.path.join(FILM, 'edit', 'edl.json')))
        st = sorted(edl['starts'].items(), key=lambda kv: kv[1])
        acts = {}
        for sid, f in st:
            acts.setdefault(sid[0], [f, f])
            acts[sid[0]][1] = f
        bounds = sorted((v[0], k) for k, v in acts.items()) + [(C['length_frames'], 'end')]
        for (f0, act), (f1, _) in zip(bounds, bounds[1:]):
            a, b = int(f0 / fps * sr), int(f1 / fps * sr)
            rm = 20 * np.log10(np.sqrt((mus[a:b] ** 2).mean()) + 1e-9)
            rs = 20 * np.log10(np.sqrt((sfx[a:b] ** 2).mean()) + 1e-9)
            print(f'[stems] act {act}: frames {f0}-{f1}  music {rm:6.1f} dB  sfx {rs:6.1f} dB  (sfx-music {rs - rm:+.1f})')
    mix = mus + sfx
    mix *= db(M.get('gain_db', 0))
    mix = limiter(mix, sr, M.get('ceiling_db', -1.0))
    mix = mix[: int(C['length_frames'] / fps * sr)]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pcm = (np.clip(mix, -1, 1) * 8388607).astype(np.int32)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 's32le', '-ar', str(sr), '-ac', '2', '-i', '-',
                          '-c:a', 'pcm_s24le', out], stdin=subprocess.PIPE)
    p.communicate((pcm << 8).astype(np.int32).tobytes())
    pk = np.abs(mix).max()
    rms = np.sqrt((mix ** 2).mean())
    print(f'[mix] wrote {out}  peak {20*np.log10(pk+1e-9):.1f} dBFS  rms {20*np.log10(rms+1e-9):.1f} dBFS  len {len(mix)/sr:.2f}s')


if __name__ == '__main__':
    main()
