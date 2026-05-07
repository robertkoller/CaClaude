import os
os.environ['GLOG_minloglevel'] = '3'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import FaceTrackerModule as ftm
import time

# --- Config ---
ALWAYS_ON_TOP = True
displayScalar = 45
camScalar     = 80
BTN_H         = 44

displayW, displayH = 16 * displayScalar, 9 * displayScalar
captureW, captureH = 16 * camScalar,     9 * camScalar

cap = cv2.VideoCapture(ftm.find_builtin_camera())
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  captureW)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, captureH)

faceDetector = ftm.FaceDetector()
gestureCtrl  = ftm.HeadGestureController()
pTime       = 0
running     = True
lastSent    = ''
show_camera = True
show_hud    = True

# --- Window ---
root = tk.Tk()
root.title("CaClaude")
root.attributes('-topmost', ALWAYS_ON_TOP)
root.resizable(True, True)
screen_w = root.winfo_screenwidth()
root.geometry(f"{displayW}x{displayH + BTN_H}+{screen_w - displayW - 10}+10")
root.configure(bg='#111111')

# Button bar packed first so tkinter reserves its space before the expanding panel
btn_frame = tk.Frame(root, bg='#111111', height=BTN_H)
btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
btn_frame.pack_propagate(False)

panel = tk.Label(root, bg='black')
panel.pack(fill=tk.BOTH, expand=True)

BTN = dict(bg='#1e1e1e', activebackground='#2e2e2e',
           relief=tk.FLAT, font=('Helvetica', 11, 'bold'),
           padx=14, pady=0, cursor='hand2', borderwidth=0)

def toggle_camera():
    global show_camera
    show_camera = not show_camera
    cam_btn.config(text="● CAM" if show_camera else "○ CAM",
                   fg='#00ff88'  if show_camera else '#555555')

def toggle_hud():
    global show_hud
    show_hud = not show_hud
    hud_btn.config(text="● HUD" if show_hud else "○ HUD",
                   fg='#44aaff'  if show_hud else '#555555')

def toggle_topmost():
    global ALWAYS_ON_TOP
    ALWAYS_ON_TOP = not ALWAYS_ON_TOP
    root.attributes('-topmost', ALWAYS_ON_TOP)
    top_btn.config(text="● TOP" if ALWAYS_ON_TOP else "○ TOP",
                   fg='#ffaa00'  if ALWAYS_ON_TOP else '#555555')

cam_btn = tk.Button(btn_frame, text="● CAM", fg='#00ff88', command=toggle_camera, **BTN)
cam_btn.pack(side=tk.LEFT, padx=(10, 4), pady=8)

hud_btn = tk.Button(btn_frame, text="● HUD", fg='#44aaff', command=toggle_hud, **BTN)
hud_btn.pack(side=tk.LEFT, padx=(4, 4), pady=8)

top_btn = tk.Button(btn_frame, text="● TOP", fg='#ffaa00', command=toggle_topmost, **BTN)
top_btn.pack(side=tk.LEFT, padx=(4, 10), pady=8)

def on_quit(*_):
    global running
    running = False

root.bind('q', on_quit)
root.protocol("WM_DELETE_WINDOW", on_quit)

# Track window size for rezing shenanigans
win_w, win_h = displayW, displayH

def on_resize(event):
    global win_w, win_h
    if event.widget is root:
        win_w = max(event.width, 1)
        win_h = max(event.height - BTN_H, 1)

root.bind('<Configure>', on_resize)

while running:
    success, img = cap.read()
    if not success:
        print("Failed to grab frame — check camera permissions")
        break

    img = cv2.flip(img, 1)
    img = cv2.resize(img, (captureW, captureH))

    img = faceDetector.findFace(img, draw=show_hud)
    noseTip             = faceDetector.getNoseTip(img)
    leftOpen, rightOpen = faceDetector.getEyeStates()
    gesture             = gestureCtrl.update(noseTip, leftOpen, rightOpen)

    if gesture in ftm.GESTURE_MAP:
        choice = ftm.GESTURE_MAP[gesture]
        ftm.send_to_tmux(choice)
        lastSent = choice

    cTime = time.time()
    fps   = 1 / (cTime - pTime)
    pTime = cTime

    pw, ph = win_w, win_h
    sx, sy = pw / displayW, ph / displayH
    sc     = min(sx, sy)

    def sp(x, y):
        return (int(x * sx), int(y * sy))

    if show_camera:
        display_img = cv2.resize(img, (pw, ph))
    else:
        display_img = np.full((ph, pw, 3), 18, dtype=np.uint8)

    if show_hud:
        ftm.hud(display_img, f"FPS {int(fps)}", sp(10, 38), 1.4 * sc, (255, 80, 255))

        if leftOpen is not None:
            right_wink = leftOpen and not rightOpen
            left_wink  = not leftOpen and rightOpen
            if right_wink:
                mode_text, mode_color = "R-WINK  NOD=1  SHAKE=2", (0, 255, 100)
            elif left_wink:
                mode_text, mode_color = "L-WINK  NOD=3  SHAKE=4", (80, 210, 255)
            else:
                mode_text, mode_color = "wink to activate", (200, 200, 200)
            ftm.hud(display_img, mode_text, sp(10, 76), 1.4 * sc, mode_color)

        if lastSent:
            ftm.hud(display_img, f"-> {lastSent}", sp(10, 114), 1.8 * sc, (0, 255, 255))

        if gestureCtrl.gestureCooldown > 0:
            g_color = (0, 255, 80) if 'NOD' in gestureCtrl.lastGesture else (60, 80, 255)
            ftm.hud(display_img, gestureCtrl.lastGesture, sp(10, 155), 2.2 * sc, g_color, 3)

    # Status dot, always visible
    face_color = (0, 230, 0) if faceDetector.faceDetected() else (0, 0, 230)
    dot_x, dot_y = pw - int(22 * sx), int(22 * sy)
    cv2.circle(display_img, (dot_x, dot_y), int(12 * sc), (0, 0, 0), cv2.FILLED)
    cv2.circle(display_img, (dot_x, dot_y), int(9  * sc), face_color, cv2.FILLED)

    img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
    tk_img  = ImageTk.PhotoImage(Image.fromarray(img_rgb))
    panel.configure(image=tk_img)
    panel.image = tk_img

    try:
        root.update()
    except tk.TclError:
        break

cap.release()
root.destroy()
