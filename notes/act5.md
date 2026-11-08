# Act V - THE DESK: iteration log

Files: shots/act5_desk.py (scene + 3 cameras; `--shot` accepts a comma list), lib/desk.py (materials + props),
lib/desk_tex.py (numpy texture generator: cutting mat, blueprints, sketches, photo placeholder; run with
Blender's python outside Blender), shots/act5_carlines.py (renders lib/car.py normals -> edge-detected line
art -> tex/act5_bp_car.png + tex/act5_sk_car.png).
Photo texture constant: desk.PHOTO = renders/photo_temple.png (falls back to tex/act5_photo_placeholder.png).
Scale: real metres, desk top z=0. Pocket watch 50 mm case, pencils 7.4 mm hex.

## v0 - textures (numpy)
- Mat/blueprint/sketch generators written; single-stroke technical font (ISO-ish) for all lettering.
- Sketch sheet: gear stack drawn off-sheet (projection offset wrong) -> moved origin; coffee ring inner
  fill read as a flat disc -> reduced to a faint tint.

## v1 - first full build (build 102 s, first still +4 min shader compile, 452 s total)
- 5A f8: photo fills frame correctly (T4 ok) BUT loupe brass frame + a pencil intrude at the frame edges
  -> photo moved to (-0.088, 0.066), mech pencil moved away; pencils no longer pass under the print.
- 5A end: reads as a dark tabletop with lamp at top - promising - but: photo too small (no focal subject),
  sheets washed out (sheen + high albedo under the lamp), mat grid invisible at frame scale, fog 0.3 too
  milky (no deep blacks), motes = too many sharp white specks ("snow").
  -> end camera low + close (photo in lower third, lamp practical in top of frame), lamp moved behind the
  work to backlight the desk; paper albedo 0.72, no sheen; mat lines 3.4/5 px; fog 0.11; 650 tiny motes.
- 5B: totally unreadable - real-scale macro DOF at f/2 = everything is mush. -> f/13, focus 6 cm.
- 5C: movement under the crystal is pitch black: the refractive crystal casts an opaque shadow
  -> crystal + loupe lens visible_shadow=False. Hunter lid seen edge-on reads as a stick
  -> lid pivot moved to the far side (world ~10 deg) so the open lid faces the approach as a backdrop
  (inner face = guilloche perlage).
- Perf: 180 knurl boxes, 60 indices, 40 crown knurls joined into 4 meshes; pencils share one paint shader
  (object colour) to cut shader compile time.

## v2 (build 79 s, 177 s total incl. 12 stills when the GPU was not shared)
- 5A end now works: photo is the focal subject with a glossy lamp sheen, mat grid reads, lamp practical
  glows in the background, out-of-focus pencils in the foreground. Problems: f8 still has a dark wedge in
  the lower-left = curled corner of the car blueprint poking through the print -> bp_car curl 0.8 mm, print
  raised to z 4.6 mm. Linen tester reads as a wire cube ("programmer art") -> solid side plates + top
  plate. Eraser = grey box -> printed paper sleeve. A hard white streak on the back of the desk was the
  CoolRim area light grazing the desk -> moved up/back. Moonlight invisible -> 4.5 W/m2.
- 5B readable now (f/13): blueprint lines rushing under the lens, pencils as dark logs, loupe frame, watch
  + lid at the end. Far too dark at macro height -> per-shot exposure (+0.9 EV for 5B, +0.5 for 5C).
- 5C: lid now a gold backdrop behind the watch (good), skeleton dial + blued hands read. Lid face plain
  -> engine-turned guilloche shader. Perlage too flat -> stronger. Watch interior dim -> small warm
  "lamp bounce" area light over the watch.
- 5C dive end = total mush: EEVEE thin-lens CoC ~ f/|s-f| blows up when focus distance s crosses the
  focal length (28 mm) - inevitable on a real-scale dive. Also the dive only finished at f48 but the cut
  is at f42. -> dive retimed f18-40 (smootherstep, crosses s~f in ~3 frames), f-stop driven by |s-f|
  (f/22 near the singularity, f/10 at the end), creep f40-48 on the teeth; end camera below the crystal.
- Red-pencil markup layer (circles, arrow, "CHECK DROP") added to the watch blueprint.

## v3
(previous session died before rendering v3; v3 = its post-v2 edits rendered by the continuation session, 10:15)
- v3 stills (40%, 12 spp, build 28 s, 50 s total for 11 stills when the GPU is free):
  5A end: composition works but the lamp is a blown face-on disc dead centre-top, all-warm (no moonlight read),
  back wall shows a regular dot grid (volumetric froxel aliasing, vol tile 8 at low res).
  5B: f14 blueprint lines rushing = good; f34 mush (camera at 6.5 mm between two pencils, 1-2 cm from
  everything at f/13 FF-equiv); f50 loupe = murky box; f70 watch on blueprint = good.
  5C: f12 good (lid guilloche reads), but crystal reflection = milky veil over the movement; f26 soft; f36 a
  tan blur (camera passes through the crystal + CoC singularity again); f44 teeth read but washed-out sepia.

## v4 (continuation session)
- Lamp moved high over the work (head 0.36 m), pointing almost straight down: shade seen from the side, light
  cone in the haze, never the bulb face-on. 46 W (was 16 W at 0.2 m). Moon 9 W/m2, bluer, volume 1.4.
- vol tile 8 -> 4 (froxel grid).
- "Small-sensor macro" cameras: cam_obj(sensor=...) keeps the FOV with a proportionally shorter lens, so EEVEE's
  CoC ~ f/(s-f) never explodes at mm focus distances. 5C: 4 mm sensor, f-stop solved per frame for a constant
  background blur (macro_fstop). 5B: 8 mm sensor, f/3.2, focus 4.5 cm.
- 5C dive rebuilt: crash-in curve (1-(1-u)^3.2) f16-38 to a point under the crystal above the centre wheel,
  looking 32 deg down at the centre-wheel/third-wheel mesh; creep f38-48. Crystal hide_render keyed the frame the
  lens gets within 2.5 mm of the glass. Crystal Specular IOR Level 0.3 (AR coated). Exposure ramps +0.35 -> -0.25.
  Cool low kicker on the watch (blue edges on brass), warm fill reduced.
- 5B: low points of the pencil slalom raised 6.5 -> 8.8-9.8 mm.
- !! v4 first attempt deadlocked the whole render farm for 6 min: our Blender sat idle holding .blender.lock with
  its own pid ("[gpu] waiting for GPU lock" from itself). Cause: Windows race in tools/gpu_guard.py release() -
  os.remove fails while another agent's guard has the lock file open for reading; the exception is swallowed,
  _held is reset, the file stays -> next acquire() waits on itself forever. Killed it; added
  desk_more.install_lock_fix(): before render_init/render_pre (when the guard does not hold the lock) and after
  render_post/complete/cancel, a lock file naming our own pid is stale -> delete it with retries. (Director: other
  acts can hit the same deadlock; the guard itself should retry the remove.)
- Walnut rebuilt as glued-up planks (12.5 cm boards, glue seams, per-board tone, fine straight grain) - the old
  large wavy bands read as zebra stripes. Moon re-aimed (0.80, 0.36, -0.48) so the window patch lands on the back
  wall behind the work. Background props: book stack (cloth covers, page edges, gilt bands), pencil cup with
  6 standing pencils + steel rule, watchmaker's parts tray (12 compartments, ~180 instanced screws/wheels/jewels).
  140 more loose parts in a corridor along the 5B path. Motes now keep 3 cm clear of the 5B/5C camera paths and
  9.5 cm around the photo's vertical axis (a mote 2 mm from the lens = giant disc in 5B f14; specks over T4).
- Car blueprint regenerated: faint 5/25 mm drafting grid (lines rushing under the lens anywhere), station numbers +
  sill hatching, DETAIL A wheel/hub section, notes block, overlapping 4470/2660 dims fixed.
- Photo fallback = newest tests/4F_*f0072.jpg (real 4F hold frame) until renders/photo_temple.png exists.
- 5C: local haze volume (density 38/m, cool) + 90 glowing specks inside the case, keyed visible from the frame
  the crystal drops out (img_gears haze/specks look for the dive end).
- v4 results (10:38, after ~10 min in the GPU queue): 5A end now reads as a real desk - planks, book stack + pencil
  cup in the background, the 4F temple frame on the print, no lamp disc. Still: background wall black (wall albedo
  was ~5 %, so the moon patch never showed), f8 T4 frame veiled (lamp glint in the coat + bloom on the 1.15
  emission boost). 5B: corridor parts work as speed cues; f14 big blurred disc in lower right = a loose gear lying
  right under the lens; everything soft at f/3.2. 5C: f12 good (crystal veil gone); f26 mush (60 % of the dive
  distance in 5 frames); f32/38 a giant lilac blob = the blued minute hand 0.7 mm under the lens; f46 teeth ring
  over perlage reads as clockwork but all one brown (gold plate under brass wheels).
## v5
- T4: print shader = mix(lit glossy print, pure 1.08 emission of the image) driven by PhotoBoost (1 -> 0 over
  f9-15) -> no glint/veil/bloom on the handoff frame. Boost keys applied per shot (apply_shot_state).
- Walls 17 % albedo (blue-grey plaster) + masonite pegboard with a hole grid: the moon patch / window light can
  read behind the work.
- 5B f/5 (was 3.2) + rack focus along the run (4 cm lines -> 2.8 cm pencil tips -> 5 cm loupe -> watch distance);
  loose parts kept 9 mm clear of the path centre line; nose tips up toward the lens approaching the loupe.
- 5C: hands at 10:50 (out of the dive line); plate + bridges rhodium (cool) vs brass wheels (warm), perlage spots
  0.6 mm (were 1.1 mm "targets"); dive f14-38 = smootherstep(u^1.25) (accelerate, brake on the teeth); shutter 0.3
  for 5C (0.45 5B, 0.5 5A). Inner haze + specks now built (were added after the v4 launch).
- Part sources baked (apply_mods) before instancing -> ~500 instances no longer each evaluate a Bevel modifier.
- Pencils: gold-foil stamped lettering ("ESCAPEMENT No.2 HB ...", tex/act5_pencil_foil.png from desk_tex 'foil')
  on the up-facing hex face.
- v5 results (10:58): 5C end finally has the img_gears look - dark rhodium perlage plate, brass wheel teeth catching
  the lamp, deep blacks, bokeh; out-of-focus centre arbor = vertical foreground streak (kept). 5C f30 still a
  1-frame whoosh blur. 5B readable but soft (motion blur at shutter 0.45, 1 cm from things). Moon STILL absent and
  the same big blurred disc in 5B f8-16 (not a mote, not a loose part).
- Build time: crumbs+dust section had grown to 126 s (5000 dust cubes via per-cube bmesh ops) -> numpy
  fast_cubes(): whole build now ~12 s on a free CPU.
- Probe (ray casts toward the sun, no render): every moon ray from the back wall hit the 'Sky' backdrop box
  outside the window - visible_shadow=False is not enough here. No shot looks out of the window -> Sky
  hide_render. --probe2 prints what the 5B camera sees in the lower right at f8/12/16.
## v6
- Sky backdrop removed (moon unblocked). T4: world fog density keyed 0 on f1-9 -> 0.11 at f17 (5A only) - the
  froxel grid + lamp in-scatter were veiling the handoff frame. Crystal Specular IOR Level 0.15.
- 5B shutter 0.25 (sharper detail, speed from the parallax), exposure +0.35 (was +0.6: lavender, washed blueprint).
- 5C dive f-stop solved for 1.1 % blur f23-34 (less whoosh mush), exposure ramp ends -0.15.
- v6 results (11:13, 240 s for 10 stills + 62 motion frames): T4 frame clean (pure image, no veil). Motion sheets:
  5A hold f1-9, whip f9-16 with roll + speed ramp, then a near-static 30-frame hold; 5B reads end to end (lines +
  parts rushing, shavings, green/black pencil walls, through the loupe frame, out to the watch); 5C rise -> dive ->
  gear ring, but the crystal still laid a milky veil over the movement f10-22 and the end barely moves.
  Moon STILL invisible with the backdrop gone. 5B disc: --probe2 showed the lower right hits 'CuttingMat' through
  the blueprint -> the sheet's +-0.6 mm undulation dipped it under the mat (z 0.0024 - 0.0006 < 0.002) and the mat
  showed through as a round hole. Mystery solved.
## v7
- make_sheet undulation now 0..+0.5 mm (never below its base height).
- Moon = distant narrow SPOT (650 W, 34 deg, aimed through the window along the old sun direction); the SUN is
  kept at 0 W (no sun-light contribution ever appeared in EEVEE here - not chased further).
- Crystal = transparent + Fresnel glossy (no refraction, BLENDED).
- Watch train x3 speed; 5C creep 3 mm (was 2 mm and nearly static); 5A hold has a 3 cm lateral slide (parallax).
- v7 results (11:28): MOONLIGHT FINALLY READS - blue back wall with the window-mullion shadow bars, pegboard holes,
  blue rims on the pencil cup / books, cool blueprint in 5B vs the warm lamp pool: the tungsten-vs-moon contrast
  of the brief. 5B disc gone. 5C crystal now clear: rhodium perlage, brass wheels, rubies, blued hands visible
  through the glass. 5C end shows a froxel dot pattern from the inner haze at 12 spp -> haze density 38 -> 20.
- Full-res stills at the script-default 48 spp (11:50, GPU free): 5A f40 ~25 s (first frame 58 s incl. shader
  compile), 5B f40 22 s, 5C f44 16 s; build 6 s. All under the 30 s/frame budget.
- BRIEF.md gained CLIENT RULE sections (real-looking effects; never too bright; no blown highlights) + the
  tools/exposure_check.py QC. Results: 5A full f40 PASS (p5 0.06, p50 0.32), 5C full f44 PASS (p50 0.20),
  5B full f40 OVEREXPOSED (p50 0.50), 5B f58 washed (p5 0.18), 5C f16 TOO BRIGHT (3.3 % clipped, p50 0.66),
  5A f8 = the T4 photo of the 4F daylight frame (transition frame, matches 4F; judged with --day).
## v8 (client rules)
- Exposure: 5A 0 on the T4 frames -> -0.15 after the whip; 5B -0.3 (was +0.35); 5C -0.55 -> -0.15.
- Motes non-emissive and 280 (was 650 with emission 0.15); watch specks 40, non-emissive (were 90 emitting 6.0).
- Lamp bulb emission 60 -> 6 (practical at moderate intensity). Cedar re-tinted tan (read salmon under tungsten).
- v8 QC: 5A f44, 5B f12/f40, 5C f44 PASS; still too bright: 5B f76 (p50 0.50), 5C f10/f16 (p50 0.46-0.51, p5
  0.16-0.21), 5C f30 dive (p50 0.65). 5A f8 (T4) = 4F's own frame: 4F_v7_f0072 itself measures p5 0.20 with --day,
  ours 0.16 -> the handoff inherits 4F's grade (Act IV's to fix, we match it).
## v9-v12 (CLIENT RULE exposure pass)
- Sheet albedo: blueprints 0.32 (deep Prussian blue, was 0.72), graphite sheets 0.56. Moon spot 420 W (650).
  World haze 0.11 -> 0.07 (FOG_D), lamp volume factor 1.6 -> 1.1.
- 5C exposure keys -1.15 (f1-22) -> -0.85 (f30) -> -0.2 (f36) -> -0.15 (f48).
- QC v11 @50 %: 5A f44 PASS (p5 0.03, p50 0.26), 5B f20 PASS (p50 0.22), 5B f70 PASS (p50 0.42),
  5C f44 PASS (p50 0.17); 5C f10 borderline (p5 0.09) / f16 (p5 0.12) = all-paper frames with no true black,
  re-checked at -1.15 EV in v12.
- v12 QC: 5C f10 PASS (p5 0.07, p50 0.27); 5C f16 p5 0.10 (borderline WASHED: all blueprint + rhodium plate, no
  true black in frame; looks rich, left as is).
## State at 12:15 (continuation session end)
- Contact sheet of the newest stills: tests/act5_state_1215.jpg. Full-res timing stills: tests/5*_full_f00*.jpg
  (48 spp default; 5A ~25 s/frame + ~35 s one-off shader compile, 5B 22 s, 5C 16 s; build 6-12 s).
- Final render: rb.py shots/act5_desk.py -- --shot 5A --anim --from 1 --to 52   (5B --to 84, 5C --to 48)
  BEFORE final 5A: renders/photo_temple.png must exist (else the print uses the newest low-res 4F test still).
- Open items: 5C mid-dive (f27-31) is a deliberate motion-blur whoosh; perlage cells read a little large at the 5C
  end; out-of-focus centre-arbor streak in the 5C end; loupe brass a bit flat; the SUN light never contributed
  in EEVEE here (MoonSpot does the job).
- 12:15 single-shot 5C motion run with a RELATIVE --outdir finished rc 0 but no frames appeared anywhere; a re-run
  with an absolute outdir (tests/5C_animtest, frames 44-46) saved correctly. The script now turns any relative
  --outdir into film/<path>. The final-render default (renders/<ID>/) was always absolute. The last 5C motion sheet
  therefore is still the v6 one (tests/5C_sheet_v6.jpg); v7+ 5C changes (clear crystal, x3 train speed, 3 mm creep)
  were verified on stills only.

## Revision pass (director critique 12:59, score 5) - v13..v16 (13:05-13:50)
Critique: T5 does not hand off (5C f48 YAVG 59 sepia vs 6A YAVG 30 blue), fake centre/third "mesh", LED-dash teeth,
perlage cells, arbor streak; 5A whip white wash (f10 p50 0.66 / p5 0.33) + lamp glint in 4F's sky + milky print;
5B golf-ball lid, stalled ending + near-repeat cut into 5C, lavender blueprint, salmon "finger" cedar, ham-slice
shavings, ruby sprinkles / even ring scatter, dolly-on-rails run.
- v13 T5 rebuild (lib/desk.py make_watch): chunky 48-tooth centre wheel (module 0.3, 0.8 mm thick, rounded tips via
  0.12 mm bevel) at z 6.0; REAL third pinion (8 leaves, r_p 1.2) at r_c + r_p = 8.4 mm on the -39 deg line, phased
  into the wheel gaps (ph_c = TH3 mod step, ph_p = TH3 + pi - step_p/2), rates by tooth ratio (pinion = centre*48/8);
  third wheel coaxial BELOW the pinion (z 4.9) so nothing covers the engagement; third arbor shortened. Ratchet +
  crown wheel + click spring on the barrel bridge, Cotes de Geneve bridges (new mat_cotes), fine perlage (2600,
  low bump), new mat_wheel (gilt brass, circular graining via radial-tangent anisotropy).
- v13 5C end camera: first try looked ALONG the rim at 11 deg down (v13 stills: wheels edge-on, dark bands, arbor
  post in the middle) -> v14: 35-40 deg above the engagement from outside the rim (END_CAM_LOCAL), creep 8.5 -> 6 mm.
  Practicals inside the case behind the mesh: WatchWarm (area, glints on teeth tops) + WatchCool (point, 8 deg, lights
  the new 2 mm haze slab between plate and wheels -> blue backlight); both keyed on from the crystal-hide frame.
  Lamp volume off in 5C (warm veil), lamp eases 46 -> 24 W over f32-40, 5C froxels 0.4 mm..12 cm from f30.
  Hands/cap/centre arbor hidden once the lens is below 10.8 mm. Exposure end -1.25.
  Result (v16 f40/46): pinion star meshing with the centre-wheel teeth (sharp), near rim teeth blurred foreground,
  dark Cotes bridge top-left as an occluder, blue in the spoke windows; PASS p5 0.00-0.01, p50 0.20-0.23.
- 5A: print emission only inside the image mask (border = diffuse paper 0.70), photo boost 1 through f10 -> 0 at f13,
  LampSpot specular keyed 0 on f1-11, exposure (10,-0.75)(12,-1.05)(14,-0.95)(18,-0.4)(24,-0.15); lustre print (coat
  0.1, rough 0.42-0.55, spec 0.3, sat 1.1); T4 frames f1-9 rendered with the Standard view + compositor bypass
  (T4Bypass mix keyed by a frame_change_pre handler) so 4F's display-referred PNG is not tone-mapped twice; motion
  blur steps 4 on f9-18 (same handler); slow 4 cm push-in f24-46 + late rack toward the loupe.
  QC v15: f12 p5 0.09 (borderline, transition), f14 PASS p50 0.35, f46 PASS.
- 5B: S-curve over the blueprint (f1-24, lower 30 -> 12 mm), clustered spilled piles (4) instead of the corridor,
  focus lands on the loupe base bar f44-58, end retimed: skims 7 mm past the case rim (f74-80) and pans onto the open
  lid (cut f78 lands mid-move). Lid laid back to 132 deg, polished darker guilloche (900 rings/m, rough 0.04-0.12):
  reads 'open pocket watch', not a disc. Exposure -0.3 -> -0.45 at the end.
- 5C start moved to front-RIGHT and higher (W + (0.055,-0.07,0.03)), so the 5B->5C cut changes angle and side.
- Blueprints: cyanotype re-colour in mat_sheet (Prussian ground 0.010/0.040/0.150, lines 0.46/0.53/0.64, red markup
  kept, spec 0.25), 5 mm grid regenerated at 25 % contrast (tex/act5_bp_car.png, backup _act5_bp_car_v12_backup.png),
  fold creases (bump ridges). 5B f1/f8/f22 colourful 27-37 (was 18).
- Pencils: yellow-olive cedar with annual-ring grain + scalloped paint edge (shader, from the hex facet angle);
  shavings: ruffled section, painted rim band 24 %, separate CedarShaving material.
- Specks: 24 sprinkled rubies -> 4 in a brass dish on a watchmaker's cloth with a laid-out row of wheels/screws;
  pile under the tweezer tips; 8 strays; DeskDust dark (0.22) and none on the cyanotypes.
- Background: hardcover books (boards, recessed aged page block, rounded spine, gilt bands/title following the curve,
  cloth x0.6), 3x2 sash with 12 mm bars, moon blend 0.35, loupe brass 2500 scale + 180-ridge knurled lens ring,
  LampInner 0.85 -> 0.42 (it was the white 'card' mirrored in the crystal), crystal glossy 0.62 x Fresnel 0.45.
## v17-v24 (13:50-14:30)
- Motion sheets v17 (all three) / v22 (5B, 5C): 5A hold -> whip with roll -> push-in reads; 5B banks through the S,
  rushes past piles, threads the pencils, passes under the loupe, pans onto the open lid at the cut; 5C rise -> dive
  -> end creep on the real mesh. tests/5A_sheet_v17.jpg, tests/5B_sheet_v22.jpg, tests/5C_sheet_v22.jpg.
- T5 match work (5C f43 vs 6A_review_f0007, signalstats): v17 YAVG 72 / hue 185 (whole wheel face cream: the warm
  practical sat in the face's mirror direction + anisotropy 0.85 smeared every light across it) -> WatchWarm moved
  to a 14 deg grazing rim light, wheel rough 0.10-0.20 / aniso 0.5, lamp eases to 12 W, cool 0.085 W, exposure -1.6:
  v21 YAVG 47, hue 210, p50 0.09-0.10, p5 0.00 (6A: YAVG 27, hue 241). Dark wheel faces, warm tooth rims, blue
  in the spoke windows and on the bridge edge.
- 5B f40 'finger' again = the camera flew straight over the black pencil's cedar cone -> tip moved 5 mm out of the
  track (now a near-miss: graphite tip + cedar pass on the right). Green shaving moved off the f28 track.
- Cedar: darker, 900 rings/m, stronger latewood. Cotes subtler (aniso 0.5). Crystal glossy 0.45 x Fresnel 0.45,
  rough 0.07 (the remaining light polygon is the moonlit window mirrored in the glass - kept, softer). Enamel ivory.
- 5A f12 exposure -1.2 -> PASS (p5 0.08); 5C dive exposure dip at f27 (was p50 0.52 whoosh frame).
- T4 verified in an ANIMATION render (frame_change_pre handler also fires there): 5A anim f8 YLOW 57 / YAVG 114.6 /
  YHIGH 189 vs 4F_full4_f0072 55 / 114.1 / 191 (v12: YLOW 43, YHIGH 183).
- Full-res 48 spp (tests/*_full13_*): 5A f40 ~21 s, 5A f12 (4 motion-blur steps) ~20 s, 5B f40 ~16 s, 5B f28 ~17 s,
  5C f44 ~22 s (incl. first-frame compile), 5C f16 ~17 s. Build 4 s. QC: all PASS except 5A f12 (fixed in v23).
- 14:29: crystal Fresnel mix 0.45 -> 0.30 (the moonlit-window reflection was still the brightest thing in 5C f7, the
  cut-in frame). From ~14:15 all three rb.py slots were held by other acts' jobs (final renders): test turnaround went
  from ~30 s to 15+ min, so the last checks were queued.
- 14:45 final checks: 5A f12 at full res with the whip's 64 spp + 4 motion-blur steps (frame_change_pre bumps the
  48 spp default to 64 on f9-18 only; explicit --samples are untouched) PASS p5 0.07, ~27 s/frame net (79 s incl.
  15 s GPU-lock wait + first-frame shader compile). 5C f7 full res PASS. 5C dive exposure dip (26,-1.4)(30,-1.6)
  (33,-1.3): f27 p50 0.43, f29 0.41, f31 0.14 PASS.
- NOTE photo fallback: Act IV is re-grading 4F (tests/4F_r1/r2_f0072 are darker, low-res tests); PHOTO_FALLBACK
  picks the newest tests/4F_*f0072.jpg, so the print follows 4F's current look. For finals copy the FINAL 4F
  frame to renders/photo_temple.png (T4 then matches exactly; the Standard-view T4 frames reproduce it 1:1).
- State sheet: tests/act5_state_1445.jpg (5A T4 f8 / whip f12 / hold f40; 5B f28 / f40 / f78; 5C f7 / dive f27 / T5 f44).
