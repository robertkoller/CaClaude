import os, sys

# Both module directories must be on the path before any other imports
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'FaceTracking'))
sys.path.insert(0, os.path.join(_HERE, 'HandTracking'))

os.environ['GLOG_minloglevel'] = '3'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import FaceTrackerModule as ftm
import HandTrackerModule as htm
import time

# Basic setting stuff

BTN_H      = 44
DISPLAY_SC = 45 # window size scalar
CAM_SC     = 80 # capture resolution scalar

WIN_W, WIN_H = 16 * DISPLAY_SC, 9 * DISPLAY_SC
CAM_W, CAM_H = 16 * CAM_SC,     9 * CAM_SC

cap = cv2.VideoCapture(ftm.find_builtin_camera())
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

faceDetector = ftm.FaceDetector()
gestureCtrl  = ftm.HeadGestureController()
handDetector = htm.handDetector(maxHands=2)
handCtrl     = htm.GestureController()

pTime      = 0
running    = True
lastSent   = ''
show_cam   = True
show_hud   = True
on_top     = True
show_face  = True
show_hand  = True

# Building the actual window
root = tk.Tk()
root.title("CaClaude")
root.attributes('-topmost', on_top)
root.resizable(True, True)
root.configure(bg='#111111')

screen_w = root.winfo_screenwidth()
root.geometry(f"{WIN_W}x{WIN_H + BTN_H}+{screen_w - WIN_W - 10}+10")

# Button bar first so tkinter reserves its space before the expanding panel
btn_frame = tk.Frame(root, bg='#111111', height=BTN_H)
btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
btn_frame.pack_propagate(False)

panel = tk.Label(root, bg='black')
panel.pack(fill=tk.BOTH, expand=True)

BTN = dict(bg='#1e1e1e', activebackground='#2e2e2e',
           relief=tk.FLAT, font=('Helvetica', 11, 'bold'),
           padx=14, pady=0, cursor='hand2', borderwidth=0)

def toggle_cam():
    global show_cam
    show_cam = not show_cam
    cam_btn.config(text="● CAM" if show_cam else "○ CAM",
                   fg='#00ff88' if show_cam else '#555555')

def toggle_hud():
    global show_hud
    show_hud = not show_hud
    hud_btn.config(text="● HUD" if show_hud else "○ HUD",
                   fg='#44aaff' if show_hud else '#555555')

def toggle_top():
    global on_top
    on_top = not on_top
    root.attributes('-topmost', on_top)
    top_btn.config(text="● TOP" if on_top else "○ TOP",
                   fg='#ffaa00' if on_top else '#555555')

def toggle_face():
    global show_face
    show_face = not show_face
    face_btn.config(text="● FACE" if show_face else "○ FACE",
                    fg='#ff88ff' if show_face else '#555555')

def toggle_hand():
    global show_hand
    show_hand = not show_hand
    hand_btn.config(text="● HAND" if show_hand else "○ HAND",
                    fg='#ff8844' if show_hand else '#555555')

BTN_SM = {**BTN, 'padx': 10}

cam_btn  = tk.Button(btn_frame, text="● CAM",  fg='#00ff88', command=toggle_cam,  **BTN_SM)
cam_btn.pack(side=tk.LEFT, padx=(10, 3), pady=8)
hud_btn  = tk.Button(btn_frame, text="● HUD",  fg='#44aaff', command=toggle_hud,  **BTN_SM)
hud_btn.pack(side=tk.LEFT, padx=(3, 3), pady=8)
top_btn  = tk.Button(btn_frame, text="● TOP",  fg='#ffaa00', command=toggle_top,  **BTN_SM)
top_btn.pack(side=tk.LEFT, padx=(3, 3), pady=8)
face_btn = tk.Button(btn_frame, text="● FACE", fg='#ff88ff', command=toggle_face, **BTN_SM)
face_btn.pack(side=tk.LEFT, padx=(3, 3), pady=8)
hand_btn = tk.Button(btn_frame, text="● HAND", fg='#ff8844', command=toggle_hand, **BTN_SM)
hand_btn.pack(side=tk.LEFT, padx=(3, 10), pady=8)

def on_quit(*_):
    global running
    running = False

root.bind('q', on_quit)
root.protocol("WM_DELETE_WINDOW", on_quit)

win_w, win_h = WIN_W, WIN_H

def on_resize(event):
    global win_w, win_h
    if event.widget is root:
        win_w = max(event.width, 1)
        win_h = max(event.height - BTN_H, 1)

root.bind('<Configure>', on_resize)


# Main stuff
while running:
    success, img = cap.read()
    if not success:
        print("Failed to grab frame — check camera permissions")
        break

    img = cv2.flip(img, 1)
    img = cv2.resize(img, (CAM_W, CAM_H))

    cTime = time.time()
    fps   = 1 / (cTime - pTime)
    pTime = cTime

    # Face stuff
    if show_face:
        img                 = faceDetector.findFace(img, draw=show_hud)
        noseTip             = faceDetector.getNoseTip(img)
        leftOpen, rightOpen = faceDetector.getEyeStates()
        gesture             = gestureCtrl.update(noseTip, leftOpen, rightOpen)
        if gesture in ftm.GESTURE_MAP:
            choice = ftm.GESTURE_MAP[gesture]
            ftm.send_to_tmux(choice)
            lastSent = choice
    else:
        noseTip    = None
        leftOpen   = None
        rightOpen  = None
        gesture    = None

    # Hand detection
    if show_hand:
        img     = handDetector.findHands(img, draw=show_hud)
        lmRight = handDetector.findPositionByHandedness(img, 'Right')
        lmLeft  = handDetector.findPositionByHandedness(img, 'Left')
        status  = handCtrl.update(img, lmRight, lmLeft)
    else:
        status = {'keyboardActive': False, 'switcherOpen': False,
                  'lastSwipe': '', 'swipeCooldown': 0}

    # Scaling window size dynamically
    pw, ph = win_w, win_h
    sx, sy = pw / WIN_W, ph / WIN_H
    sc     = min(sx, sy)

    def sp(x, y):
        return (int(x * sx), int(y * sy))

    if show_cam:
        display = cv2.resize(img, (pw, ph))
    else:
        display = np.full((ph, pw, 3), 18, dtype=np.uint8)

    # hud
    if show_hud:

        ftm.hud(display, f"FPS {int(fps)}", sp(10, 38), 1.4 * sc, (255, 80, 255))

        if leftOpen is not None:
            rw = leftOpen and not rightOpen
            lw = not leftOpen and rightOpen
            if rw:
                mt, mc = "R-WINK  NOD=1  SHAKE=2", (0, 255, 100)
            elif lw:
                mt, mc = "L-WINK  NOD=3  SHAKE=4", (80, 210, 255)
            else:
                mt, mc = "wink to activate", (200, 200, 200)
            ftm.hud(display, mt, sp(10, 76), 1.4 * sc, mc)

        if lastSent:
            ftm.hud(display, f"-> {lastSent}", sp(10, 114), 1.8 * sc, (0, 255, 255))
        if gestureCtrl.gestureCooldown > 0:
            gc = (0, 255, 80) if 'NOD' in gestureCtrl.lastGesture else (60, 80, 255)
            ftm.hud(display, gestureCtrl.lastGesture, sp(10, 155), 2.2 * sc, gc, 3)

        kbd_label = "KEYBOARD ON" if status['keyboardActive'] else "KEYBOARD OFF"
        kbd_color = (0, 255, 0) if status['keyboardActive'] else (0, 100, 255)
        ftm.hud(display, kbd_label, sp(10, WIN_H - 80), 1.4 * sc, kbd_color)

        if status['switcherOpen']:
            ftm.hud(display, "SWITCHER — pump to confirm", sp(10, WIN_H - 44), 1.3 * sc, (0, 200, 255))
        elif status['swipeCooldown'] > 0:
            ftm.hud(display, status['lastSwipe'], sp(10, WIN_H - 44), 1.5 * sc, (0, 255, 255))

    if show_face:
        dot_color = (0, 230, 0) if faceDetector.faceDetected() else (0, 0, 230)
        dx, dy = pw - int(22 * sx), int(22 * sy)
        cv2.circle(display, (dx, dy), int(12 * sc), (0, 0, 0), cv2.FILLED)
        cv2.circle(display, (dx, dy), int(9  * sc), dot_color, cv2.FILLED)

    img_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
    tk_img  = ImageTk.PhotoImage(Image.fromarray(img_rgb))
    panel.configure(image=tk_img)
    panel.image = tk_img

    try:
        root.update()
    except tk.TclError:
        break

handCtrl.release()
cap.release()
root.destroy()
