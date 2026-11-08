"""Builds film/edit/edl.json from shotlist.json + the editorial plan below.

Per-shot overrides: 'trim': (+in, -out) frame offsets inside handles (to land cuts on beats),
'tr_in' transition from the previous shot, 'fx' list (see edit.py), 'grade'.
"""
import json, os

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SL = json.load(open(os.path.join(FILM, 'shotlist.json')))

PLAN = {
    '1A': dict(fx=[dict(type='black', **{'from': 0, 'to': 10, 'env': 'down'})]),
    '1B': dict(fx=[dict(type='shake', **{'from': 5, 'to': 9, 'px': 6})]),
    '1C': dict(),
    '1D': dict(),
    '1E': dict(fx=[dict(type='whip', **{'from': 0, 'to': 2, 'env': 'down', 'px': 90}),
                   dict(type='zoom', **{'from': 48, 'to': 55, 'env': 'up', 'amount': 0.06})]),
    '2A': dict(fx=[dict(type='zoom', **{'from': 0, 'to': 4, 'env': 'down', 'amount': 0.06})]),
    '2B': dict(fx=[dict(type='whip', **{'from': 0, 'to': 3, 'env': 'down', 'px': 160})] +
               [dict(type='shake', **{'from': f, 'to': f + 3, 'env': 'down', 'px': 10}) for f in (11, 23, 35, 47, 59)]),
    '2C': dict(),
    '2D': dict(),
    '2E': dict(fx=[dict(type='exposure', **{'from': 0, 'to': 4, 'env': 'down', 'stops': 0.35})]),
    '2F': dict(),
    '2G': dict(),
    '3A': dict(fx=[dict(type='whip', **{'from': 0, 'to': 3, 'env': 'down', 'px': 200}),
                   dict(type='leak', **{'from': 0, 'to': 21, 'env': 'tri', 'amount': 0.25, 'x': 0.88})]),
    '3B': dict(),
    '3C': dict(),
    '3D': dict(fx=[dict(type='leak', **{'from': 0, 'to': 15, 'env': 'tri', 'amount': 0.28, 'x': 0.15, 'color': (1.0, 0.15, 0.1)})]),
    '3E': dict(fx=[dict(type='shake', **{'from': 14, 'to': 26, 'px': 14})]),
    '3G': dict(fx=[dict(type='shake', **{'from': 9, 'to': 16, 'env': 'tri', 'px': 14})]),
    '3H': dict(fx=[dict(type='whip', **{'from': 0, 'to': 3, 'env': 'down', 'px': 140})]),
    '3F': dict(fx=[dict(type='shake', **{'from': 10, 'to': 22, 'env': 'tri', 'px': 6})]),
    '4A': dict(tr_in=dict(type='luma', frames=12), fx=[dict(type='cloudify', **{'from': 0, 'to': 999, 'env': 'flat', 'amount': 0.85})]),
    '4B': dict(tr_in=dict(type='luma', frames=12), fx=[dict(type='cloudify', **{'from': 0, 'to': 999, 'env': 'flat', 'amount': 0.85})]),
    '4C': dict(),
    '4D': dict(),
    '4E': dict(),
    '4F': dict(),
    '5A': dict(),
    '5B': dict(fx=[dict(type='whip', **{'from': 0, 'to': 3, 'env': 'down', 'px': 140})]),
    '5C': dict(fx=[dict(type='zoom', **{'from': 26, 'to': 35, 'env': 'up', 'amount': 0.15})]),
    '6A': dict(fx=[dict(type='zoom', **{'from': 0, 'to': 4, 'env': 'down', 'amount': 0.05})]),
}


# 4A dropped after the 0x119 crash cost the render time: 3E's dust dissolves straight into 4B's cloud
SKIP = {'4A', '4D', '4E'}  # 4D/4E: the reworked temple scene hung the GPU; not rendered


def act_grade(sid):
    return 'act' + sid[0]


def build(trims=None, out=None):
    trims = trims or {}
    clips = []
    t = 0
    for s in SL['shots']:
        sid = s['id']
        if sid in SKIP:
            continue
        a, b = trims.get(sid, (0, 0))
        clip = dict(shot=sid, **{'in': s['cut_in_local'] + a, 'out': s['cut_out_local'] + b}, grade=act_grade(sid))
        clip.update({k: v for k, v in PLAN.get(sid, {}).items()})
        clips.append(clip)
        t += clip['out'] - clip['in'] + 1
    # letterbox: 2.39 through the film, opens to 16:9 on the temple reveal, closes for the title
    starts = {}
    k = 0
    for c in clips:
        starts[c['shot']] = k
        k += c['out'] - c['in'] + 1
    lb = [[0, 2.39], [starts['4B'] + 6, 2.39], [starts['4B'] + 30, 1.7778], [starts['6A'] - 1, 1.7778], [starts['6A'], 2.39]]
    edl = dict(fps=24, clips=clips, letterbox=lb, total=t, starts=starts,
               finish=dict(grain=0.028, glow=0.1, glow_threshold=0.72, glow_radius=28, chroma=0.0012, vignette=0.3))
    out = out or os.path.join(FILM, 'edit', 'edl.json')
    json.dump(edl, open(out, 'w'), indent=1)
    print('[edl]', out, t, 'frames', round(t / 24, 2), 's')
    return edl


if __name__ == '__main__':
    tr = {}
    p = os.path.join(FILM, 'edit', 'trims.json')
    if os.path.exists(p):
        tr = {k: tuple(v) for k, v in json.load(open(p)).items()}
    build(tr)
