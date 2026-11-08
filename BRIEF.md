# ESCAPEMENT — production bible

A ~42 s, 24 fps, 1920x1080, fully procedural 3D short made in Blender 5.2 (EEVEE) from Python.
No humans. One continuous dream that keeps "escaping" from world to world through impossible
transitions. Title refers to the clock escapement: the heart that lets time move one tick at a time.

Client's words: "CRAZY good scenes, INSANE detail, ultra cinematic, ultra creative transitions
that look way too creative to be in this world, fast cuts, really really cool looking." The
quality bar is the reference set in `film/ref/` — study it before you build anything:

- `img_gears_1.jpg`, `img_gears_2.jpg` — macro clockwork: huge foreground teeth, razor-thin focus,
  warm brass/rust highlights against cool blue haze, glowing specks, deep blacks. THIS is the
  macro look for every mechanical close-up in the film.
- `img_temple.jpg` — ornate temple render: insane ornament density, gold filigree + teal glazed
  tiles + white walls + vermilion trim, layered tiered roofs, spires, vivid blue sky, symmetry.
- `sheet_car_film_teal_red.jpg`, `car_frame_*.jpg` — car film grade: teal skies, crimson/rust
  rocks, red light streaks, haze, low sun, mirror shots, fast handheld cuts, light leaks.
- `sheet_room_voxel_disintegration.jpg`, `room_frame_*.jpg` — dark concrete room, wet reflective
  floor, linear fluorescent strips, glowing doorway, the whole room DISINTEGRATING into cubes/
  voxels, diagonal hairline wipe transitions.
- `sheet_product_review_transitions.jpg`, `review_frame_*.jpg` — tactile tabletop transitions:
  blueprint sketches flying, exploded-view assembly on a cutting mat, hand-drawn type.

DO NOT replicate any of these (no Thai temple copy, no Honda NSX, no that room). Take the STYLE,
light, grade and detail density; design everything yourself.

## Story / acts (cut lengths in frames @24 fps; see shotlist.json for the authoritative table)

I   THE MOVEMENT — macro clockwork (act1_gears.py)
    1A reveal: light sweep across a wall of giant brass teeth out of darkness, dust motes.
    1B escapement anchor rocks, escape wheel ticks. 1C balance wheel + hairspring, ruby jewel.
    1D lateral dolly across a gear train with rack focus.
    1E FPV flight threading THROUGH the mechanism, ending head-on with a big 6-spoke gear
       spinning up and filling the frame  ==> T1 match cut.
II  ASSEMBLY — car built in a dark studio (act2_car.py, car model in lib/car.py)
    2A head-on spinning 6-spoke wheel rim (matches 1E), decelerates, pull back.
    2B exploded-view car floating mid-air; camera orbits; parts SLAM together on beats, sparks.
    2C macro panel lock + sparks. 2D red rear light bar ignites. 2E front light strips ignite.
    2F hero low 3/4 on wet floor, strip-light reflections, car squats (rev).
    2G the studio DISINTEGRATES into voxels and blows away revealing a dusk canyon; car launches.
III THE RUN — dusk canyon drive (act3_canyon.py)
    3A low tracking at wheel height. 3B side-mirror shot. 3C top-down drone on winding road,
    dust trail. 3D rear light bar + exhaust heat. 3E car blasts past a low camera and away; the
    dust plume billows up and ENGULFS camera  ==> T3 (dust becomes clouds).
IV  THE SANCTUM — clouds + clockwork temple (act4_temple.py)
    4A inside cloud -> emerge above a sea of golden-hour clouds -> pitch down, dive in.
    4B punch through: vast ornate temple complex below (gold spires with slowly rotating gear
       rings, teal tiled tiered roofs, a giant orrery), god rays, descending.
    4C/4D/4E macro ornament cuts (gold finial + gear ring; glazed tiles + gold trim glint; bell
       or orrery arm). 4F axial glide through the gate, ends on a perfectly SYMMETRIC hold
       (last 12 frames static) ==> T4: that frame becomes a printed PHOTO.
V   THE DESK — macro tabletop (act5_desk.py)
    5A starts with the photo filling the frame, whip pull-back: it's a photo print on a dark
       walnut workbench with car blueprints, a brass pocket watch, pencils, calipers, a loupe.
    5B low FPV "run" across the desk at macro scale (over blueprint, between pencils, under the
       loupe). 5C rise over the open pocket watch and DIVE into its gears ==> back to gears.
VI  6A title "ESCAPEMENT" in machined brass with turning gears behind, light sweep, to black.

## Transition handoffs (must match across scripts)

- T1 (1E last frames -> 2A first frames): both head-on (camera looking down the rotation axis),
  object centered, outer diameter ~95% of frame height, exactly 6 spokes, rotating CLOCKWISE on
  screen, motion-blurred fast spin. 1E = brass gear on black; 2A = dark rim with brass center lock.
- T2 is inside 2G (one continuous shot). Dusk look shared with Act III: sun ~3-6 deg elevation,
  teal upper sky, warm horizon, rust-red rock silhouettes, haze.
- T3 (3E end -> 4A start): 3E's last 12 frames are fully filled with warm tan dust (no features);
  4A's first 12 frames are fully inside bright warm-white cloud. The edit cross-dissolves them.
- T4 (4F end -> 5A start): 4F's final frame is copied to `film/renders/photo_temple.png` and used
  as the photo texture. 5A's first frame shows ONLY the photo's image area filling the 16:9 frame
  exactly (camera orthogonal to the print), then pulls back fast.
- T5 (5C end -> 6A): dive into the watch gears; 6A starts on macro gears.

## Look rules (all acts)

- Compose for a 2.39:1 center band (y 138..942 of 1080) — the edit may letterbox. Full 16:9 must
  still look good.
- Every frame needs: a clear focal subject, depth layers (foreground occluder / subject /
  background), atmosphere (fog, dust, motes, haze), contrast (deep blacks, bright speculars),
  and motivated light (practicals, strips, sun). Shallow depth of field on close-ups.
- Detail density is the whole game: bevels on every hard edge (light catches edges), material
  variation (noise-driven roughness/color, scratches, grime), small parts (screws, rivets,
  jewels, panel gaps, vents, ornaments) — thousands of them via loops/instancing.
- Camera moves are motivated and fast: whip-pans, speed ramps (ease-in/ease-out keyframes),
  handheld micro shake (common.shake), dolly + rack focus. Motion blur ON.
- Palette: Act I warm brass vs cool cyan haze; Act II cool white strips, wet black, teal and red
  accents, orange sparks; Act III teal sky + rust red + crimson lights; Act IV gold, teal tiles,
  white, vermilion, blue sky + golden light; Act V tungsten lamp vs blue window, walnut, paper.
- View transform AgX (look 'AgX - Medium High Contrast' or 'AgX - Punchy'); final grade happens
  in post, so render clean, not crushed.

## Technical rules (READ — the laptop must not crash)

- Machine: AMD Ryzen 7 260 + Radeon 780M iGPU (shared RAM). ONE Blender process at a time.
- NEVER launch blender.exe directly. Always:
    PY=/e/experimentswithclaude/tools/blender/blender-5.2.2-windows-x64/5.2/python/bin/python.exe
    cd film && "$PY" tools/rb.py shots/<script>.py -- --shot 2B --stills 1,30,60 --pct 50 --samples 16
  rb.py holds a global GPU lock (you may wait for other agents' renders — that's expected).
  Use Bash timeouts up to 600000 ms; for long jobs use run_in_background.
- Do not modify `film/lib/common.py` or `film/tools/rb.py` (shared). Put helpers in your own
  module `film/lib/<yourname>.py` or in your shot script.
- Test stills: --pct 50 --samples 16 (they are JPEG in film/tests/). View them with Read.
  Motion check: --anim --jpg --pct 40 --samples 8 --step 2 --outdir film/tests/<shot>_motion
  then make a contact sheet with ffmpeg (tile filter) and Read it.
- Final-quality budget: <= 30 s per frame at 1920x1080 at the samples you choose (measure it
  with one full-res still; the log prints the time). Keep polycount sane (< ~8M tris visible),
  volumetric_tile_size >= '4', no 8K textures (all procedural anyway).
- Units: meters. Real-world scale matters for DOF (macro scenes can be built big and use a
  small fstop/long lens to fake macro, or tiny with realistic macro fstop — your call, but DOF
  must look like macro photography).
- Each act script: `--shot <ID>` selects camera + frame range; frames are LOCAL to the shot,
  starting at 1, and include handles (see shotlist.json `render_frames`). Output of
  `finish(shot_id)`: `film/renders/<ID>/####.png`.

## Library (film/lib/common.py)

reset, setup_render, compositor (bloom + dispersion), world_color / world_hdri (Blender's
bundled sunset/sunrise/forest/city/courtyard/interior/night/studio .exr) / world_sky (physical
sky) / add_world_fog, prim, mesh_obj, from_bmesh, bevel, subsurf, apply_mods, set_mat, parent,
empty, make_gear (spur gear with rim/spokes/hub), spin_gear, fc_key, key_vec, set_interp,
shake, look_at, track_to, camera (with DOF), bind_cameras, light, NB (node builder), mat_brass,
mat_metal, mat_gold, mat_carpaint, mat_glass, mat_rubber, mat_concrete (wet puddles),
mat_rock, mat_asphalt, mat_principled, mat_image, mat_emission, mat_volume, volume_box, arg,
finish. Read the file — it is short.

## CLIENT RULE (added mid-production) — effects must look REAL

The client: "never do random VFX that are not good, like random unrealistic particles — be CREATIVE in a
sense that is of course not realistic, but effects that LOOK REAL." So:
- Every effect must be physically plausible in look: sparks = hot metal (short-lived, gravity, white-yellow
  core cooling to orange, motion-blurred streaks, bounce off the floor, light the surroundings); dust =
  volumetric, lit by the sun, soft-edged, swirling with turbulence; disintegration = real material chunks
  (concrete/metal fragments with proper shading, shadows, mass, motion blur), not glowing toy cubes or
  floating confetti; motes = sparse, tiny, mostly out of focus, catching light like real dust.
- The IDEAS can be impossible (a studio dissolving into a canyon, dust becoming clouds); the RENDERING must
  look photographed. No sci-fi glow particles, no rainbow sparkles, no evenly-spread random specks, no
  emissive "magic" bits, no cartoon effects. When in doubt: fewer, bigger, better-lit, motion-blurred.
- Sound: only real downloaded free assets (never self-synthesized SFX or music).

## CLIENT RULE (added mid-production) — NEVER too bright; colour must be rich and detailed

The client looked at the stills and said the light is far too bright ("never do light that is too bright…
your normal light is bright as well") and that colouring must be detailed and good. Blown-out, milky,
washed-out frames (current 1B/1C/1D, 2C, 3D, 4A) are unacceptable.
- Expose like the img_gears refs: most of the frame in deep shadow and rich mid-tones, highlights reserved
  for small speculars, edges and practical lights. Large white/near-white areas are a failure (a
  deliberate 1-3 frame flash in the edit is the only exception). Lower light energies, lower fog density,
  lower emission strengths; let contrast come from darkness, not from more light.
- Fog/haze must never lift the blacks into milky grey: keep shadows dark (p5 luma < 0.08 for interiors and
  macro), use thin, localised volumes (shafts, pools), not a global soup.
- Colour: deliberate palettes with colour contrast (warm key vs cool fill/rim, coloured practicals),
  saturated but natural; per-material hue variation (brass from pale gold to deep amber, tiles with
  per-tile teal/green shifts, rocks with rust/ochre/violet variation). No grey, desaturated frames.
- MANDATORY QC on every still you judge:
    "<blender python>" tools/exposure_check.py [--day] tests/<still>.jpg
  (--day only for daylight exteriors: Act III sky shots, Act IV temple/clouds). Fix every TOO BRIGHT /
  OVEREXPOSED / WASHED OUT / DULL COLOUR failure before moving on, except deliberate transition frames
  (inside dust/cloud, flash) which you note as such.

## CLIENT RULE 2 (added mid-production) — no blown highlights ANYWHERE + more crazy driving

The client circled every bright spot in the current stills: ceiling/vertical fluorescent strips, the red
light bar, car-paint reflections, spark clusters, gold glints, sun-flare blobs, bloom halos. ALL of them
read as "too crazy bright". Rules:
- Practical lights (strips, panels, lamps, light bars, headlights) must read as coloured, textured light
  sources at moderate intensity: visible diffuser/LED structure, a soft gradient, slight colour (cool
  4500-5600K for strips, deep red for tail lights), peak display value ~0.8-0.9, never a solid white bar
  with a halo. Use low Emission Strength (typically 2-8, not 20-100) and let area lights do the lighting.
- Reflections of those lights on paint/floor must keep their colour and not clip. Sparks: few, small, short.
- Bloom: barely visible. common.compositor() now caps bloom (<= 0.12) and applies a highlight shoulder
  that rolls bright values off before white — do not try to fight it with more energy.
- exposure_check.py is now stricter on clipping (max 0.5% clipped, 2% near-white).

ACT III gets three NEW driving shots (shotlist.json order is now 3A 3B 3F 3C 3G 3D 3H 3E):
  3F DRIFT (36 f): low wide on the outside of a hairpin; the car enters in a full four-wheel drift, tail
     sweeping out, tyres throwing gravel + real dust, backlit by the low sun; camera pans with it.
  3G OVERPASS (24 f): camera lying on the asphalt; the car charges head-on and drives right OVER the lens —
     the underbody, diffuser fins and exhaust glow sweep overhead — then recedes. Impossible, but photoreal.
  3H SLOT CANYON (36 f): FPV drone chase behind the car through a narrow slot canyon, banking hard, rock
     walls inches from the lens, shafts of sun cutting through, dust trail.
The car must DRIVE like a real hypercar: weight transfer, body roll, suspension compression on bumps, wheel
spin matching speed, steering angle into corners, slip angle in the drift.

## CLIENT RULE 3 (12:50) — remaining hotspots the client marked + schedule

Still too bright (fix in the scene, not just in post): 1B the glint on the top edge; 1C the hot glint on
the balance-wheel rim (left); 1D the large white/near-white plate area in the lower half (darken/texture
it, it must not read as a white sheet); 2C the bolt-head glint; 2G the sun glow next to the car (horizon
sun disc/flare - make it a dim, warm, partially occluded glow); 3D the exhaust flames, the light bar and
the exhaust glow (much dimmer, deep red bar, small blue-orange flame cores); 4D the gold trim glint
streak on the tiles. Everything else the client called "good" - keep it.
The compositor shoulder is now stronger (knee 0.5, cap 1.6) but large bright AREAS must be fixed in the
scene: lower light energy, rougher/darker materials, smaller highlights.
SCHEDULE: all revision passes end at 14:30 local time - final renders start then.

## DIRECTOR FIX (13:30)
common.shake() no longer overwrites the first key of already-animated channels (previously every shaken camera started at its END pose). If you worked around that (e.g. frame_set before shake), it still works; if you didn't, re-check your shaken cameras' first frames. Do NOT use PLANE light probes (they disable screen-space reflections in this EEVEE build).

