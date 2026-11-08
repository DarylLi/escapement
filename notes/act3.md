# ACT III - THE RUN : iteration log

Files: `lib/canyon.py` (environment toolkit), `shots/act3_canyon.py` (shots 3A-3E, `--shot ID`).

Design
- Road = analytic centerline from a curvature profile (Gaussian bumps), arc length s / lateral d frame.
  Cliff (layered strata wall mesh in road frame) on the LEFT, terrain heightfield (world grid, KD-tree to
  centerline) dropping into the canyon on the RIGHT, distant strata mesas across the canyon.
- Aerial perspective is in every environment material (view-distance mix toward a view-dependent haze
  emission, warmer toward the sun) + thin world volume fog for sun shafts.
- Sky = custom gradient world (teal zenith, warm cream horizon, sun glow + disc) matching the per-shot sun.
- Scatter via one Geometry Nodes "Instance on Points" group (pick/rot/scale attributes): boulders,
  pebbles (~12k), scrub, grass tufts, guard posts + red reflectors, edge-line studs, chevron signs.
- Car driven along the road with per-frame keys (yaw from heading, roll from lateral accel, vibration),
  wheels spun by distance / radius. Dust = keyframed volume puffs (4D noise, object colour = density/emission).

## Iterations

v0 (02:56) GN scatter: setting a Collection on a modifier socket raises "id properties not supported"
   -> each scatter gets its own copy of the node group with the collection set on the Collection Info node.
v1 3E (03:02) car.py already available (switched from proxy; proxy kept as fallback).
   - Huge BLACK mass top-right: mesas were placed along road.point(s, d) for far-away s, so the winding road
     dropped one right next to the camera -> mesas now placed on a ring around the section and rejected
     if closer than R*1.35+160 m to ANY road sample; added a 9 km hazed canyon-floor plane (no void).
   - Sun was off-frame / behind the cliff (sun_dir from a far tangent): 3E sun now set relative to the
     camera forward vector, 9 deg right of centre (over the canyon side).
   - Dust = opaque hard-edged domes with checker noise: density 1.6 -> 0.5, noise-driven wispy mask
     (fall*0.25 + noise, mapped 0.52..0.85), wider radial falloff.
   - car.set_light was being passed 1.0 (lights almost OFF): now rear 90 / front 40.
   - Scene too dark overall: world strength 1.35, exposure +0.45, red rear glow light 150 -> 60 W.
   - Camera 3E: 20 mm, 0.42 m high, aimed 5.5 m up at 70 m -> more sky/cliff, less black ground.
   - car.py wheels: positive X = forward roll (proxy is opposite) -> sign per car; roll/pitch/vibration
     now keyed on car['sprung'] so wheels stay planted.
v2 all shots (03:26, batched one GPU-lock wait via --shot 3A,3B,...; --stills_<ID> per-shot frames)
   - 3C/3B/3A washed teal-grey: material haze far too dense for dusk exposure (20% at 80 m) -> haze
     distance 420 -> 1300 m (far rock 900 m); refs are clear at 100 m and only fade at km range.
   - Sky reads BLACK in the sun-facing shots (3A, 3E): suspect the 900x sun disc + pow(mu,3000) spike
     (inf/NaN spread by bloom) -> disc 30x, spike pow 400 x6.  Mesas no longer cast shadows
     (visible_shadow off) and are lower (H 40-100 m) so a 4-deg sun is never blocked by them.
   - 3D blown out pink/white: 1.8 m refractive heat-haze sheet in front of the lens + 40x flames ->
     sheet 0.6 m, IOR 1.015, flame cones smaller and 14x.
   - 3E plume engulfs far too early (puffs spawned next to the lens) -> trail starts 9 m past the
     camera, slimmer lateral growth; billows start f36-54 and reach the lens ~f62; cocoon f57->67.
   - 3B mirror reflected our own flank/rear bar: car.py glass re-origined + toed out 5 deg, planar probe
     matched, camera moved to 0.40 m directly behind the glass (35 mm, f/2).
   - Added crimson lens light-leaks (soft additive emissive cards glued to the lens) on 3A/3B/3D.

## Pass 2 (new builder, continuing after the standby crash) - 10:05

Review of v2 stills: unusable. Sky BLACK whenever the camera faces the sun (3A/3E), whole frames murky,
3C a uniform teal-grey wash (no road visible), 3E f50/72 a coarse checkerboard of dust, 3D a pink white-out.
Diagnostic (sky world + ground + fog box alone, tests/3diag_grid.jpg): the sky shader itself renders fine,
so the black/murk comes from the big volumes (400 m FogBox + 4 m cube dust + cocoon) at tile 8 / 8 samples.
v3 (10:35)
  - FogBox disabled (FOG_BOX_ON=False). Atmosphere = surface aerial perspective only (HAZE_D 1300->1000 m,
    far mesas 900->650 m, haze colour matched to the new horizon mint (0.60,0.76,0.69)).
  - Sky retuned toward the refs: bright cream-mint horizon band, saturated teal zenith.
  - Dust rebuilt: mat_dust2 on unit ICOSPHERE puffs, density = warped radial smoothstep x 4D fbm, forced to 0
    at the mesh surface (no box edges); trail puffs spawn at both rear tyres, spread to the canyon side.
    grow values are now radii. Trails start at f-50 (old puffs beyond the 60 m froxel range were wasted).
  - Volumetrics: tile 4, 64 steps, light clamp 20, froxel range per shot 40-140 m (dust only).
  - 3E engulf: big soft billows ride the tail wind into the lens + camera-glued lens_dust sheets (animated fbm
    alpha) that go fully opaque warm tan at CUT_OUT-12 -> guaranteed featureless T3 frames, no volume cocoon.
  - Car lights 90/40 -> 30/22 (3D white-out).
v3 result 3E (10:44, 30%/16spp): SKY IS BACK (bright mint, sun glow on the horizon) -> the black sky was the
  big volumes, not the world shader. Cliff strata read, dust plume soft + backlit, no checkerboard at 16 spp,
  f72 featureless tan. Problems: cliff joints read as a tiled polygon net; boulders = smooth orange blobs
  (they inherited world-space strata colour); far side of the canyon empty (mesas 40-100 m tall at <2 deg ->
  only one odd green dome visible); foreground gravel grey; billows made a flat wall from f60 (18 cut frames).
  3A-3D crashed: light_leak used gradient_type 'SPHERE' (5.2 enum is 'SPHERICAL') -> fixed, re-queued (v3b).
  Also in v3b: 3B mirror housing scaled x1.5 about its centre, toe-out 12 deg, camera just outside the flank
  focusing on the reflection (7 m); 3D reframed to hold bar (z .70) + exhaust (z .43), flames moved onto the
  real 4-in-a-row tips; airborne motes (3A/3D path specks, 3E drifting cloud); near-lens scrub/grass in 3E;
  anamorphic streak glare on highlights > 4.
v4 prep: mesas 110-250 m tall at 0.5-2.8 km (layered hazy silhouettes), thinner broken cliff joints, new
  object-space mat_boulder (per-instance hue, chipped cracks, dust on top), rustier gravel, sky a touch more
  saturated, 3E billows start 6 frames later with lower density/more structure, lens dust from f56.
v3b result (10:52): 3A readable (wheel + flank + lit cliff + mint sky) but dust plume barely visible, sun hidden
  behind the body (back=162 put it screen-left), crimson leak too big. -> v4: sun straight behind (back=180, 3.6 deg)
  at the vanishing point, trail density 1.5 / bigger radii, smaller leak.
  3B = unreadable blur: camera focused at 7 m but EEVEE DOF uses the depth buffer, so the reflection blurs WITH
  the glass. -> v4: driver's-window viewpoint (mirror glass faces the lens at frame left, reflects cliff + road
  behind), focus ON the glass, canopy hidden from camera, mirror x1.8, toe 8 deg.
  3C finally shows the winding road, strata terraces of the leaning cliff from above, boulders, car + red bar,
  but car tiny (70 m), dust trail faint, no visible long shadows (sky fill ~4x the grazing sun on flat ground).
  -> v4: camera 46 m, trail 1.6 density; GLOBAL: world lighting x0.6 via Light Path 'Is Camera Ray' (sky stays
  bright to the lens), sun x1.6 -> deeper shadows, grazing form, longer readable shadows.
v4 result (11:00): sky mint + cliff strata + car pass with red bar through the trail (3E f24) all read; 3A gets
  the sun at the vanishing point with the plume. Problems:
  - 3E near-lens scrub: sharp (20 mm f/4 hyperfocal ~3 m, no blur) and its leaf quads read as paper -> v5:
    grass + a dark boulder silhouette instead. Far mesas STILL invisible (haze 650 m -> ~90% haze colour) ->
    FarRock haze 1500 m with a darker teal haze base so they read as layered silhouettes.
  - Dust reads as smooth smoke blobs -> mat_dust2 noise contrast 1.3 -> 1.8, scale 1.8, detail 5, tighter soft band.
  - 3A: glittery sparkles = path motes streaking past the lens (too bright) -> strength 0.7 / fewer; hard-edged
    grey smear at frame bottom = EEVEE motion-blur clamp (32 px) -> motion_blur_max 128.
  - 3B: the mirror glass renders as a flat grey card (no reflection) -> planar probe diagnostic queued.
  - 3C: car readable at 46 m, long boulder shadows across the road now; but the camera rolled with the road so
    every bend looked straight -> near-fixed heading with a slow 10 deg drift; dust invisible from above (64
    exponential froxel slices over 0-140 m are ~3 m thick at 45 m) -> 3C froxels 25-75 m, distribution 0.3.
  - 3D (old framing): refractive heat sheet = opaque glowing white card, 90 W red glow floods frame, flames blown
    -> v5: sheet disabled, glow 22 W, flames 5x / lights 8 W, 50 mm 3/4 rear framing with the whole bar.
Mirror diagnostic (11:14, tests/3diag_m_grid.jpg): a PLANE light probe on a metallic roughness-0 quad DOES
  reflect objects behind the camera (SCREEN tracing; probe normal sign irrelevant; ray_tracing_method PROBE
  kills it). So v4's grey glass was a real reflection of the asphalt: the lens sat 13 cm above the glass and
  looked down into it. v5b: lens level with the glass, 6 cm outboard, 0.55 m back -> reflection looks straight
  back down the road. v5 also: rubble + scrub instanced on every up-facing cliff ledge (wall polygons with
  normal.z > 0.55), lower/wider 3E trail (rise 1.4 -> 0.6).
v5 result (11:18, tests/3_sheet_v5.jpg): 3B mirror now reflects the road + yellow centre line + terrain behind
  (works!) but a black octagon sits in the glass = the mirror's own stalk end-cap mirrored -> probe clip_start
  0.25. 3C bends now sweep through frame, ledge rubble breaks up the smooth strata, boulder shadows across the
  road; dust still thin -> density 2.2, radii 4/6/2.2. 3D f20 = the ref-like rear 3/4 (bar + fin + 4 flaming
  tips + wing, cliff bokeh) but f8 is fogged: the lens flies through every fresh puff 1.6 frames after it
  spawns -> only the LEFT tyre's plume, drifting left (dust_trail sides/spread params). 3E: far mesas finally
  visible but as pale flat-topped white BOXES -> mesa_mesh with per-angle eroded/stepped tops, steeper talus,
  stronger radial noise; darker teal haze base (0.30,0.46,0.47). Plume now has billow structure; car pass
  reads; engulf + T3 tan OK. 3A: road grit streaks + sun at VP; lens raised 0.30 -> 0.36 (smeared road block).
v6 (11:47-12:01, GPU queue ~8 min per still): 3D f8 now clear (left-tyre-only plume). 3B still had a black disc
  -> v7 hid all lens FX cards from probes/reflections (_lens_only) and reverted clip_start.
v7 = stills + MOTION (30 %, 8 spp, step 3) for all shots. NOTE: relative --outdir 'tests/<ID>_motion' resolves
  to C:\tests\ (Blender cwd) - frames copied into film/tests/<ID>_motion, sheets tests/<ID>_sheet_v7.jpg.
  3E motion: empty road f1-10, car blasts past f13-16 (red streak), recedes into its own trail, plume grows along
  the cliff and rolls at the lens, frame fully tan from f61 (cut 55) to the end -> billows 4 frames later +
  lens dust (58,0)(62,.3)(64.5,.7)(66,1) to keep more rolling plume before the T3 hold. Far buttes still pale
  boxes on the right -> lower (80-170 m), wider, 0.55 talus lean = hazy ridges.
  3B motion: reflection (road, yellow line, rubble, dust) steady, but a dark blob remains = our own rear flank
  straight behind the glass -> toe 8 -> 16 deg. 3C motion: bends sweep through frame, car centred, trail clumpy
  -> 3C dust contrast 1.5 / soft (.2,.7) / density 2.4. 3A motion: consistent, cliff streams past, leak pulses;
  a hard-edged grey smear persists bottom-left (near-road DOF + blur) -> f/4 and tilt up.
  Added a per-frame render timer (render_pre/post handlers, excludes GPU-lock waits).
v8 = full-res stills at the final default 32 spp for timing (queued 12:10).
v8 full-res @ 32 spp (12:11-): 3E f20 14.7 s (incl. shader compile), f52 9.1 s; 3B f16 16.7 s -> well under the
  30 s budget, so the final default is now 48 spp. 3E full-res reads like a film frame (car receding with red bar
  + motion blur, kicked-up dust, lit strata cliff with ledge rubble, scrub, posts with red reflectors, grass
  foreground; f52 backlit plume rolling down the road). Fixes after it: motes looked like white dead pixels
  (n 700->350, size/strength way down); rock joints/boulders read as turtle-shell polygon nets (thin broken
  cracks, weaker bump). 3B full-res: reflection now shows road + scrub + strata behind, but a black 12-gon =
  the pod's rear tip ring poking through the toed glass -> glass + probe pulled 3.5 cm rearward (v9).
  3D: flames rebuilt as soft additive emission (blue root -> orange -> transparent noisy tip).
v9 (12:35, 50 %/24 spp): 3B black blob GONE (glass pulled proud of the pod) - mirror shows road, scrub, strata
  behind; 3D soft flames OK; 3E plume ragged + ground-hugging, frame fully tan from ~f62 (cut 56) -> >= 16 tan cut
  frames for T3; 3C trail reads as a soft elongated plume. v10: dark coated bezel behind the glass (framed mirror).
FINAL COST (full HD, script default 48 spp, render-only, lock waits excluded):
  3B f16 20.5 s, 3D f14 21.4 s. At 32 spp: 3E 9.1-14.7 s, 3A 10.9 s, 3C 8.2 s -> est. 13-22 s at 48 spp. All <= 30 s.
Final command per shot: rb.py shots/act3_canyon.py -- --shot <ID> --anim --from 1 --to <render_frames>
Known issues left: 3A bottom-left near-road smear (DOF+vector blur, reduced not gone); 3B bezel is a plain flat
  frame; 3C cliff-top strata very saturated salmon, trail short; 3D flames still slightly cone-shaped; 3E a pale
  flat far ridge at the right frame edge; motion sheets (v7) predate the last 3E timing / 3B mirror fixes.

## Pass 3 (revision after director review 3.5/10) - 13:25
Review: 3F/3G/3H missing; 3E pass = silver shards (1-step blur, car read WHITE), engulf = static cream blob then a
2-frame pop to flat beige; 3D flames = white wedges + bulbs, salmon bar clipping, chessboard carbon; car glides
(constant 40 m/s, pitch 0, no steer); whole act pastel salmon afternoon (median luma .36-.51 vs refs .14-.26).
v11 changes (backups of the v10 files in notes/_canyon_v10_backup.py, notes/_act3_canyon_v10_backup.py):
  GLOBAL  SKY_LIGHT .6 -> .3, sun colour (1,.45,.22), strata ramp to rust/crimson/basalt (no peach stops),
          exposure -.3 on 3B/3C/3E, motion_blur_steps 4-6 on 3A/3E/3F/3G (3 on 3H), car paint patched in
          canyon.get_car (metallic .15, rough .15-.22 = black with crisp coat), carbon weave scale 260 + low contrast,
          rear bar deep crimson (1,.012,.004) at 14 (7 in 3D), motes non-emissive + sparse, light leaks removed from
          3A/3D (edl adds them), 3E rendered whoosh shake removed (edl adds one); boulders = noise-ridge fractures (no
          voronoi turtle shell), 7 facet planes; scrub = 12-18 x 1-2 cm leaves per tip; far mesas darker teal, jagged
          tops, welded seam, 45 deg sun exclusion + optional camera-cone exclusion (3E).
  DRIVE   canyon.drive: pitch from accel (squat/dive), road bump heave + pitch per axle, roll clamp .06, front
          hubs steer atan(WB*k) (+ counter-steer for drift slip), yaw_fn/lane_fn/lift_fn hooks;
          canyon.speed_curve: eased speed profiles (3A 34->46, 3C 40->30->40, 3E 50->56, 3F 38->22->30 ...).
  3E      pass at f13, camera 1.5 m from the flank, spring-driven whip-pan (aims back at the oncoming car, follows
          the pass, settles down-road); billows born in the near wake, cross the lens f56-64; wind 6 m/s; rust
          self-shadowed plume (emit .02, contrast 3.5); lens dust (60,0)(64,.5)(67,1) streaming along the wind.
  3D      flame cores r .02 x .10, no cap, rim-faded, 2 decaying bursts (f10-12, f17-18), lights 1.5 W.
  3F/3G/3H new (see shot functions); 3H uses lib/canyon_slot.py (own path, side-canyon gaps for low sun shafts,
          small local fog boxes only).
v11 result (13:56, 40%/16spp, tests/3_v11_sheetA/B.jpg): medians now .14-.31 (refs .14-.26), deep shadows, black car with
  crisp sun edges in 3A, rear 3/4 3D readable, 3F drift frame (tail out, red bar, blurred cliff) and 3G oncoming silhouette
  read like film frames. Problems -> v12: 3E fully tan already at f52 (billows born at 5-24 m reached the lens by f45) ->
  born 16-46 m, approach keyed late, trail skips 14 m before the lens, wind 4.5. Rock too saturated orange (sat .4-.7 vs
  refs .26-.40) -> crimson/maroon strata ramp. 3F gravel chips = huge black squares at the lens -> 5-16 mm, 70/frame,
  3 m lens exclusion, less growth. 3H no sky, murky fog, walls closing overhead -> walls 19 m with sun-side saddles,
  sun 13 deg, 14 mm aimed higher, fog .006, red glow 10 W. 3D 4 warm 'bulbs' = flame cones seen end-on.
v12 result (14:10): 3E motion (tests/3E_sheet_v12.jpg): approach f1-10, whip pass f13-16, receding red bar, plume grows and
  rolls in from f43, engulf f55; but frames 55-64 an identical orange glow and the lens-dust frames flicker between grey
  beige and orange: diag (notes/_act3_diag_lens.py) proved the sheet opacity keys are right -> the froxel in-scatter of the
  billow volume was painted over the 6-11 cm lens sheets -> 3E volumetric_start 0.3 m. Billows cross at f59-67, density .6.
  3D bar still salmon (245,90,65) at 3.5: AgX turns intense pure red salmon -> 1.0 (wides 4). 3H now reads as a slot
  (sky slit, chockstone, sunlit upper wall) but no beams -> deeper/wider saddles, uniform fog .011. 3C p5 .14 -> sky fill
  .15 for 3C only, sun 6.5.
v13 result (14:25-14:31): 3D PASS (0% clipped): deep red segmented bar at 1.0, small blue flame cores in the tips, no bulbs.
  3E motion (tests/3E_sheet_v13.jpg): plume now grows and rolls in f43-58, engulf f58-61, but the lens-dust frames still
  flicker orange (f67, f79-82): EEVEE's volume resolve uses the OPAQUE depth, so billow in-scatter is composited over
  BLENDED lens sheets whatever volumetric_start is -> lens dust render method DITHERED (writes depth) + billows fade out
  70-75 behind the full lens dust; lens colour (.95,.78,.60) x1.6 to sit closer to 4A's warm white (217,212,205).
  3F motion (tests/3F_sheet_v13.jpg): approach + broadside + tail-out drift with red bar read well (f13-21), but f27-47 =
  murky brown dust (sun was behind the camera: dust front-lit/dark) -> sun 38 deg off the drift view (back-lit), dust .45,
  life 70. 3C still low contrast/orange -> exposure -.75, trail density 1.3.
v14 result (14:39): 3E tail clean: f73-84 a single warm beige (205,196,187), luma std ~1, closer to 4A's (217,212,205);
  f67-70 still orange: with DITHERED sheets the remaining leak is the first froxel slab of the billows (camera inside
  them) -> billows fade 63->67, so the lens dust alone carries cut frames 67-78. Plume rolls in f43-58 with structure.
  3G motion: oncoming silhouette f1-10, car over the lens f13 (dark underbody), whip f16, but the receding car is a
  60 px speck -> crash zoom 16->45 mm f17-21. 3F: drift reads (tail out f19-22, red-lit dust) but f31-46 = brown murk with a
  red dot: the hairpin sits in the 486 m shadow of the far leg's cliff at a 4-deg sun, so the dust is never sun-lit ->
  dust .3 / life 50, fewer chips, push-in 24->50 mm f22-34 to keep the car readable. 3H sun moved ahead-left at 28 deg
  (back-lit shafts down the slot; slot walls hide the sun height).
v15 result (14:52-15:04, tests/3EGH_sheet_v15.jpg, tests/3FH_sheet_v15.jpg):
  3E T3: f67-84 one uniform warm beige (205,196,187), luma std 1.0 -> the last 12 cut frames (67-78) + handles are
  featureless dust; f55-64 inside the rust billows (orange glow), 3-frame change to beige f64-67. 3G: approach, over-lens,
  whip, crash zoom finds the receding car - but its rear read WHITE (sun straight behind the lens after the whip
  mirrored in the black paint) -> sun back 172 -> 138 (behind-right). 3H: sculpted slot walls, sky slit, chockstones,
  lit rims, red bar; no visible beams (sun direction change made little difference) - accepted as is. 3F: car now
  readable through the exit with the push-in, but the dust is a flat brown veil (never sun-lit in the cliff shadow)
  -> density .2, 25 chips/frame.
Final full-res timing stills queued 15:06 (tag _final11, script default 48 spp).
FINAL COST v15 (full HD, script default 48 spp, first frame of each process so it INCLUDES shader compilation;
  GPU-lock waits excluded): 3E f30 30.7 s (6 motion-blur steps), 3F f20 28.0 s, 3G f10 15.4 s, 3H f24 21.9 s.
  (v11 at 40% showed ~33 s of first-frame compile vs ~3 s/frame after, so steady-state cost is well below these.)
  Build times 4-35 s normally; 3E took 176 s once while 3 other acts were building/rendering (15 s unloaded).
  exposure_check (full HD): 3A/3D/3E/3F/3G PASS, 3H LOW CONTRAST (dark slot, p95-p5 .27; intentional mood).
Final command per shot: rb.py shots/act3_canyon.py -- --shot <ID> --anim --from 1 --to <render_frames>
  (3A 34, 3B 30, 3F 48, 3C 48, 3G 36, 3D 28, 3H 48, 3E 84) -> film/renders/<ID>/0001.png..
