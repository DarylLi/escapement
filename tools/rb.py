"""Render-safe Blender runner (v2).

Every Blender invocation (tests, stills, final renders) must go through this script:
  <blender python> film/tools/rb.py <script.py> [-- script args...]
  <blender python> film/tools/rb.py --blend file.blend [blender args...]

- At most MAX_SLOTS Blender processes exist at once (scene building is CPU work and may overlap).
- tools/gpu_guard.py is loaded first and holds the global GPU lock (.blender.lock) only while
  Blender is actually rendering, so GPU rendering is strictly one-at-a-time.
"""
import os, sys, time, subprocess, json, threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
BLENDER = os.environ.get("BLENDER", r"E:\experimentswithclaude\tools\blender\blender-5.2.2-windows-x64\blender.exe")  # set BLENDER to your blender.exe
GUARD = os.path.join(TOOLS, "gpu_guard.py")
LOG = os.path.join(TOOLS, "render_log.jsonl")
MAX_SLOTS = 1  # one Blender process at a time after the 0x119 bluescreen
TIMEOUT = 60 * 60 * 6


def pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True).stdout
        return str(pid).encode() in out
    except Exception:
        return True


def acquire_slot(tag):
    waited = 0
    # final renders (render_queue.py sets RB_FINAL=1) get their own reserved slot so test jobs can't starve them
    names = [str(i) for i in range(MAX_SLOTS)]  # finals and tests share the single slot
    while True:
        for i in names:
            p = os.path.join(TOOLS, f".slot.{i}")
            try:
                fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, json.dumps({"pid": os.getpid(), "tag": tag, "t": time.time()}).encode())
                os.close(fd)
                return p
            except FileExistsError:
                try:
                    info = json.load(open(p))
                    if not pid_alive(info.get("pid", -1)):
                        os.remove(p)
                except Exception:
                    pass
        if waited % 60 == 0:
            print(f"[rb] waiting for a Blender slot ({waited}s)...", flush=True)
        time.sleep(2)
        waited += 2


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if args[0] == "--blend":
        cmd = [BLENDER, "-b", args[1], "--python", GUARD] + args[2:]
        tag = os.path.basename(args[1])
    else:
        script, rest = args[0], args[1:]
        cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", GUARD, "--python", script] + rest
        tag = os.path.basename(script)
    slot = acquire_slot(tag)
    t0 = time.time()
    rc = -1
    box = {"p": None}
    limit = TIMEOUT if "--anim" in args else 60 * 60

    def _watchdog():
        while box["p"] is None or box["p"].poll() is None:
            time.sleep(5)
            p = box["p"]
            if p is not None and p.poll() is None and time.time() - t0 > limit:
                print(f"[rb] TIMEOUT after {limit}s, killing Blender", flush=True)
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                return
    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        flags = 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS keeps the desktop responsive
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", creationflags=flags)
        box["p"] = p
        for line in p.stdout:
            if "Rendering" in line and "/" in line and "sample" in line.lower():
                continue
            sys.stdout.write(line)
        rc = p.wait()
    finally:
        p = box["p"]
        if p is not None and p.poll() is None:
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        try:
            os.remove(slot)
        except FileNotFoundError:
            pass
        # if Blender died while holding the GPU lock, free it
        lk = os.path.join(TOOLS, ".blender.lock")
        try:
            info = json.load(open(lk))
            if p is not None and info.get("pid") == p.pid:
                os.remove(lk)
        except Exception:
            pass
        dt = time.time() - t0
        with open(LOG, "a") as f:
            f.write(json.dumps({"tag": tag, "cmd": cmd[3:], "rc": rc, "sec": round(dt, 1), "t": time.time()}) + "\n")
        print(f"[rb] done rc={rc} in {dt:.1f}s", flush=True)
        print("[rb] DIRECTOR NOTE (new client feedback, applies to every act): frames are too bright/washed out. "
              "Read ALL 'CLIENT RULE' sections at the end of film/BRIEF.md (never too bright - no blown highlights anywhere incl. light strips/bars/reflections/glints/bloom, rich detailed colour, "
              "effects must look real; Act III MUST build the 3 NEW driving shots 3F 3G 3H in shotlist.json; see CLIENT RULE 3 for the exact hotspots the client marked; ALL REVISIONS END 14:30) and run tools/exposure_check.py [--day] on every still you judge.", flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
