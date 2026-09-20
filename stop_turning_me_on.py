"""
stop_turning_me_on.py

A dialog box that gets progressively more dramatic about closing itself.
Each launch bumps a run counter (saved in your home folder) and picks the next stage.

Setup:  pip install pyautogui
        pip install pygame           # optional: run 8 battle music + video's substitute audio
        pip install opencv-python pillow   # optional: run 8's top-right video
Optional (drop these next to this script -- run 8 auto-detects them):
          battle_theme.mp3 / .wav        -- loops for the whole run 8 duel
          battle_video.mp4 / .mov / .avi -- plays muted, top-right corner, from ~0:30
                                             (waits for that corner to be clear first)
          battle_video_audio.mp3 / .wav  -- substitute soundtrack, starts when the video does

Usage:  python stop_turning_me_on.py            # normal
        python stop_turning_me_on.py --stage 8  # test a specific stage
        python stop_turning_me_on.py --reset    # start over from run 1
        python stop_turning_me_on.py --stage 9 --dry-run  # test shutdown safely
"""
import json
import math
import os
import random
import subprocess
import sys
import tkinter as tk

import pyautogui

STATE_FILE = os.path.join(os.path.expanduser("~"), ".stop_turning_me_on.json")
PAUSE_MS = 3000  # the 3 second pause before every "closing" attempt

pyautogui.PAUSE = 0.1


# ---------- run counter ----------
def load_count():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)["runs"]
    except Exception:
        return 0


def save_count(n):
    with open(STATE_FILE, "w") as f:
        json.dump({"runs": n}, f)


def resource_dir():
    """Where to look for optional media files: next to the script normally,
    or PyInstaller's bundled-data folder when running as a frozen .exe."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


# ---------- the window ----------
def build_window():
    root = tk.Tk()
    root.overrideredirect(True)  # borderless, so WE own the close button
    w, h = 340, 130
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.attributes("-topmost", True)

    frame = tk.Frame(root, bg="#f0f0f0", highlightbackground="#444", highlightthickness=2)
    frame.pack(fill="both", expand=True)

    bar = tk.Frame(frame, bg="#2b2b2b", height=26)
    bar.pack(fill="x")
    tk.Label(bar, text="Message", fg="white", bg="#2b2b2b").pack(side="left", padx=8)
    close_btn = tk.Button(bar, text="X", width=3, bg="#c0392b", fg="white",
                          relief="flat", command=root.destroy)
    close_btn.pack(side="right")

    tk.Label(frame, text="stop turning me on", font=("Segoe UI", 14),
             bg="#f0f0f0").pack(expand=True)

    root.bind("<Escape>", lambda e: root.destroy())
    root.update()
    root.focus_force()
    return root, close_btn


def button_center(btn):
    return (btn.winfo_rootx() + btn.winfo_width() // 2,
            btn.winfo_rooty() + btn.winfo_height() // 2)


# ---------- the escalation ladder ----------
def stage_self_close(root, btn):
    root.destroy()


def stage_mouse_click(root, btn):
    root.update()
    x, y = button_center(btn)
    pyautogui.moveTo(x, y, duration=1.2, tween=pyautogui.easeInOutQuad)
    pyautogui.click()


def _write_and_run_batch(taskkill_args):
    """
    Visibly: open Notepad, type out a .bat file, save it to the Desktop,
    then use the cursor to run it via the Run dialog.
    Windows only (batch files).
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop, exist_ok=True)
    bat_path = os.path.join(desktop, "close_me.bat")
    pid = os.getpid()

    lines = [
        "@echo off",
        "timeout /t 1 /nobreak >nul",
        f"taskkill {taskkill_args} /PID {pid}",
    ]
    content = "\r\n".join(lines) + "\r\n"

    # Open a blank Notepad window
    subprocess.Popen(["notepad.exe"])
    pyautogui.sleep(1.0)  # let it open and take focus

    # Type the batch file contents, line by line
    for line in lines:
        pyautogui.typewrite(line, interval=0.03)
        pyautogui.press("enter")

    # Save As -> Desktop\close_me.bat
    pyautogui.hotkey("ctrl", "s")
    pyautogui.sleep(0.8)
    pyautogui.typewrite(bat_path, interval=0.02)
    pyautogui.press("enter")
    pyautogui.sleep(0.8)
    # Notepad may pop a "replace existing file?" prompt if run twice
    pyautogui.press("enter")

    # Close Notepad so the .bat file isn't locked / in the way
    pyautogui.hotkey("alt", "f4")
    pyautogui.sleep(0.5)

    # "Cursor runs it": open the Run dialog and type the path, like a user would
    pyautogui.hotkey("win", "r")
    pyautogui.sleep(0.5)
    pyautogui.typewrite(bat_path, interval=0.02)
    pyautogui.press("enter")


def stage_force_kill(root, btn):
    _write_and_run_batch("/F")  # /F: force, no cleanup


def stage_window_battle(root, btn):
    """
    A second (blue) window appears first -- before anything else, including
    the music -- to face down the original (red) window, "the one that needs
    to be closed." The red window is the boss: every 30 seconds it unleashes
    a big, telegraphed, Undertale-boss-style attack (a different pattern
    each time), and the blue window scripts a clean dodge out of the way
    every time, while chipping away at the red window's HP with its own
    steady counter-fire in between. It's scripted so the blue window is
    guaranteed to have worn the red one down by the end. Both move freely
    around the screen (no bouncing off each other). At 2:30 the fighting
    stops; the damaged-but-alive blue window says its goodbyes over the
    next 10 seconds and closes itself at 2:40. Fully automated -- no input
    needed. Drop a battle_theme.mp3 / .wav next to this script for music
    (needs pygame).
    """
    for widget in root.winfo_children():
        widget.destroy()
    root.unbind("<Escape>")  # this one plays itself out, start to finish

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    BOSS_W, BOSS_H = 260, 100   # the red window -- the one that needs to be closed
    HERO_W, HERO_H = 200, 70    # the blue window -- the new one, trying to close it
    IDLE_SPEED = 11
    TICK_MS = 20

    T_BATTLE_MS = 150_000        # 2:30 of fighting
    T_GOODBYE_MS = 10_000        # then 10s of goodbyes -> closes at 2:40
    BOSS_ATTACK_INTERVAL = 30_000
    CHIP_INTERVAL = 3_000
    CHIP_DAMAGE = 2               # 50 chip-hits x 2 dmg = exactly 100 by 2:30
    VIDEO_START_MS = 30_000      # video tries to come in at the 0:30 mark
    VIDEO_MAX_W = 340            # corner video is scaled to this width, aspect kept
    VIDEO_MARGIN = 20            # px from the top-right corner

    state = {"phase": "intro", "elapsed": 0, "b_dodging": False,
             "video_win": None, "video_cap": None, "video_rect": None}

    # ---------- music (best-effort, silently skipped if unavailable) ----------
    music_playing = [False]

    def start_music():
        try:
            import pygame
            pygame.mixer.init()
            here = resource_dir()
            for name in ("battle_theme.mp3", "battle_theme.wav", "music.mp3", "music.wav"):
                path = os.path.join(here, name)
                if os.path.exists(path):
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.set_volume(0.6)
                    pygame.mixer.music.play(loops=-1)
                    music_playing[0] = True
                    break
        except Exception:
            pass

    def stop_music():
        if music_playing[0]:
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass

    def safe(fn):
        try:
            fn()
        except tk.TclError:
            pass

    def start_video():
        """Optional: a muted video clip in the top-right corner, with a substitute
        audio track standing in for its original sound. Just a template hookup --
        drop matching files next to this script and it activates on its own. It
        waits for its corner to be empty of both fighters before claiming it."""
        try:
            import cv2
            from PIL import Image, ImageTk
        except Exception:
            return
        here = resource_dir()
        video_path = None
        for name in ("battle_video.mp4", "battle_video.mov", "battle_video.avi"):
            p = os.path.join(here, name)
            if os.path.exists(p):
                video_path = p
                break
        if not video_path:
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return

        src_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640
        src_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360
        scale = VIDEO_MAX_W / src_w
        vid_w, vid_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        frame_delay = max(15, int(1000 / fps))

        vid_x = screen_w - vid_w - VIDEO_MARGIN
        vid_y = VIDEO_MARGIN

        def spot_is_clear():
            for f in fighters.values():
                if (f["x"] < vid_x + vid_w and f["x"] + f["w"] > vid_x
                        and f["y"] < vid_y + vid_h and f["y"] + f["h"] > vid_y):
                    return False
            return True

        def wait_for_clear_spot():
            if state["phase"] != "battle":
                safe(cap.release)  # battle ended before a gap ever opened up
                return
            if not spot_is_clear():
                root.after(250, wait_for_clear_spot)
                return
            claim_spot()

        def claim_spot():
            state["video_rect"] = (vid_x, vid_y, vid_w, vid_h)  # solid for the fighters now

            vid_win = tk.Toplevel(root)
            vid_win.overrideredirect(True)
            vid_win.attributes("-topmost", True)
            vid_win.geometry(f"{vid_w}x{vid_h}+{vid_x}+{vid_y}")
            vid_label = tk.Label(vid_win, bd=0)
            vid_label.pack(fill="both", expand=True)

            state["video_win"] = vid_win
            state["video_cap"] = cap

            # muted video -- the substitute audio file is its stand-in soundtrack,
            # started the moment the video comes in
            try:
                import pygame
                pygame.mixer.init()
                for name in ("battle_video_audio.mp3", "battle_video_audio.wav"):
                    ap = os.path.join(here, name)
                    if os.path.exists(ap):
                        pygame.mixer.Sound(ap).play()
                        break
            except Exception:
                pass

            def render_frame():
                if state["phase"] not in ("battle", "goodbye"):
                    state["video_rect"] = None
                    safe(cap.release)
                    safe(vid_win.destroy)
                    return
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop back to the start
                    ok, frame = cap.read()
                    if not ok:
                        state["video_rect"] = None
                        safe(cap.release)
                        safe(vid_win.destroy)
                        return
                frame = cv2.resize(frame, (vid_w, vid_h))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                photo = ImageTk.PhotoImage(Image.fromarray(frame))
                try:
                    vid_label.config(image=photo)
                    vid_label.image = photo  # keep a reference so it isn't garbage-collected
                except tk.TclError:
                    safe(cap.release)
                    return
                root.after(frame_delay, render_frame)

            render_frame()

        wait_for_clear_spot()

    # ---------- fighter A: the RED window (needs to be closed / the boss) ----------
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    ax0, ay0 = screen_w // 4, screen_h // 3
    root.geometry(f"{BOSS_W}x{BOSS_H}+{ax0}+{ay0}")
    frame_a = tk.Frame(root, bg="#ffe0e0", highlightbackground="#c0392b", highlightthickness=3)
    frame_a.pack(fill="both", expand=True)
    bar_a = tk.Frame(frame_a, bg="#7a1f1f", height=22)
    bar_a.pack(fill="x")
    tk.Label(bar_a, text="Window", fg="white", bg="#7a1f1f", font=("Segoe UI", 8)).pack(side="left", padx=6)
    hp_label_a = tk.Label(bar_a, text="HP 100", fg="#2ecc71", bg="#7a1f1f", font=("Segoe UI", 8, "bold"))
    hp_label_a.pack(side="right", padx=6)
    text_a = tk.Label(frame_a, text="stop turning me on", font=("Segoe UI", 11), bg="#ffe0e0")
    text_a.pack(expand=True)

    # ---------- fighter B: the BLUE window -- appears first, before anything else ----------
    win_b = tk.Toplevel(root)
    win_b.overrideredirect(True)
    win_b.attributes("-topmost", True)
    bx0, by0 = screen_w * 2 // 3, screen_h // 2
    win_b.geometry(f"{HERO_W}x{HERO_H}+{bx0}+{by0}")
    frame_b = tk.Frame(win_b, bg="#e0f0ff", highlightbackground="#1f4e7a", highlightthickness=3)
    frame_b.pack(fill="both", expand=True)
    bar_b = tk.Frame(frame_b, bg="#1f4e7a", height=22)
    bar_b.pack(fill="x")
    tk.Label(bar_b, text="Window", fg="white", bg="#1f4e7a", font=("Segoe UI", 8)).pack(side="left", padx=6)
    hp_label_b = tk.Label(bar_b, text="HP 100", fg="#2ecc71", bg="#1f4e7a", font=("Segoe UI", 8, "bold"))
    hp_label_b.pack(side="right", padx=6)
    text_b = tk.Label(frame_b, text="...", font=("Segoe UI", 11), bg="#e0f0ff")
    text_b.pack(expand=True)

    def b_arrival():
        safe(lambda: text_b.config(text="no, YOU stop"))

    taunts_a = ["stay closed!", "again?!", "I'm not going anywhere.", "make me!"]
    taunts_b = ["ha, missed!", "not today.", "too slow.", "my turn."]

    fighters = {
        "a": {"win": root, "frame": frame_a, "text": text_a, "hp_label": hp_label_a,
              "x": float(ax0), "y": float(ay0), "vx": float(IDLE_SPEED), "vy": float(IDLE_SPEED),
              "w": BOSS_W, "h": BOSS_H, "hp": 100, "taunts": taunts_a},
        "b": {"win": win_b, "frame": frame_b, "text": text_b, "hp_label": hp_label_b,
              "x": float(bx0), "y": float(by0), "vx": float(-IDLE_SPEED), "vy": float(IDLE_SPEED),
              "w": HERO_W, "h": HERO_H, "hp": 100, "taunts": taunts_b},
    }
    hp_floor = {"a": 0, "b": 20}

    def hp_color(hp):
        if hp > 60:
            return "#2ecc71"
        if hp > 25:
            return "#f1c40f"
        return "#e74c3c"

    def damage(key, amount, text):
        if state["phase"] != "battle":
            return
        f = fighters[key]
        f["hp"] = max(hp_floor[key], f["hp"] - amount)
        border = "#c0392b" if key == "a" else "#1f4e7a"
        safe(lambda: f["hp_label"].config(text=f"HP {f['hp']}", fg=hp_color(f["hp"])))
        safe(lambda: f["text"].config(text=text))
        safe(lambda: f["frame"].config(highlightbackground="#ffffff"))
        root.after(120, lambda: safe(lambda: f["frame"].config(highlightbackground=border)))

    # ---------- generic helpers ----------
    def move_to(key, tx, ty, duration_ms, on_done=None):
        f = fighters[key]
        steps = max(1, duration_ms // TICK_MS)
        tx = max(0, min(tx, screen_w - f["w"]))
        ty = max(0, min(ty, screen_h - f["h"]))
        sx, sy = f["x"], f["y"]
        dx, dy = (tx - sx) / steps, (ty - sy) / steps

        def step(i=0):
            if state["phase"] != "battle":
                return
            f["x"] += dx
            f["y"] += dy
            safe(lambda: f["win"].geometry(f"+{int(f['x'])}+{int(f['y'])}"))
            if i < steps:
                root.after(TICK_MS, lambda: step(i + 1))
            elif on_done:
                on_done()
        step()

    def spawn_bar(x, y, w, h, color, life_ms):
        bar_win = tk.Toplevel(root)
        bar_win.overrideredirect(True)
        bar_win.attributes("-topmost", True)
        bar_win.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
        tk.Frame(bar_win, bg=color).pack(fill="both", expand=True)
        root.after(life_ms, lambda: safe(bar_win.destroy))
        return bar_win

    def spawn_moving_bullet(x, y, dx, dy, size, color, steps, on_done=None):
        bwin = tk.Toplevel(root)
        bwin.overrideredirect(True)
        bwin.attributes("-topmost", True)
        bwin.geometry(f"{size}x{size}+{int(x)}+{int(y)}")
        tk.Frame(bwin, bg=color).pack(fill="both", expand=True)
        pos = {"x": float(x), "y": float(y)}

        def step(i=0):
            pos["x"] += dx
            pos["y"] += dy
            try:
                bwin.geometry(f"+{int(pos['x'])}+{int(pos['y'])}")
            except tk.TclError:
                return
            if i < steps:
                root.after(TICK_MS, lambda: step(i + 1))
            else:
                safe(bwin.destroy)
                if on_done:
                    on_done()
        step()
        return bwin

    def announce(text):
        safe(lambda: text_a.config(text=text))
        safe(lambda: frame_a.config(highlightbackground="#ffcc00"))
        root.after(400, lambda: safe(lambda: frame_a.config(highlightbackground="#c0392b")))

    def end_attack(graze, text):
        state["b_dodging"] = False
        damage("b", graze, text)
        safe(lambda: text_a.config(text=random.choice(taunts_a)))

    # ---------- boss attack patterns (each different, every 30s) ----------
    def bone_assault():
        announce("BONE ASSAULT!")
        state["b_dodging"] = True
        cols = 6
        xs = [int(screen_w * i / (cols + 1)) for i in range(1, cols + 1)]
        gap = random.choice(xs)
        move_to("b", gap, fighters["b"]["y"], 700)
        root.after(600, lambda: [
            spawn_bar(x - 10, 0, 20, screen_h, "#e67e22", 900)
            for x in xs if x != gap
        ])
        root.after(1700, lambda: end_attack(10, "ouch, grazed by a bone"))

    def gaster_blaster():
        announce("GASTER BLASTER!")
        state["b_dodging"] = True
        row = random.randint(int(screen_h * 0.2), int(screen_h * 0.75))
        target_y = row - 220 if row > screen_h / 2 else row + 220
        move_to("b", fighters["b"]["x"], target_y, 700)
        spawn_bar(0, row - 3, screen_w, 6, "#f1c40f", 500)
        root.after(550, lambda: spawn_bar(0, row - 20, screen_w, 40, "#ffffff", 450))
        root.after(1500, lambda: end_attack(12, "singed by the blaster"))

    def ring_of_errors():
        announce("RING OF ERRORS!")
        state["b_dodging"] = True
        ax = fighters["a"]["x"] + BOSS_W / 2
        ay = fighters["a"]["y"] + BOSS_H / 2
        far_x = 40 if ax > screen_w / 2 else screen_w - HERO_W - 40
        far_y = 40 if ay > screen_h / 2 else screen_h - HERO_H - 40
        move_to("b", far_x, far_y, 700)

        def burst():
            for i in range(8):
                angle = i * (2 * math.pi / 8)
                spawn_moving_bullet(ax, ay, math.cos(angle) * 9, math.sin(angle) * 9,
                                     14, "#e74c3c", 40)
        root.after(300, burst)
        root.after(1900, lambda: end_attack(15, "clipped by an error"))

    def homing_404():
        announce("404 NOT FOUND!")
        state["b_dodging"] = True
        ax = fighters["a"]["x"] + BOSS_W / 2
        ay = fighters["a"]["y"] + BOSS_H / 2
        old_bx = fighters["b"]["x"] + HERO_W / 2
        old_by = fighters["b"]["y"] + HERO_H / 2
        new_x = random.uniform(40, screen_w - HERO_W - 40)
        new_y = random.uniform(40, screen_h - HERO_H - 40)
        move_to("b", new_x, new_y, 900)
        steps = 60
        for i in range(3):
            ox = ax + random.uniform(-20, 20)
            oy = ay + random.uniform(-20, 20)
            dx = (old_bx - ox) / steps
            dy = (old_by - oy) / steps
            root.after(i * 150, lambda ox=ox, oy=oy, dx=dx, dy=dy:
                       spawn_moving_bullet(ox, oy, dx, dy, 20, "#9b59b6", steps))
        root.after(2200, lambda: end_attack(11, "a 404 caught up to me"))

    boss_attacks = [bone_assault, gaster_blaster, ring_of_errors, homing_404]

    def boss_attack_cycle(index=0):
        if state["phase"] != "battle":
            return
        boss_attacks[index % len(boss_attacks)]()
        root.after(BOSS_ATTACK_INTERVAL, lambda: boss_attack_cycle(index + 1))

    # ---------- blue window's steady counter-fire ----------
    def b_chip_attack():
        if state["phase"] != "battle":
            return
        bx = fighters["b"]["x"] + HERO_W / 2
        by = fighters["b"]["y"] + HERO_H / 2
        af = fighters["a"]
        ax = af["x"] + BOSS_W / 2
        ay = af["y"] + BOSS_H / 2
        travel_ms = 260  # short flight time so a fast-moving A can't outrun the shot
        steps = max(1, travel_ms // TICK_MS)
        # lead the target: aim where A will actually be when the bullet arrives, not
        # where it was when fired -- otherwise a fast A just walks out of the way
        pred_ax = ax + af["vx"] * steps
        pred_ay = ay + af["vy"] * steps
        dx, dy = (pred_ax - bx) / steps, (pred_ay - by) / steps
        spawn_moving_bullet(bx, by, dx, dy, 10, "#3498db", steps,
                             on_done=lambda: damage("a", CHIP_DAMAGE, random.choice(taunts_b)))
        root.after(CHIP_INTERVAL, b_chip_attack)

    # ---------- idle movement (screen-contained, no bouncing off each other) ----------
    def bounce_off_video(f):
        rect = state.get("video_rect")
        if not rect:
            return
        vx0, vy0, vw, vh = rect
        if not (f["x"] < vx0 + vw and f["x"] + f["w"] > vx0
                and f["y"] < vy0 + vh and f["y"] + f["h"] > vy0):
            return  # not touching the video frame
        # push back out along whichever side has the least overlap, and bounce that axis
        overlap_left = (f["x"] + f["w"]) - vx0
        overlap_right = (vx0 + vw) - f["x"]
        overlap_top = (f["y"] + f["h"]) - vy0
        overlap_bottom = (vy0 + vh) - f["y"]
        smallest = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
        if smallest == overlap_left:
            f["x"] = vx0 - f["w"]
            f["vx"] = -abs(f["vx"])
        elif smallest == overlap_right:
            f["x"] = vx0 + vw
            f["vx"] = abs(f["vx"])
        elif smallest == overlap_top:
            f["y"] = vy0 - f["h"]
            f["vy"] = -abs(f["vy"])
        else:
            f["y"] = vy0 + vh
            f["vy"] = abs(f["vy"])
        f["x"] = max(0, min(f["x"], screen_w - f["w"]))
        f["y"] = max(0, min(f["y"], screen_h - f["h"]))

    def idle_drift():
        if state["phase"] != "battle":
            return
        state["elapsed"] += TICK_MS
        for key, f in fighters.items():
            if key == "b" and state["b_dodging"]:
                continue
            f["x"] += f["vx"]
            f["y"] += f["vy"]
            if f["x"] <= 0 or f["x"] + f["w"] >= screen_w:
                f["vx"] *= -1
                f["x"] = max(0, min(f["x"], screen_w - f["w"]))
            if f["y"] <= 0 or f["y"] + f["h"] >= screen_h:
                f["vy"] *= -1
                f["y"] = max(0, min(f["y"], screen_h - f["h"]))
            bounce_off_video(f)
            safe(lambda f=f: f["win"].geometry(f"+{int(f['x'])}+{int(f['y'])}"))

        if state["elapsed"] >= T_BATTLE_MS:
            start_goodbye()
            return
        root.after(TICK_MS, idle_drift)

    # ---------- ending ----------
    def start_goodbye():
        state["phase"] = "goodbye"
        state["b_dodging"] = False
        safe(root.withdraw)  # the red window disappears right here, battle over

        lines = ["* whew. okay.", "* good fight, honestly.", "* ...anyway, goodbye!"]

        def say(i=0):
            if state["phase"] != "goodbye" or i >= len(lines):
                return
            safe(lambda: text_b.config(text=lines[i]))
            root.after(2500, lambda: say(i + 1))
        say()

        root.after(T_GOODBYE_MS, finish)

    def finish():
        stop_music()
        state["video_rect"] = None
        if state.get("video_cap") is not None:
            safe(state["video_cap"].release)
        if state.get("video_win") is not None:
            safe(state["video_win"].destroy)
        state["phase"] = "done"
        safe(win_b.destroy)
        root.after(400, lambda: safe(root.destroy))

    def start_battle():
        state["phase"] = "battle"
        state["elapsed"] = 0
        idle_drift()
        root.after(CHIP_INTERVAL, b_chip_attack)
        root.after(BOSS_ATTACK_INTERVAL, lambda: boss_attack_cycle(0))
        root.after(VIDEO_START_MS, start_video)

    root.after(400, b_arrival)      # the blue window settles in first...
    root.after(1300, start_music)   # ...then the music...
    root.after(2100, start_battle)  # ...then the fight begins


DRY_RUN = "--dry-run" in sys.argv


def stage_shutdown(root, btn):
    """The final answer: open Command Prompt and type the shutdown command."""
    if not sys.platform.startswith("win"):
        if sys.platform == "darwin":
            cmd = ["osascript", "-e", 'tell app "System Events" to shut down']
        else:
            cmd = ["systemctl", "poweroff"]  # may need sudo / polkit permission
        if DRY_RUN:
            print("[dry run] would run:", " ".join(cmd))
            root.destroy()
            return
        subprocess.run(cmd)
        return

    # Open Command Prompt via the Run dialog, like a user would
    pyautogui.hotkey("win", "r")
    pyautogui.sleep(0.5)
    pyautogui.typewrite("cmd", interval=0.03)
    pyautogui.press("enter")
    pyautogui.sleep(1.0)  # let Command Prompt open and take focus

    command = "echo [dry run] this would have shut down the PC" if DRY_RUN else "shutdown /s /t 0"
    pyautogui.typewrite(command, interval=0.03)
    pyautogui.press("enter")

    if DRY_RUN:
        pyautogui.sleep(0.5)
        root.destroy()


STAGES = [
    # (first run it applies to, action)
    (1, stage_self_close),     # runs 1-5
    (6, stage_mouse_click),    # run 6
    (7, stage_force_kill),     # run 7
    (8, stage_window_battle),  # run 8
    (9, stage_shutdown),       # run 9+ : shuts the PC down
]


def pick_stage(run):
    chosen = STAGES[0][1]
    for first_run, action in STAGES:
        if run >= first_run:
            chosen = action
    return chosen


def main():
    if "--reset" in sys.argv:
        save_count(0)
        print("Counter reset.")
        return

    if "--stage" in sys.argv:
        run = int(sys.argv[sys.argv.index("--stage") + 1])
    else:
        run = load_count() + 1
        save_count(run)  # save BEFORE the window opens: later stages kill us

    action = pick_stage(run)
    root, btn = build_window()
    root.after(PAUSE_MS, lambda: action(root, btn))
    root.mainloop()


if __name__ == "__main__":
    main()
