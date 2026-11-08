"""Loaded by rb.py before every shot script: holds the global GPU lock only while Blender renders.

Scene building (CPU) can overlap between processes; GPU rendering stays strictly one-at-a-time.
"""
import atexit, json, os, subprocess, time
import bpy

LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".blender.lock")
_held = [False]


STALE_S = 15 * 60  # no single frame takes this long: a lock this old belongs to a hung render


def _pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True).stdout
        return str(pid).encode() in out
    except Exception:
        return True


TOOLS = os.path.dirname(LOCK)


def _others_waiting(me):
    """Fairness: other processes announce themselves with .want.<pid> while they wait for the lock."""
    for n in os.listdir(TOOLS):
        if n.startswith(".want.") and n != f".want.{me}":
            try:
                if _pid_alive(int(n.split(".")[-1])):
                    return True
                os.remove(os.path.join(TOOLS, n))
            except Exception:
                pass
    return False


def acquire():
    if _held[0]:
        return
    me = os.getpid()
    want = os.path.join(TOOLS, f".want.{me}")
    # an animation re-acquires within milliseconds of releasing: if someone else is waiting, yield first
    if _others_waiting(me):
        time.sleep(2.0)
    try:
        open(want, "w").close()
    except Exception:
        pass
    waited = 0.0
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": me, "tag": "render", "t": time.time()}).encode())
            os.close(fd)
            _held[0] = True
            try:
                os.remove(want)
            except Exception:
                pass
            if waited:
                print(f"[gpu] lock acquired after {waited:.0f}s", flush=True)
            return
        except (FileExistsError, PermissionError):
            try:
                with open(LOCK) as f:
                    info = json.load(f)
                pid = info.get("pid", -1)
                if pid == me:  # our own earlier release failed to delete it: we still hold it
                    _held[0] = True
                    return
                if not _pid_alive(pid) or time.time() - info.get("t", time.time()) > STALE_S:
                    print(f"[gpu] removing stale lock of pid {pid}", flush=True)
                    os.remove(LOCK)
                    continue
            except Exception:
                pass
            if int(waited * 4) % 240 == 0:
                print(f"[gpu] waiting for GPU lock ({waited:.0f}s)", flush=True)
            time.sleep(0.25)
            waited += 0.25


def release(*_a):
    if not _held[0]:
        return
    # Windows can refuse the delete while another guard is reading the file: retry
    for _ in range(50):
        try:
            with open(LOCK) as f:
                info = json.load(f)
            if info.get("pid") != os.getpid():
                break
            os.remove(LOCK)
            break
        except FileNotFoundError:
            break
        except Exception:
            time.sleep(0.05)
    _held[0] = False


# HARD RULE: every render, final or test, takes the single GPU lock. Never bypass it.
# (Bluescreen 0x119 VIDEO_SCHEDULER_INTERNAL_ERROR on 2026-11-08 20:26 when 3 EEVEE renders shared the 780M.)


@bpy.app.handlers.persistent
def _on_init(*_a):
    acquire()
    # RB_NO_MB=1: skip motion blur (EEVEE re-evaluates the whole scene for the shutter: slow on huge scenes)
    if os.environ.get("RB_NO_MB"):
        try:
            bpy.context.scene.render.use_motion_blur = False
        except Exception:
            pass
    # dense scenes overflow EEVEE's default 512 MB shadow pool ("Shadow buffer full" -> missing shadows)
    try:
        ee = bpy.context.scene.eevee
        if ee.shadow_pool_size in ('16', '32', '64', '128', '256', '512'):
            ee.shadow_pool_size = '1024'
    except Exception:
        pass
    # the CPU compositor (shoulder + bloom + lens) ran inside the GPU lock and left the GPU idle half the time
    try:
        if bpy.context.scene.render.compositor_device != 'GPU':
            bpy.context.scene.render.compositor_device = 'GPU'
            print("[gpu] compositor -> GPU", flush=True)
    except Exception as e:
        print("[gpu] compositor device not set:", e, flush=True)


@bpy.app.handlers.persistent
def _on_done(*_a):
    release()


# lock per frame: animations release the GPU between frames so test stills can interleave
bpy.app.handlers.render_init.append(_on_init)
bpy.app.handlers.render_pre.append(_on_init)
bpy.app.handlers.render_post.append(_on_done)
bpy.app.handlers.render_complete.append(_on_done)
bpy.app.handlers.render_cancel.append(_on_done)
atexit.register(release)
print("[gpu] guard active", flush=True)
