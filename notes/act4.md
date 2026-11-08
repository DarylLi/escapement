# Act IV - THE SANCTUM: iteration log

Files: `shots/act4_temple.py` (cameras, shot set-ups, `--multi` mode), `lib/temple.py` (architecture
generators), `lib/tgeo.py` (numpy mesh kernel: lathe / sweep / surface / instancing / merged builder),
`lib/tmat.py` (materials, procedural sky with cumulus layer, cloud surface + volume shaders).

Design: original "clockwork temple" - layered gable roofs (teal glazed barrel-tile shader, vermilion
edge band, gold barge boards with gear-tooth flames and spiral horns), pediments that are giant clock
dials, white marble with ashlar joints, vermilion fluted columns with toothed gold capitals, spires made
of stacked rotating gear rings, armillary orrery (6 nested toothed rings on gimbals) on a drum.
Everything static is merged per material (thousands of instanced ornaments).

`--multi "4F:40,72;4B:10"` renders several shots in one Blender session (saves the GPU-lock queue).

## Iterations
- v1: first build (16 s build, ~1.4M verts merged). Render: EVERYTHING BLACK except emissive lanterns and the
  cloud-sea ambient emission; sky black. Cause: EEVEE (4.2+) world volumes are infinite -> a world fog
  of 0.0012/m swallows the whole sky AND the sun. Fix: no world volume; a bounded 1.4 km haze box instead.
  Also 445 s for the first 4F still at 30 %/8 spp = mostly shader compilation (~25 materials).
- v2 prep: shared one gold shader, gate gable crest removed (hero finial lives there), 4A flight re-aimed
  west so the low sun side-lights the cloud sea, cumulus towers on the horizon (4A/4B/4F), flower beds
  (red/white/gold accents), sun-lit dust motes (bokeh in macros), 4D glint light placed by mirror
  reflection about the roof normal so the highlight really sweeps across the glaze.
- v3 (all 6 shots in one session, 258 s incl. build 17 s): the temple finally reads - 4F through the
  gate arch (gold rosette coffers framing the hall) is a strong image. Problems: flat/overcast light,
  milky haze (0.0016/m too dense), physical sky pale grey-blue (and SUNCHECK showed no sun disc where
  expected -> sky/sun mismatch), motes rendered as snowflakes, lantern heads blown white, pediment
  vermilion reads pink, hall too small at 20 mm, 4B too far + plateau a flat green table + cloud sea
  like cotton wool, 4D horn occludes the centre, 4E sun orb = frosted light bulb, inside-cloud frames
  grey and too thin (plateau silhouette showing through in 4B f12).
  Per-still cost at 30 %/8 spp: 4F 35 s, 4B 17 s, macros 20-25 s, 4A 1.5 s (no temple geometry).
- v4 changes: art-directed gradient sky (deep zenith blue -> warm horizon, sun glow on the true sun
  direction) + cumulus layer; sun 7.5 warmer; haze 0.00055; gold brighter, lacquer deeper; lantern
  glass 3.0 orange; reflecting pool IOR 1.8 / near-mirror; cloud surface less translucent/emissive so
  domes get real side light; volumes 2x denser + warm emission (bright warm-white inside); 4F 22 mm,
  shift 0.15, ends over the pool head (y -72) for a bigger hall + reflection; 4B ends 170 m from the
  hall; plateau groves (150 mirrored trees); rosettes lighter (render cost); motes tiny and kept off
  the lens path.

## Session 2 (continuation after the standby crash)
- v4 rendered as a baseline (30 %/8 spp, all six shots ~2.5 min): blue sky finally there, but
  4A broken (flat lilac-grey inside the cloud; bright RECTANGLES = volume box faces: the old cloud volume's falloff
  never reached zero at the faces AND Principled Volume emission is not density-weighted, so the whole box glowed),
  4B = tiny model seen from straight above on cotton wool, 4E = light bulb, 4F hall = big flat pink-red
  pediments (no teal visible from the front), facade lit flat, motes = snow, grey lumps on the horizon (far peaks).
- v5 changes:
  * tmat: m_enamel (deep teal cloisonne), deeper/less pink lacquer, m_cloud_vol2 (ellipsoid falloff that is 0 before
    the box faces + emission multiplied by the density field), m_cloud_surface2 (bumped diffuse + translucency,
    sky-fill emission in shadow, forward-scatter silver lining toward the sun, camera-distance aerial haze,
    optional dithered soft silhouettes), world sun nodes named so the sun can be re-aimed per shot.
  * per-shot sun (SUNS table) + set_sun() (light, sky glow, cloud layer, cloud materials) + set_haze().
  * hall: stacked gables made narrow + steep (hw 10.5/7.6/5.2) so the teal hip slopes of the skirts read on both
    sides from the axis (ref composition); pediments teal enamel + gold, vermilion/gold rake bands with bead rows;
    front spires taller; inner cypress row 0.62x so the spires show; urns removed (blocked the reflection);
    gate passage walls get relief panels, windows, gold pilasters and a tooth frieze.
  * orrery heart replaces the bulb: enamel globe, toothed gold latitude bands, star studs, armillary meridians,
    flame-ray crown, polar finials; 4E camera inside the ring cage, rings 6x speed, focus pull.
  * 4C finial: 12 filigree curls, vermilion/teal cabochon collar in bezels, 16-petal flame crown, bead strings,
    48-tooth main ring with windows + bead rim, sun moved behind camera (deep blue sky, hall bokeh at right).
  * new lib/tclouds.py: vectorized cloud-sea heightfield (domes + fbm + bumps/holes), cauliflower towers,
    volume blobs, camera-invisible god-ray casters, a flapping bird flock.
  * 4A rebuilt: start cloud (emissive vol2 blob) -> exit ~f26 ~80 m above a golden cloud sea, flying toward the
    low sun with backlit towers on the horizon -> pitch down -> dive into a cloud head (vol2) by f70.
  * 4B rebuilt: starts inside the deck volume, oblique 20 mm descent from (-150,-350,300) to (-26,-122,46) toward the
    complex (spires rising toward camera), wisps + sunlit puffs for parallax, side sun from the west with shadow
    casters for shafts, denser haze, flock of white birds as a scale cue.
- v6 (30 %/8 spp): 4F final frame now reads as the ref composition (teal enamel pediments, gold clock, teal skirt
  slopes both sides, tall gear spires, cypress frame) but the mist veil washed it out, and the POOL is a uniform
  pale slab (no reflection at all - the planar probe seems to give nothing; testing SSR only). 4B f72 strong
  (gate spires rising toward the lens, hall + orrery behind) but f8 should be inside the deck and is not; cloud sea
  reads as tan sand dunes; towers = stacked snowballs; no visible god rays (shadow casters gave no shafts).
  4A: the deck mesh rose ABOVE the flight path (heads up to z 428 with the camera at 425) -> grey wall in f10/f56.
  4C: pinion face-on -> blown glare disc; flat front light. 4E: heart rays read as a spiked sea mine. 4D: tile
  highlights = perfectly regular LED grid.
  Debug (shots/act4_voltest.py): camera deep inside a vol2 box DOES render (white) -> 4B issue is elsewhere.
- v7 changes: 4A deck clamped ~90 m under the path (dive head allowed), sun to the side (az 22, el 9) for lit/shadow
  contrast, two nearer towers; towers = core spheres + 3x surface bulges with R-relative 2-octave displacement;
  cloud albedo near-white (warmth now only from the sun), lavender shadows, low-freq bump; temple sea gets
  cauliflower bulges + 5 big towers 0.7-1.3 km out; 4B fake god rays = emissive volume shafts along the light
  direction (tclouds.beam_material/light_beams); mist 0.0035 -> 0.0013; planar probe off (A/B); 4C sun from the
  side, pinion turned edge-on; 4E flat halo of blades + wavy flames on a toothed ring; 4D per-tile jitter
  (roll/pitch/lift), vermilion border tiles, gold gear antefixes, softer glint, 65 mm f/2.
- Reflection test (shots/act4_refltest.py): water + red pillar -> SSR alone reflects correctly; adding a PLANE light probe REMOVES the reflection entirely. Planar probe disabled for good.
- BUG found (since v3): cam_path + common.shake(): shake keys the current value at frame_start, which after cam_path was the LAST key's pose -> f1 key overwritten -> every shaken camera (4A, 4B, 4C, 4E) started at its END position and swung back. This is why 4A f10 / 4B f8 were not inside the clouds. Fix: frame_set(first key) at the end of cam_path.
- v7 results: 4A f40 finally a cloudscape (cauliflower towers side-lit, blue sky) but cool/white - the warm sun
  washes to white through AgX; 4B f72 big cumulus towers behind the temple = real scale; 4F: towers behind the
  hall are gorgeous, mist now subtle; POOL STILL has no reflection even without the planar probe (investigating
  with dbg_refl2: volumes / clip_end / DOF variants); 4C side light gives the gold form, cabochon collar reads;
  4D vermilion border tiles + jitter work, highlights still dotty; 4E halo-of-blades sun reads as a proper orrery
  heart.
- v8 changes: suns more saturated + sky fill lower (4A el 8 / (1,.52,.22) / sky .6; 4B (1,.56,.27) / .6; 4F
  (1,.6,.32) / .65), 4A sky cloud layer cover .08 (was speckled), fewer/lower 4A wisps, 11 rock pinnacles rising
  from the cloud sea around the plateau, bells under all skirt eaves, broader tile highlights (roughness .06-.3).
- ROOT CAUSE of the dead pool (and soft/pillowy architecture since v1): Blender 5.2 has Mesh.set_sharp_from_angle, NOT set_sharpness_by_angle -> tgeo.MB.build's try/except fallback smoothed every face with no sharp edges (corner normals of a box = +-0.577). Test dbg_refl4: MB-built water box = domed pillow, no reflection; plain plane = mirror. Fixed in tgeo (set_sharp_from_angle). NOTE for the director: lib/common.py shade() has the same dead call + all-smooth fallback (affects every act's prim/mesh_obj/make_gear).
- v9 (sharp normals fixed): everything crisp, POOL REFLECTS the hall (4F f30/f72), tiles in 4D now show proper
  streak highlights along each barrel tile, gold edges catch light. 4B f30 showed a dark mirrored 'ghost' of the
  island in the cloud sea = EEVEE screen-traced Translucent BSDF -> translucency removed from cloud surfaces.
  Pinnacles (v8) read as factory chimneys -> removed; cloud sea raised to z0=-52 so the island sits IN the sea.
- v10 4A: sun behind-left (az -40) gives peach-gold lit faces on the towers (finally golden); deck still read as a
  pink-brown carpet (fine bump at grazing angles + dim grazing sun).
- v11: cloud materials get a wrapped N.L sun-tinted glow (fake multiple scattering, keeps the sea bright under a
  grazing sun) + much lower bump; dive volume smaller/less emissive and moved onto the f60-f72 path; 4F end camera
  now at the pool head, 1.9 m over the water, lens 21->26 mm animated (more mirror in frame, hall same size).
- v12/v13: 4A golden cloud sea reads (peach-lit tops, lavender shadows, towers, blue sky); the dark lobe under the
  island in 4B was the island's own SHADOW on the cloud sea (sun from WNW threw it toward camera) -> 4B sun moved
  to the SW (az 42, el 16): front-lit temple, shadow falls behind the island; fast GI off in 4A/4B anyway.
- Motion sheets (tests/4F_sheet.jpg, 4E_sheet.jpg, 4C_sheet.jpg, 4D_sheet.jpg): 4F glides gate -> arch -> pool
  head, decelerates, static from f61 (photo frame); 4E rings + planets sweep past the camera; 4C slow orbit with the
  gear ring turning and the hall bokeh sliding in; 4D the glint band sweeps left->right across the glaze.
- v14 4A: start cloud moved/denser core (shape_k 3) -> white through f22, open sea from ~f24 (T3: cut frames 1-12 =
  local 7-18 pure cloud), ~30 frames of golden cloud sea before the dive, white again from ~f63.
- Motion sheets 4A/4B (tests/4A_sheet.jpg, 4B_sheet.jpg): 4A white -> emerge -> glide -> pitch/dive -> white;
  4B white (f1-13) -> punch through ~f17 -> island in the cloud sea with shafts -> accelerating descent onto the
  gate spires.
- Full-res cost, 2nd frame of a pair (32 spp, before tuning, other agents' CPU builds running): 4F 57 s, 4C 54 s,
  4D 78 s, 4B ~100 s (tile 4 / 96 vol samples), 4A ~15 s. Too slow -> final defaults now 24 spp, 1 shadow ray /
  6 steps, volumes tile 8 / 48-64 samples everywhere (4B was tile 4 / 96); re-measuring (tests/*_full3*).
- Full-res stills: tests/4F_full_f0072.jpg (the T4 photo frame), 4B_full_f0060, 4A_full_f0046, 4C/4D/4E_full_f0014.
- Hero finial horn curls now 20-sided / 64 steps (faceting visible at 85 mm full res).
- Debug helper scripts (no render output used by the film): shots/act4_voltest.py, act4_refltest.py, act4_apitest.py.
- FINAL budget (full res, 2nd frame of a pair, measured under GPU contention): 4F 31 s (20 spp, courtyard mist only -
  haze box off in 4F; was 56 s), 4B 37 s (24 spp, volumes tile 8 / 64; was ~100-130 s), 4D 47 s (24 spp + sphere
  probe), 4C ~54 s and 4E ~40 s measured at 32 spp (now 24 -> est. 35-40 s), 4A ~15 s. Script defaults = final.
- Final render: rb.py shots/act4_temple.py -- --shot <ID> --anim --from 1 --to <render_frames>  (4A/4B/4F 72/72/78,
  4C/4D/4E 28). 4F's last frame (static f61-78) is the T4 photo (see tests/4F_full4_f0072.jpg).
- Known/open: 4A towers still a bit 'stacked cauliflower', exit from the start cloud is quick (f22->f26);
  4B shows a short cliff band on the right of the island; 4F cumulus towers slightly marshmallow-smooth; sun
  direction is cheated per shot (dream logic) - 4B/4F from the SW, 4A behind-left, 4C from the side.

## Session 3 - revision pass after the director's review (score 5/10)
Director QC: every key still failed exposure_check (WASHED OUT p5 0.15-0.40, 4A/4B overexposed), T3 a flat beige
fade, 33 of the first 120 cut frames textureless white, 4F front-lit/flat with clipped lanterns, 4D glint zebra,
emissive motes, macros off the img_gears look, 4B toy island, plank god ray, marshmallow towers.
- r1 (all high-impact fixes in one pass):
  * exposure: sky fill halved (SUNS[4] 0.55-0.7 -> 0.3-0.35), sun +20%; cloud surfaces emit 0.1-0.15 -> 0.03,
    wrap 0.35-0.55 -> 0.25, shadow colour (0.10,0.12,0.30), bump 0.45 -> 0.1 (sea), darker aerial haze, new
    base_dark height gradient (flat dark bases) in tmat.m_cloud_surface2.
  * 4F: sun rakes the facade from the left (el 10.5, az 80, (1,.55,.28)), glow .45; lantern glass strength 3 -> 0.7
    amber (1,.42,.12) + 12 dark bronze mullions/2 rings per head; pool lanterns 4 m -> 8 m spacing, avenue 7 -> 10.5 m;
    camera now starts at y -112 looking up at the gate roofs/spires (tilts down), linear start (VECTOR handle),
    fast passage, eases into the pool head by f55, hold f55-78 (lens 20 -> 22.5 -> 26).
  * gate + hall: relief panels = teal enamel tile panels in gold frames with gold muntins + a rosette per cell (were
    red pegboards); hall door = vermilion leaves studded with gold rosettes; column gear rings at base and capital +
    bead collar; pediment ornament = rosettes at 3 scales on radial lines from the clock + gold spokes (was an even
    polka-dot grid); 4F towers moved to (+-1500, 2600) symmetric, clear of the hall silhouette.
  * motes: emissive T_Mote (660 icospheres) -> non-emissive principled, 18 for 4C + 18 for 4D only, near the lens.
  * 4D: glint light 16000 W -> 4500 W, 5 x 0.5 m, amber (1,.7,.4), sweep +-8 m; hero roof = alternating concave pan
    rows (low, wide) and raised convex cover rows (+0.09 m) -> dark grooves between rows.
  * 4C: backlit (sun az 122 el 9), 85 mm f/1.4, 28 deg orbit + push-in 3.9 -> 3.2 m, rack focus 1.05 m (foreground
    ring) -> 3.45 m (collar) over f7-f15; camera-held dark toothed ring arc in the lower-left (Occl4C); spindle + hub
    boss under the top gear, bracket arm + axle + boss for the pinion; ring speed 2.5x -> 1.2x.
  * 4E: backlit (az 172 el 30), 50 mm f/1.4, focus on the globe bands, camera-held shadowed meridian strap (Occl4E);
    halo blades halved, curling flame blades long/short alternating; latitude band teeth 2.5x finer at half height.
  * 4A: VolA emit 0.8 -> 0.3, noise_k 3, emission colour keyed (0.85,.72,.6)@f1 -> (1,.9,.8)@f18 (3E dust hue);
    VolStart moved/shrunk (centre +467, 340 m) for a gradual exit; VolDive emit .45 -> .2, moved 15 m further; glide
    corridor clamp + 6 tall bumps -> cloud heads 25-40 m under the lens; 4 small towers + 3 dense wisps (0.08)
    15-35 m beside the path; 7 deg bank f26-f50 (bake_roll: per-frame re-key incl. shake); COVER 0 (no sky specks).
  * 4B: camera lower/closer earlier (f12 z 226, f30 z 148), Deck4B emit .4 -> .15, bottom raised (white only to
    ~f10), 3 torn sheets (0.08) on the path f12-f19; sea z0 -52 -> -34 + a third rim collar (r 192) to bury the cliff;
    8 outer gear spires + 4 pavilions on the avenue; beams gaussian cross-section, long end fades, 1.5x wider, strength
    0.014 -> 0.006.
- r1 results: 4F hold went dark navy - az 80 put the whole facade in shadow (no stripes, no gold light) -> az 62 /
  el 12 / 7.2 (r2: golden raking light, column shadows on the wall, amber lanterns no longer clip, exposure PASS
  p5 0.10 p50 0.29). 4C backlit gold = real metal, rack focus works, but the foreground ring was LIT gold (olive smear)
  -> dark aged-gold material (T_GoldDark) for both occluders; camera raised level with the collar. 4D grooves read,
  but every cover-tile crest carried a white line -> light 4500 -> 1600 W, tile coat 1.0 -> 0.6 and coat roughness
  0.02-0.09 -> 0.1-0.22, base roughness 0.16-0.38, 4D motes moved inside 1.6 m of the lens (soft discs only).
  4E: bright sky behind -> camera moved ABOVE the heart looking down (background = shadowed roofs/lawn).
  4B: island read as a pond in snow from above -> targets pushed forward so the horizon/towers enter the top of frame.
  4A (r1/r2): front light = flat tan 'sand'; sun moved to the side (az 25, el 8) -> lit gold faces / violet shadow
  sides, warm glow top-left; p5 still 0.25 (navy sky + lit shadows) -> per-shot exposure trim EXPO 4A -0.6 / 4B -0.5
  and 4A sky fill 0.22. Fractal towers (tclouds.towers: lobes -> children -> grandchildren, flat bases) read as
  sponge/coral when backlit -> 2 children (0.36-0.52) + 1 grandchild each, and the dithered 'soft' rim now only
  frays the outermost silhouette (facing 0.62-0.96; it punched holes into the small bulges).
  4A start cloud: density 0.045/scale 14 (r3) averaged out to a flat card again -> back to 0.09/scale 9 (r2 gave a
  dark pocket at f12 and a gradual exit f16-f24). Emission AND albedo keyed from 3E's tan (0.85,.66,.5) to warm
  white by f18.
- Blob trees: ico sub 2 -> 3 + a finer leafy displacement octave (faceted icospheres in 4B/4F).
- r2/r3 exposure_check: 4F f72 PASS (p5 0.10, p50 0.29, colourful 43), 4B f44 PASS (p5 0.12), 4E PASS (p5 0.04),
  4C 0.10 / 4D 0.11 (pass --day 0.15; strict 0.08 nearly) -> 4D EXPO -0.15 + cavity AO (dist 0.15, near-black grooves),
  4B f26 still median 0.63 -> EXPO 4B -0.8 and sea albedo 0.96 -> 0.86. 4A glide p5 0.19-0.20 (navy sky is the p5).
- 4C r3: orbit re-centred on the hall axis (view 105 -> 80 deg): the blurred hall gable + spire now sit behind the
  finial in cool haze, dark toothed ring blur lower-left = the img_gears read. Motes off in 4C (backlit principled
  motes rendered as dark specks); 4D keeps 8 soft out-of-focus discs.
- 4B r2 f60: horizon + fractal cumulus towers at the top of frame, compound fills the frame, long golden shadows = scale.
  Rim collar lowered (26/36/40 m) - it read as a crater wall; 7 low vapour sheets (vol2 0.035) along the rim so the
  island edge reads as vapour instead of a hole in snow.
- BUG (r1/r2): the 4F hold fix set CONSTANT on the 2nd-to-last key of EVERY curve - the lens curve has only 3 keys,
  so the lens froze at 22.5 mm from f30 and popped to 26 mm at f55. Now only location/rotation (4 keys, f55) get it.
- Full-res stills at final samples (4F 20 spp, others 24; tests/*_full_r_*): 4F f72 = the T4 photo frame, 4B f22,
  4C/4D/4E f14. Wall-clock per frame (2nd of a pair, includes GPU-lock waits; 3 other acts were building/rendering
  at the same time, CPU at 100%): 4F 87 s, 4B 77 s, 4D ~80-200 s, 4E 129 s, 4C 124 s. These are 2-3x the previous
  session's numbers for the same samples, so most of it is contention, but the scene also got heavier: fractal towers
  +0.4M verts, trees sub 3 (+0.8M verts), 8 spires + 4 pavilions. Trees went back to sub 2 for budget.
- Orrery heart meridians: 72 coarse block teeth -> 160 fine teeth at half the height (4E full-res read as Lego).
- Motion sheets (30 %, 6 spp, step 3): tests/4F_sheet_r.jpg - starts outside the gate with its roofs/spires in frame,
  already moving on f1, through the teal-panelled passage f10-f25, glides to the pool head, static f55-f78 (lens no
  longer pops). tests/4A_sheet_r.jpg - cloud f1-f10, dark pocket f13, opening f16, clear f22, glide with near towers /
  wisps and the bank f26-f50, dive f55+. The dive skimmed the deck MESH before the dive volume closed (tan streaks,
  flat tan f64-f70) -> VolDive back near its original spot (-88, 334), taller (150 m), emit 0.3.
- Motion sheets: tests/4C_sheet_r.jpg - f1-f7 the dark foreground gear teeth are sharp, rack f8-f14 onto the collar,
  orbit slides the hazy hall gable + spire behind (the img_gears grammar). tests/4E_sheet_r.jpg - orrery rings and
  the strap sweep through the defocused foreground while the globe bands hold focus. tests/4B_sheet_r.jpg - white
  f1-f7, the island glimpsed through the deck at f10, the tear sheets close in f13-f16 (layered punch-through, not a
  pop), clear from f19, island grows, rim vapour softens the edge, horizon towers enter at the top.
- tmat.m_terrain: two large-scale meadow octaves (dry ochre drifts, dark clover) - the plateau lawn was a flat
  uniform green from 4B altitude.

## Session 4 - CLOUDFIX (4A second half + 4B): the cloud deck read as BEIGE SAND DUNES
Diagnosis (renders/4B/0020-0056, out/check_2A_4B.jpg): tclouds.cloud_field = wide flat domes (h/r 0.25-0.5) + smooth
fbm ridges on a 360x150 polar grid (5-17 m cells at the island, 50+ m further out) -> no puff ever resolved; diffuse
BSDF lit by a 0.6 deg sun -> hard self-shadows + the camera-invisible god-ray casters threw crisp blue blobs on it;
lit areas ran into the compositor shoulder and AgX desaturated them to beige; the deck met the cliffs in a hard line.
New module lib/tbillow.py (backups of the pre-fix files in notes/_cloudfix_backup/):
- billow_field: square-celled LOG-polar grid (1024 x ~630 = 643k verts for 4B, 1.6-1.9 m cells at the island; 4A
  1080 x 1052 = 1.1M verts, centred on the glide path), max-union of ROUND domes at three scales: heads (r 28-110 m
  x (1 + r/1800), h/r 0.28-0.5) -> puffs 0.2-0.4x riding on the current surface -> small puffs 0.07-0.15x (within
  1.1 km) = cauliflower crevices; base layer 6 m with only +-6 m undulation (no dune ridges); a large-scale gap mask
  (thr 0.62 of a 1.4 km fbm, >600 m from the island) drops the base below z0 so a few real gaps open to the ground;
  taper (0.55x relief at r 200 -> 1x at 520 m) keeps the heads from hiding the island; baked POINT attributes:
  'occ' (2-scale cavity from box-blurred height) and 'shd' (soft heightfield sun shadow marched toward the sun, 10
  steps, penumbra 0.35 d, max 80 %).
- m_cloud_deck3: emission-only shading (no EEVEE hard shadows on the clouds): Voronoi-dome bump (9 m + 3.2 m cells,
  faded with distance) -> wrapped N.L (node CloudSunN, re-aimed by set_sun) x shd, warm-white tops -> gold toward the
  terminator, sky-blue fill x occ, darker lanes, forward-scatter gold rim toward the sun (CloudSunDot), aerial haze;
  alpha (DITHERED): soft silhouettes, h < 0 lanes/gaps fade out with noise, ragged noisy fade over the last 4-75 m to
  the island cliff edge (plateau edge function) = no more hard cut-out hole.
- far_ground (emission landscape 1.3-1.4 km below, heavy haze) seen through the gaps; wisp_cards (10 thin stratus
  veils over the 4B deck, streaky noise alpha <= 0.32, drifting 7 m over the shot); rim vapour volumes moved INTO the
  breach (z -16, 200x160x40, density 0.06, lit) so the cliff contact is misty.
- 4B: Billow4B replaces CloudSea in 4B only (shot_setup hides CloudSea, swaps CumulusT's material to T_BillowTow4B
  for 4B and back to T_CloudTow otherwise; 4C-4F unchanged); Puffs4B use T_BillowTow4B. 4A: Deck4A = billow_field
  with the same bumps/clamp; towers T_BillowTow4A. Cameras, animation, island, temple untouched.
- v1/v2 (4B+4A multi / 4B): render HUNG at render start (lock held, 0 CPU, 0 GPU, ~10 GB private) -> killed.
  Diagnostic tests/_cfx_diag.py (deck, deck3 opaque/alpha, ground, wisps alone) all render fine; the v2/v3 tower
  twin (shared mesh + OBJECT material slot) removed anyway. v4 4B hung again AND froze the concurrent 4C FINAL
  (frames stopped at 20:25 renders/4C/0017.png): two heavy act-IV EEVEE renders at once deadlock this iGPU (780M,
  shared memory). Tests of 4B must not overlap a heavy final.
- v3 4A (tests/4A_cloudfix_v3_f0036/44/54): reads as a real cloud sea (billowy puffs, blue shadow sides) but grey/cool
  and p5 0.16 (WASHED OUT): self-shadow at el 8 deg too strong + fill too high -> v4/v5: softer/partial baked shadow
  (floor 0.3), sun 3.0-3.1 warmer (4A (1,.85,.66)), fill 0.26-0.3, deeper cavities (occ floor 0.06, direct x 0.4-1),
  fine bump halved (read as grainy foam close up).
