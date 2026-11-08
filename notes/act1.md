# Act I - THE MOVEMENT (+ 6A title) - iteration log

Script: `shots/act1_gears.py` (`--shot 1A|1B|1C|1D|1E|6A`, also comma lists; `--st<ID> f1,f2` per-shot stills override).
Kit: `lib/act1_kit.py` (gear builder w/ round/pinion/club/trap teeth, crossings, sunk disks; screws, jewels,
bridges, hairspring w/ shape-key breathing; Cotes de Geneve / perlage / worn brass / blued / ruby materials; motes).

Scale: built big (wheels 0.5-2.6 m), faked macro with 85-135 mm lenses at f/1.6-2.2 -> few-cm DOF.

## v1 (first build)
- One scene per shot (each shot builds its own set-up from the kit; < 15 s build).
- 1E/T1: hero gear 48T, 6 spokes, tip D ~3.0 m, axis = world +Y, camera at -Y on axis, 28 mm,
  distance = D*lens/(0.95*20.25 mm) -> 95% frame height. Spin = rotation about +Y increasing = clockwise on screen.
  Spin-up eases in from frame 40 to 26 deg/frame at 60 (kept < 30 deg/frame so the 6-fold spokes never
  alias into an apparent reverse spin). Shutter 0.75, motion blur steps 2.

## v2 (session 2, continuation after crash) - baseline review of all shots (40%, 12 spp)
- 1A ok-ish (v1): too many near-lens bokeh motes (snowstorm), hero face shows a woven "carbon fibre" pattern.
- 1B/1C/1D: milky, washed out, no blacks at all: world fog 0.03 everywhere + 70 kW cyan back spots = flat grey veil.
  Cameras too grazing (8-12 deg elevation) -> escape wheel/balance seen edge-on, unreadable. 1C: balance cock sits
  between camera and balance (big blurry slab).
- Carbon-fibre weave = (a) mat_brass_x orthogonal stretched-noise scratches (s1 along Y, s2 along X/Z -> grid),
  (b) Geneve arcs at 3 mm period in the bump -> moire.
- 1E: f20 chaotic zoom-blur soup; f40 back-haze spot pointing at the lens makes radial god-ray starburst;
  f62 hero OK-ish but bright fog blob top right and starfield-like motes (reads as space, not clockwork).
- 6A: same starburst from back spot through gear teeth (looks like zoom blur), bokeh blizzard, title small/muddy.

## v3 - materials + atmosphere + cameras
- Scratches -> sparse iso-lines of stretched noise in two OBLIQUE directions masked by patch noise (no grid).
  Geneve -> curved sawtooth bands (bump tilt per band, no 3 mm arcs). Perlage ring freq lowered.
- World fog 0.03 -> 0.004; background glow now from a local noisy haze box (K.haze) lit by a cyan spot from
  the SIDE/top (no spot aimed into the lens). Key lights volume_factor 0-0.15 so the foreground stays black.
- K.sheen_card: area light at the camera's mirror direction so flat plates/bridges show their finish.
- 1B/1C/1D cameras raised to 24-36 deg (K.orbit_pos); 1C cock arm moved to the back-left, hairspring moved
  ABOVE the arms (under the cock), stud under the cock arm. 6A title bigger/thicker, sweep = tall area light
  behind camera whose reflection crosses the letter faces (area-light specular is analytic; an emissive card
  behind the camera would be invisible to screen-space reflections).
- Result: escapement + hairspring now clearly readable; but everything over-bright (sheen 140-220 W far too
  hot), perlage = polka dots, blued screw sitting ON every bridge jewel, and a new artifact became obvious:
- RADIAL COMB STREAKS on every gear face. Diagnosed on CPU (evaluated corner normals): tooth profile has
  consecutive points at equal angles; the inner rings reused those angles -> zero-length edges -> degenerate
  quads (aspect 1e9) -> garbage normals in every smoothing fan. Fixed: inner rings evenly spaced +
  remove_doubles/dissolve_degenerate in MB.build. Corner-normal deviation on faces now 6e-8; polys -20%.
## v4 - sheen 3.5x lower, screws moved off jewels, softer perlage, 1D rack hero->back train (pillars stay soft),
  6A gear key dimmed, 1E end motes = few soft bokeh discs, 1E shutter animated 0.3 (flight) -> 0.75 (spin-up).
## v5 - K.gear_wall: 6 proto wheel meshes (bevel applied) reused as linked duplicates on parent empties
  (spin about local axis), 34-50 wheels per background layer -> ~80+ wheels per shot at little cost.
  1B now good (deep tones, ruby pallets, club teeth, razor DOF). 6A lush but title low-contrast vs lit wheels.
  1D blown: the 70 kW haze spot cone hit the floor plate.
## v6 - K.vol_only(): haze spots now light ONLY the volume (diffuse/specular 0) -> silhouettes against glowing
  haze, no blown floors. 6A: gear world lit grazing from behind-left + cyan haze sheet between title and
  gears. 1A world fog 0.024 -> 0.007 + local haze box (v5 sweep looked like hot neon). 1C pulled back
  (balance rim + screws in frame). 1D lower (15 deg), dolly 1.0 m (was 2 m: near-layer blur ~90 px/frame).
  Ruby glow 1.2 -> 0.7 (pallets looked like plastic LEDs).
## v6 review / v7
- 1A f44 at reference level (bevelled teeth, dark screwed face, warm/cool bokeh). f20 sweep still clipped -> 240 W.
- 1B, 1C good: ruby pallets, gold club teeth, blued hairspring, balance rim now in frame.
- 1E motion sheet (34 frames): dense hazy corridor, banking, exit into black, spin-up smear reads; corridor
  ended abruptly into ~12 frames of void -> side walls extended to just behind the final camera position
  (T1 frame stays clean) + ceiling/floor walls; hero gets a polished bezel ring with 12 blued screws + collar.
  Clockwise check (math): spin = +Y rotation, camera looks +Y with right = +X -> top moves right = CW.
- GOTCHA: a RELATIVE --outdir (tests/1E_motion) was resolved by Blender against the drive root (C:\tests\...).
  Always pass an absolute --outdir. (C:\tests\2G_motion from act2 has the same problem.)
- 1D: haze light 70 kW -> 14 kW (camera at 15 deg looks straight into it; metal reflected the glow -> milky);
  near wheel gold -> darker rust. 6A: sweep is now a steep top-down spot (its beam no longer lands on the gear
  behind the title, which was the bright patch killing title contrast).
## v8 review / v9
- 1B tick motion (frames 6-21, step 1): wheel locked, jumps one tooth with blur on local 13 (= cut 7),
  anchor snaps, settles. Tick jolt noise halved (0.012 -> 0.006); foreground motes 500 -> 260, warmer.
- 6A v8: title finally pops (warm machined letters vs. silhouetted gears in cyan haze) after tilting the
  background trains off the lens axis. v9: in-focus motes around the title 260 -> 90 (read as snow), added a
  warm GearRim area light from behind-right so teeth/rims glint while faces stay dark.
- 1D v8 still silvery-white: the 300 W cyan RimCool sat exactly in the low camera's mirror direction, so every
  horizontal wheel face reflected it. Now 60 W, raised to z 3.
## full-res pass (32 spp default) + new CLIENT RULES in BRIEF.md
- v9: 6A title pops with warm rim glints on the gear teeth; 1D finally warm/moody with deep blacks.
- Full-res stills 1A f40, 1B f14, 1C f12, 1D f24, 1E f60, 6A f36 (tests/*_full_*). exposure_check.py:
  1A/1C/1D/1E/6A PASS (p5 0.00, no clipping, colourful 31-61); 1B FAIL 0.9% clipped (gold top face + rubies).
  1E approach frame (f34, small gear in black) = LOW CONTRAST by design (deliberate dark approach).
- 1A + 6A motion sheets OK (1A: specks in black -> sweep reveal ~local 10 -> slow push; 6A: gears in focus
  -> rack to title -> sweep -> fade).
- CLIENT RULE (effects must look real): retired emissive motes. New K.mat_dust = non-emissive diffuse +
  translucent (only visible where a light hits it, glows when backlit); K.motes now rejection-samples a
  turbulence density (clumps/wisps, not evenly spread) and DUST_SCALE 0.5 halves every count.
- 1B: KeyRake 450 -> 300, sheen 20 -> 11 (clipping); perlage roughness rings lower contrast.
- 6A: font offset -0.0012 -> 0 (negative offset + bevel made a light spike on the M's acute vertex).
## final pass timing (full res 1920x1080, default 32 spp, steady-state = 2nd of two consecutive frames)
- 1B 15.7 s, 1D 17.6 s, 1E 11.8 s, 6A 18.4 s, 1A 32.7 s, 1C 56.1 s per frame. 1A/1C are the f/1.6 shots with
  the biggest defocus -> EEVEE DOF gather cost. Fix: K.dof_settings bokeh_max_size 200 -> 120 px, 1C f/1.6 -> 2.0.
- QC (exposure_check.py) final: 1A/1C/1D/1E/6A PASS; 1B 0.7% clipped = red channel of the lit exit ruby pallet
  (located with a clip map) -> ruby albedo 0.38 -> 0.2.
- 6A spike above the M persisted with offset 0: the CURVE bevel mitres the acute V. Title is now converted to a
  mesh (extrude only) and bevelled with a Bevel modifier, use_clamp_overlap=True.
## final state (session 2)
- 1C cost was the CLEAR-COAT on the blued hairspring (2nd ray-traced closure over half the frame): coat removed
  -> 1C 56-65 s -> 15-16 s/frame. Re-timed (full res, 32 spp, steady state): 1A ~20 s (33 s under heavy GPU
  contention), 1B 16 s, 1C 15 s, 1D 18 s, 1E 12 s, 6A ~10-18 s. Measurements are noisy (+-2x) because other
  acts render at the same time.
- exposure_check.py on final frames: all six PASS (1A_final2 f40, 1B_final2 f14, 1C_final3 f13, 1D_final f24,
  1E_final f60, 6A_final2 f12/f36). 1E approach frames (~f30-45, small gear on black) read LOW CONTRAST by design.
- 6A title now mesh + clamped Bevel modifier: no spike on the M.
- Final render: rb.py shots/act1_gears.py -- --shot <ID> --anim --from 1 --to <render_frames>
  (defaults: 32 spp, motion blur on; 1E 2 mb steps + animated shutter 0.3 -> 0.75).

## REVISION PASS (session 3, after director review score 5) - 13:50 ->
### r1 (1E, 1A, 6A)
- 1E: corridor now runs to the hero (side walls y 0-33 / 55 wheels, ceiling+floor walls y 17-35 / 20 wheels, gates at
  27.2 + 29.6, cf/beams/posts extended; everything ends behind the final camera at y 31.6 -> T1 frame stays black).
  END_FLY 46 -> 54, spin-up 46 -> 60. Hero redesigned to rhyme with 2A: teeth/rim = blackened steel 'tyre' (per-face
  material slot by radius), polished chrome lip ring r 1.04-1.12 (~68% frame height), darker brass spokes, collar
  r 0.19-0.23 + gold 14-notch castellated nut (~13% frame height) instead of the ruby; blued screws removed.
  Two faint warm vertical haze strips behind the hero at screen x 25%/75% (pre-echo of 2A's strip lights).
  motesEnd deleted. Beams geneve -> brass, posts steel_pol -> steel (stripe textures aliased under vector blur).
  warm{i} 320 -> 150 W, shadow_soft 0.8. motion_blur_max 256. Motion-blur steps cannot be keyed -> frame_change_pre
  handler switches eevee.motion_blur_steps 3 (flight) -> 8 (from local 46, spin-up smear). r1 f60: smooth spoke smear.
- r1 1E f30/f44: blocky 'knit' pattern in the dark haze = volumetric froxel aliasing of the gear-wall tooth SHADOWS in
  the corridor haze -> haze spots use_shadow=False. Approach re-timed (cruise -> max at 44 -> brake): hero 45% at
  local 44 -> 95% at 54 (was 70% at 44).
- 1A r1: sweep = elongated SPOT (scale y 0.22 -> horizontal band ~1.5 teeth tall) climbing the tooth stack; f18 shows
  4 lit teeth with darkness above/below. But f8/f12 still black -> band now enters at cut-in, BackHaze from frame 1
  at 45 kW, Sliver spot 2.6 kW. brass_big now yellow brass + per-tooth voronoi hue/value + polished bevel edges
  (object-normal |nz|~0.7 edge mask - EEVEE has no Pointiness) + fine flank tool marks. Face screws polished steel/gold
  0.01 proud. FaceSheen card at the camera mirror direction about the wheel axis (face read as a black board).
- 6A r1: offset 0.0035 + extrude 0.035 + bevel 0.009x4 -> heavy machined letters, but the text offset left a
  swallowtail spike above the M (reflex notch vertex) -> the M is taken from a thin (offset 0.0012) copy (letters
  split into islands, sorted by x). Retimed: rack by 18, sweep 16 -> 40, hold 40-56 (strip 110, key 60), fade 56-66.
  Camera yaw drift x -0.62 -> +0.2; fstop 2.0 -> 1.4 after the rack; bgTrain y 2.4 -> 3.2; rule rougher, screws gone.
### kit/materials (all shots)
- mat_ruby: transmission 1.0, base (0.85,0.06,0.10), IOR 1.77, rough 0.02, DITHERED + raytrace refraction, emission
  only 0.03. jewel mesh: pin-size hole (10%) + domed oil sink, chaton = darker 'Chaton' gold.
- mat_perlage: no Distance in base colour, bump 0.08 -> 0.02, per-spot roughness offset, cell 0.05 -> 0.03.
- mat_blued: peacock blue (0.02,0.07,0.30)/(0.03,0.12,0.38), rough 0.12-0.25.
- mat_brass_x: edge (polished worn bevels), cell (per-tooth variation), flank (machining marks) options.
- K.haze_window(): gear wall + noisy cyan haze box + volume-only spot placed along the camera ray through the top third
  of the frame (ny ~0.6) -> 1B/1C/1D get the img_gears 'dark brass against luminous cyan' window.
### 1B/1C/1D (r2)
- 1B: plate r 2.6 -> 1.8, centre moved -y, lowered to z -0.6; haze window top third; RimCool behind/above; bowed anchor
  arms (K.band quadratic outline); chamfered pallets; unlock phase (wheel drawn back, anchor eases 6->12) + run to
  banking after the tick; rougher Geneve on the bridges (top-edge glint); jittered DOF (max 200 px, overblur 6).
- 1C: reframed 85 mm el 42 dist 5.0 (whole balance), PER 26 -> 18, hairspring 16 coils / h 0.018 / t 0.005, cock
  shorter (1.35) with fine dark Geneve (stripe 0.035), KeyRake 450 -> 260 low from the left, sheen 16 -> 8, plate r 1.6
  so the top quarter shows the haze window, train moved to the near right (defocused foreground layer).
- 1D: plate y [-1.2, 1.6], plate2 lowered; nearWheel dark brass (base 0.15) and lowered (u -0.35); rack 1 -> 12;
  pillar0 x -0.13 (exits by ~local 9); jittered DOF; haze window.
### r2 review
- 1E r2: knit pattern gone (smooth deep-blue haze); f44 hero framed at the end of the gear tunnel; T1 frame: dark tyre,
  chrome lip, smooth 8-step spoke smear. Motion sheet (tests/1E_sheet_r3.jpg, 34 frames step 2): continuous corridor all
  the way, hero visible down the tunnel from ~local 41, walls slide out of frame, brake 45% -> 95%, spin-up. No dead air.
- 1A r2: band reveal works (f12: 3 lit teeth, f18 higher, lower teeth fall back to dark); f8 only a sliver at the bottom
  -> r3 band starts at z -0.34 so the lowest teeth are lit at the cut-in; face sheen was too pale -> 16 -> 7 W.
- 6A r2: M spike gone; hold still dim -> HoldCard (broad warm area light straight behind the camera, diffuse 0.2) 36->44
  fade-in, hold to 56, out by 64. r3 f50: lit machined letters, PASS.
- 1B/1C r2: perlage became grey camouflage (per-spot roughness 0.14-0.42) and very pale; 1C haze window works (blue
  with dark wheel silhouettes) but 1B/1D windows were dim (blocked / spot not reaching the visible part).
### r3 -> r4
- K.haze_glow: haze box whose density AND a faint emission share one noise field with a spherical falloff (no box edges)
  so the window glows regardless of spot aiming. r3 glow 0.35 was milky/white (1B, 1C p95 0.87) and the metal plates
  mirrored it -> r4: glow per shot (1B 0.12, 1C 0.04, 1D 0.16), saturated cyan (0.3,0.62,1.0), perlage base 0.27
  (dark: it mirrors the haze), narrow roughness band (no camo), sheen 1B 4 W.
- 1D r3 underexposed (p95 0.16 at f7) after the sheen cut -> KeyRake 750 -> 1100, KeyRake2 250 -> 420, sheen 16.
