"""Final assembly: render the missing edit segment(s), join all lossless segments, mux the mix, encode.

  py film/tools/assemble.py            -> film/out/ESCAPEMENT.mp4 (master, CRF 14) + ESCAPEMENT_share.mp4 (<30 MB)

Segments are split at hard cuts. Reused segments (already rendered) are listed in SEGS with their start
frame in the CURRENT timeline; a segment is re-rendered when its file is missing.
"""
import json, os, subprocess, sys

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
OUT = os.path.join(FILM, 'out')
SEG = os.path.join(OUT, 'seg')
E = json.load(open(os.path.join(FILM, 'edit', 'edl.json')))
st, total = E['starts'], E['total']
# (file, start, end) in the current timeline; transitions never cross a boundary
plan = [
    ('s1_0000.mkv', 0, st['2G']),
    ('s2_0316.mkv', st['2G'], st['3A']),
    ('s3_0356.mkv', st['3A'], st['4B'] - 6),          # 3E tail frames mix with 4B -> next segment
    (f"s4_{st['4B'] - 6:04d}.mkv", st['4B'] - 6, st['4F']),
    ('s6_0688.mkv', st['4F'], st['5A']),             # rendered when 4F started at 688: content is position-independent
    ('s7_0754.mkv', st['5A'], total),
]


def nframes(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=nb_read_packets', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.strip()
    return int(r or 0)


for name, a, b in plan:
    p = os.path.join(SEG, name)
    if not os.path.exists(p):
        print(f'[assemble] rendering {name} ({a}..{b})', flush=True)
        subprocess.run([PY, os.path.join(FILM, 'tools', 'edit.py'), os.path.join(FILM, 'edit', 'edl.json'),
                        '--range', str(a), str(b), '--out', p], check=True)
    n = nframes(p)
    print(f'[assemble] {name}: {n} frames (expected {b - a})', flush=True)
    if n != b - a:
        sys.exit(f'frame count mismatch in {name}')

lst = os.path.join(SEG, 'concat.txt')
with open(lst, 'w') as f:
    for name, _, _ in plan:
        f.write(f"file '{os.path.join(SEG, name)}'\n")
mix = os.path.join(OUT, 'mix_final.wav')
subprocess.run([PY, os.path.join(FILM, 'tools', 'mix.py'), os.path.join(FILM, 'edit', 'cues.json'), '--out', mix], check=True)
master = os.path.join(OUT, 'ESCAPEMENT.mp4')
vf = 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'
tags = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', mix,
                '-map', '0:v', '-map', '1:a', '-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-tune', 'grain',
                *tags, '-c:a', 'aac', '-b:a', '320k', '-shortest', '-movflags', '+faststart', master], check=True)
print('[assemble] master', master, round(os.path.getsize(master) / 1e6, 1), 'MB', flush=True)
# phone-friendly copy under the 30 MB upload limit (two-pass, ~5.5 Mb/s)
share = os.path.join(OUT, 'ESCAPEMENT_share.mp4')
dur = total / 24.0
vbit = int((27.0 * 8e6 / dur) - 192e3)
for ps in (1, 2):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', master, '-c:v', 'libx264', '-preset', 'slow', '-b:v', str(vbit),
           '-pass', str(ps), '-passlogfile', os.path.join(SEG, 'x264pass'), *tags, '-pix_fmt', 'yuv420p']
    cmd += (['-an', '-f', 'null', '-'] if ps == 1 else ['-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', share])
    subprocess.run(cmd, check=True)
print('[assemble] share', share, round(os.path.getsize(share) / 1e6, 1), 'MB', flush=True)
