import json
H = 6
shots = [
 ("1A","act1_gears.py",48,"Reveal: light sweep across giant brass teeth from black, dust motes, slow push"),
 ("1B","act1_gears.py",14,"Escapement anchor rocks, escape wheel ticks (tick lands at cut frame 7)"),
 ("1C","act1_gears.py",14,"Balance wheel + hairspring oscillating, ruby jewel glint"),
 ("1D","act1_gears.py",24,"Lateral dolly across a gear train with rack focus"),
 ("1E","act1_gears.py",56,"FPV through the mechanism -> head-on 6-spoke gear spins up, fills frame (T1 out)"),
 ("2A","act2_car.py",30,"Head-on spinning 6-spoke rim (T1 in), decelerate, pull back to reveal"),
 ("2B","act2_car.py",72,"Exploded-view orbit; parts slam together on cut frames 12,24,36,48,60 with sparks"),
 ("2C","act2_car.py",12,"Macro panel lock + sparks"),
 ("2D","act2_car.py",14,"Rear red light bar ignites (sweep)"),
 ("2E","act2_car.py",12,"Front light strips ignite"),
 ("2F","act2_car.py",36,"Hero low 3/4 on wet floor, strip reflections, car squats"),
 ("2G","act2_car.py",48,"Studio disintegrates into voxels -> dusk canyon revealed; car launches"),
 ("3A","act3_canyon.py",22,"Low tracking at wheel height, speed"),
 ("3B","act3_canyon.py",18,"Side-mirror shot reflecting road + dust"),
 ("3F","act3_canyon.py",36,"DRIFT: low wide on the outside of a hairpin; car enters in a full four-wheel drift, tail sweeping out, tyres throwing gravel + dust, backlit"),
 ("3C","act3_canyon.py",36,"Top-down drone over winding canyon road, dust trail"),
 ("3G","act3_canyon.py",24,"OVERPASS: camera on the asphalt, car charges head-on and drives OVER the lens (underbody, diffuser, exhaust glow sweep overhead), recedes"),
 ("3D","act3_canyon.py",16,"Rear light bar + exhaust heat close-up"),
 ("3H","act3_canyon.py",36,"SLOT CANYON: FPV drone chase behind the car through a narrow slot canyon, banking, walls inches away, sun shafts"),
 ("3E","act3_canyon.py",72,"Car blasts past low camera and away; dust plume engulfs camera (T3 out: last 12 cut frames all dust)"),
 ("4A","act4_temple.py",60,"Inside cloud (T3 in) -> above golden cloud sea -> pitch down and dive"),
 ("4B","act4_temple.py",60,"Punch through clouds: clockwork temple complex reveal, god rays, descending"),
 ("4C","act4_temple.py",16,"Macro gold finial with rotating gear ring"),
 ("4D","act4_temple.py",16,"Teal glazed tiles + gold trim, glint sweep"),
 ("4E","act4_temple.py",16,"Bell swing / orrery arm macro"),
 ("4F","act4_temple.py",66,"Axial glide through gate; last 12 cut frames a static symmetric hold (T4 out -> photo)"),
 ("5A","act5_desk.py",40,"Photo fills frame (T4 in) -> whip pull-back reveals desk"),
 ("5B","act5_desk.py",72,"Macro FPV run across desk: blueprint, pencils, under loupe"),
 ("5C","act5_desk.py",36,"Rise over open pocket watch, dive into gears (T5 out)"),
 ("6A","act1_gears.py",60,"Title ESCAPEMENT in machined brass, gears behind, light sweep, to black"),
]
out = []
t = 0
for sid, script, cut, desc in shots:
    out.append({"id": sid, "script": script, "cut_frames": cut, "handles": H, "render_frames": cut + 2*H,
                "cut_in_local": H + 1, "cut_out_local": H + cut, "edit_start_frame": t + 1, "desc": desc})
    t += cut
json.dump({"fps": 24, "total_cut_frames": t, "total_seconds": round(t/24, 2), "shots": out}, open("shotlist.json", "w"), indent=1)
print(t, round(t/24,2), sum(s['render_frames'] for s in out))
