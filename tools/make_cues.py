"""Builds film/edit/cues.json (music + sound design) from film/edit/edl.json shot starts.

Only real downloaded free assets (Mixkit / Freesound CC0 / Pixabay) - never self-synthesized sounds.

Cue times are written relative to shot starts so the sound follows any re-trim of the edit.
"""
import json, os

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDL = json.load(open(os.path.join(FILM, 'edit', 'edl.json')))
ST = EDL['starts']
LEN = {c['shot']: c['out'] - c['in'] + 1 for c in EDL['clips']}
TOTAL = EDL['total']
S = 'audio/sfx/'
cues = []


def at(shot, i=0):
    return ST[shot] + i


def end(shot):
    return ST[shot] + LEN[shot]


def cue(name, frame, gain=-10, **kw):
    cues.append(dict(file=S + name + '.wav', frame=frame, gain_db=gain, **kw))


# ---------------------------------------------------------------- ACT I: the movement (no music)
cue('wind__deep_cinematic_hum', 0, -17, fade_in_s=1.5, dur_s=7.0, fade_out_s=0.8)
cue('boom__suspense_hit_swell', at('1A', 2), -13)
cue('riser__reverse_impact', at('1A', 30), -16, align='end', hp=200)
for k in range(0, end('1E') - 6, 12):           # metronome ticks on the 120 BPM grid
    cue('clock__tick_single_closemic', k + 6, -15 if k else -12, pan=(-0.3 if (k // 12) % 2 else 0.3))
cue('clock__tick_closemic_96k', at('1B', 6), -6, reverb=0.35)        # the escapement tick
cue('mech__gear_lock_metallic', at('1B', 7), -14)
cue('clock__ticktock_closeup', at('1C', 0), -14, dur_s=0.6, fade_out_s=0.1)
cue('mech__ratchet_fast', at('1D', 0), -16, dur_s=1.0, fade_out_s=0.2, pan=-0.4)
cue('whoosh__fast_swoosh', at('1E', 0), -14, align='peak')
cue('mech__gear_turn_scifi', at('1E', 8), -15)
cue('whoosh__tunnel_reverb_long', end('1E'), -9, align='peak')
cue('riser__trailer_short', end('1E'), -12, align='end')

# ---------------------------------------------------------------- ACT II: assembly (music in on T1)
cue('hit__trailer_whoosh_impact', at('2A', 0), -6, align='peak')
cue('boom__futuristic_bass_hit', at('2A', 0), -8, align='peak')
cue('servo__hydraulic_hoist', at('2A', 8), -16, dur_s=1.4, fade_out_s=0.3)
slams = ['metal__slam_factory_hard_hit', 'metal__slam_door_heavy', 'metal__slam_door_smash',
         'metal__slam_heavy_reverb', 'metal__slam_explosion_impact']
for n, f in enumerate((11, 23, 35, 47, 59)):
    cue(slams[n], at('2B', f), -7 + n * 0.6, align='peak', reverb=0.25)
    cue('boom__sub_knock', at('2B', f), -12, align='peak')
    cue('spark__welder_burst', at('2B', f), -17, pan=(0.4 if n % 2 else -0.4))
cue('servo__mech_movements', at('2B', 0), -19, dur_s=2.8, fade_out_s=0.5)
cue('spark__welding_short', at('2C', 0), -12)
cue('mech__gear_lock_fast_tap', at('2C', 3), -12)
cue('elec__fluorescent_flicker_on', at('2D', 0), -11)
cue('elec__powerup_static', at('2D', 0), -15)
cue('elec__fluorescent_switch_flicker', at('2E', 0), -12)
cue('car__engine_start', at('2F', 2), -6)
cue('car__supercar_rev', at('2F', 14), -7)
cue('glitch__disintegration', at('2G', 0), -9)
cue('glitch__laser_disintegrate', at('2G', 6), -11, pan=0.2)
cue('wind__desert_gust', at('2G', 10), -14, fade_in_s=0.6)
cue('car__v8_acceleration', at('2G', 26), -7)
cue('whoosh__cinematic_fast', end('2G'), -7, align='peak')

# ---------------------------------------------------------------- ACT III: the run
cue('car__highrpm_outside', at('3A', 0), -13, dur_s=(LEN['3A'] + LEN['3B']) / 24, fade_out_s=0.15)
cue('wind__sand_desert', at('3A', 0), -19, dur_s=6.0, fade_out_s=1.0)
cue('whoosh__fast_air', at('3B', 0), -12, align='peak')
# 3F drift
cue('whoosh__cinematic_fast', at('3F', 0), -11, align='peak')
cue('car__tire_squeal_long', at('3F', 4), -8, dur_s=1.4, fade_out_s=0.3)
cue('car__gravel_skid', at('3F', 8), -10)
cue('car__v8_rev', at('3F', 16), -9)
# 3G overpass: the car drives over the lens
cue('car__passby_loud', at('3G', 12), -5, align='peak')
cue('whoosh__deep_impact', at('3G', 12), -8, align='peak')
cue('boom__bass_hit_short', at('3G', 12), -10, align='peak')
# 3H slot canyon chase
cue('whoosh__wind_swoosh', at('3H', 0), -11, align='peak')
cue('car__highrpm_outside', at('3H', 0), -13, dur_s=LEN['3H'] / 24, fade_out_s=0.2, reverb=0.35)
cue('wind__dark_storm_gust', at('3H', 6), -15)
cue('whoosh__fast_transition', at('3C', 0), -12, align='peak')
cue('car__v8_revs_amg', at('3C', 4), -10)
cue('car__dyno_revs_turbo', at('3D', 0), -9, dur_s=0.9, fade_out_s=0.2)
cue('car__passby_v8_supercar', at('3E', 18), -4, align='peak')
cue('car__gravel_skid', at('3E', 16), -14)
cue('wind__storm_gust', at('3E', 30), -9, fade_in_s=0.5)
cue('whoosh__long_sweeping_air', end('3E'), -8, align='peak')

# ---------------------------------------------------------------- ACT IV: the sanctum
cue('wind__high_altitude', end('3E') - 12, -15, fade_in_s=0.5, dur_s=LEN['4B'] / 24 + 1.5, fade_out_s=1.5)
cue('choir__angelical_transition', end('3E') - 30, -12)
cue('riser__tech_choir', at('4B', 0), -12, align='end')
cue('boom__braam', at('4B', 0), -6, align='peak', reverb=0.3)
cue('bell__tower_toll_long', at('4B', 1), -9, reverb=0.4)
cue('whoosh__mighty_mysterious', at('4B', 0), -10, align='peak')
cue('choir__huge_echo_swell', at('4B', 6), -13)
cue('choir__magic_shine', at('4C', 0), -15)
if '4D' in ST:
    cue('whoosh__wind_sweep', at('4D', 0), -15, align='peak')
cue('bell__clock_gong', at('4E', 2) if '4E' in ST else at('4F', 0), -10, reverb=0.4)
cue('wind__mountain_top', at('4F', 0), -19, dur_s=LEN['4F'] / 24, fade_out_s=0.5)

# ---------------------------------------------------------------- ACT V: the desk
cue('camera__shutter_hard', at('5A', 0), -9, align='peak')
cue('whoosh__fast_air_zoom', at('5A', 2), -9)
cue('clock__pocketwatch_ticking', at('5A', 6), -18, dur_s=(LEN['5A'] + LEN['5B'] + LEN['5C']) / 24, fade_in_s=1.0, fade_out_s=0.2)
cue('paper__quick_movement', at('5B', 4), -14)
cue('whoosh__speeding', at('5B', 0), -12)
cue('pencil__on_table', at('5B', 30), -15)
cue('whoosh__deep_air', at('5C', 6), -12)
cue('whoosh__tunnel_reverb_long', end('5C'), -9, align='peak')
cue('riser__synth', end('5C'), -14, align='end')

# ---------------------------------------------------------------- VI: title
cue('hit__trailer_epic_impact', at('6A', 0), -4, align='peak', reverb=0.2)
cue('clock__tick_closemic_96k', TOTAL - 8, -8, reverb=0.5)

# Music: epical_drums_02 (120 BPM = 12 frames/beat). Track time = film time + 32.63 s up to the start of 3F.
# The 96 frames (8 beats = exactly 4.0 s) of extra driving (3F/3G/3H) are covered by repeating the
# previous two bars at the 3F cut, so the slams, the temple-reveal hit and the title hit stay locked.
# REP = frames the temple reveal moved later than the original 604 (track hit 57.837 s): must be whole
# bars (48 f) and is covered by repeating that many frames of music at the 3F cut (0 = no repeat).
INS = at('3F')
T0 = 32.63
REP = at('4B') - 604  # > 0: repeat that much music at the 3F cut; < 0: skip ahead (4A dropped = -1 bar)
assert REP % 48 == 0, f'reveal shift {REP} is not a whole number of bars'
music = [
    dict(file='audio/music/epical_drums_02.wav', start_frame=at('2A'), end_frame=INS,
         offset_s=T0 + at('2A') / 24.0, gain_db=-0.5, fade_in_s=0.0, fade_out_s=0.02),
]
if REP > 0:
    music.append(dict(file='audio/music/epical_drums_02.wav', start_frame=INS, end_frame=INS + REP,
                      offset_s=T0 + INS / 24.0 - REP / 24.0, gain_db=-0.5, fade_in_s=0.01, fade_out_s=0.02))
music += [
    dict(file='audio/music/epical_drums_02.wav', start_frame=INS + max(REP, 0), end_frame=at('5A'),
         offset_s=T0 + INS / 24.0 - min(REP, 0) / 24.0, gain_db=-0.5, fade_in_s=0.01 if REP else 0.0, fade_out_s=0.03),
    dict(file='audio/music/epical_drums_02.wav', start_frame=at('5A'), end_frame=TOTAL,
         offset_s=107.597, gain_db=-0.5, fade_in_s=0.01, fade_out_s=0.6),
]
out = dict(fps=24, length_frames=TOTAL, sr=48000, music=music, cues=cues,
           master=dict(gain_db=1.5, ceiling_db=-1.6, reverb_size_s=2.4))
p = os.path.join(FILM, 'edit', 'cues.json')
json.dump(out, open(p, 'w'), indent=1)
print('[cues]', p, len(cues), 'cues')
