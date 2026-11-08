"""Final-render queue: renders shots one at a time through rb.py (resumable; skips existing frames).

Only the frames the edit uses are rendered: the cut range plus handles where a transition needs them
(6 frames on a side with a dissolve/luma/diag/whiteout, 2 elsewhere for retiming slack).

  py film/tools/render_queue.py [IDs...] [--samples N] [--pct P] [--overwrite] [--dry]
"""
import json, os, subprocess, sys, time
FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
SL = json.load(open(os.path.join(FILM, 'shotlist.json')))
EDL = json.load(open(os.path.join(FILM, 'edit', 'edl.json')))
SOFT = ('dissolve', 'luma', 'diag', 'whiteout')


def ranges():
    clips = EDL['clips']
    out = {}
    for i, c in enumerate(clips):
        tin = c.get('tr_in', {}).get('type') in SOFT
        tout = i + 1 < len(clips) and clips[i + 1].get('tr_in', {}).get('type') in SOFT
        s = next(x for x in SL['shots'] if x['id'] == c['shot'])
        a = max(1, c['in'] - (6 if tin else 2))
        b = min(s['render_frames'], c['out'] + (6 if tout else 2))
        out[c['shot']] = (a, b)
    return out


a = sys.argv[1:]
extra = []
for flag in ('--samples', '--pct'):
    if flag in a:
        i = a.index(flag); extra += [flag, a[i + 1]]; del a[i:i + 2]
if '--overwrite' in a:
    a.remove('--overwrite'); extra += ['--overwrite']
dry = '--dry' in a
if dry:
    a.remove('--dry')
R = ranges()
ids = [i for i in (a or [s['id'] for s in SL['shots']]) if i in R]  # shots dropped from the edit are skipped
total = 0
def photo_handoff():
    """T4: 4F's final cut frame becomes the printed photo on the desk (renders/photo_temple.png)."""
    s4 = next(x for x in SL['shots'] if x['id'] == '4F')
    src = os.path.join(FILM, 'renders', '4F', f"{s4['cut_out_local']:04d}.png")
    dst = os.path.join(FILM, 'renders', 'photo_temple.png')
    if os.path.exists(src):
        import shutil
        shutil.copyfile(src, dst)
        print('[queue] photo handoff', src, '->', dst, flush=True)
        return True
    return False


for sid in ids:
    s = next(x for x in SL['shots'] if x['id'] == sid)
    f0, f1 = R[sid]
    if sid == '5A' and not dry and not photo_handoff():
        print('[queue] 5A skipped: 4F final frame not rendered yet', flush=True)
        continue
    total += f1 - f0 + 1
    out = os.path.join(FILM, 'renders', sid)
    need = [f for f in range(f0, f1 + 1) if not os.path.exists(os.path.join(out, f'{f:04d}.png'))]
    if dry:
        print(f'{sid}: frames {f0}-{f1} ({f1 - f0 + 1}), missing {len(need)}')
        continue
    if not need and '--overwrite' not in extra:
        print(f"[queue] {sid} complete", flush=True)
        continue
    t0 = time.time()
    print(f"[queue] {sid} start frames {f0}-{f1} (missing {len(need)})", flush=True)
    cmd = [PY, os.path.join(FILM, 'tools', 'rb.py'), os.path.join(FILM, 'shots', s['script']), '--', '--shot', sid,
           '--anim', '--from', str(f0), '--to', str(f1)] + extra
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=FILM,
                       env=dict(os.environ, RB_FINAL='1'))
    tail = '\n'.join(l for l in r.stdout.strip().splitlines()[-6:] if 'DIRECTOR NOTE' not in l)
    have = len([f for f in range(f0, f1 + 1) if os.path.exists(os.path.join(out, f'{f:04d}.png'))])
    print(f"[queue] {sid} rc={r.returncode} frames={have}/{f1 - f0 + 1} in {time.time() - t0:.0f}s\n{tail}", flush=True)
if dry:
    print('total frames', total)
