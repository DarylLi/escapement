"""Tile the newest test still of each shot (in shotlist order) into one labelled contact sheet.

  py film/tools/latest_grid.py [out.jpg] [--ids 1A,1B,...] [--cols 4] [--w 480] [--dir tests]
"""
import json, os, re, subprocess, sys

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[1:]


def opt(n, d):
    return a[a.index(n) + 1] if n in a else d


out = a[0] if a and not a[0].startswith('--') else os.path.join(FILM, 'out', 'latest_grid.jpg')
src = os.path.join(FILM, opt('--dir', 'tests'))
ids = opt('--ids', None)
ids = ids.split(',') if ids else [s['id'] for s in json.load(open(os.path.join(FILM, 'shotlist.json')))['shots']]
cols = int(opt('--cols', 4))
w = int(opt('--w', 480))
h = w * 9 // 16
files = os.listdir(src)
picked = []
for sid in ids:
    cands = [f for f in files if re.match(rf'^{sid}(_|$)', f) and f.endswith('.jpg') and 'sheet' not in f]
    if not cands:
        continue
    best = max(cands, key=lambda f: os.path.getmtime(os.path.join(src, f)))
    picked.append((sid, os.path.join(src, best)))
if not picked:
    sys.exit('no stills')
inputs, fc = [], ''
font = 'C\\:/Windows/Fonts/bahnschrift.ttf'
for i, (sid, p) in enumerate(picked):
    inputs += ['-i', p]
    label = os.path.basename(p).replace('.jpg', '')
    fc += (f"[{i}:v]scale={w}:{h},setsar=1,"
           f"drawtext=fontfile='{font}':text='{label}':x=8:y=8:fontsize={max(12, w // 26)}:fontcolor=white:box=1:boxcolor=black@0.6[v{i}];")
n = len(picked)
rows = (n + cols - 1) // cols
for j in range(n, rows * cols):  # pad with black tiles
    fc += f"color=black:s={w}x{h}:d=1[v{j}];"
layout = '|'.join(f'{(k % cols) * w}_{(k // cols) * h}' for k in range(rows * cols))
fc += ''.join(f'[v{k}]' for k in range(rows * cols)) + f'xstack=inputs={rows * cols}:layout={layout}'
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', fc, '-frames:v', '1', '-q:v', '3', out], check=True)
print(out, [s for s, _ in picked])
