import os
os.environ['GLOG_minloglevel'] = '3'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import tkinter as tk
from PIL import Image, ImageTk
import HandTrackerModule as htm
import time

def find_builtin_camera():
    """Return the OpenCV index of the physical built-in camera.

    Queries AVFoundation directly so it works even when iPhone Continuity
    Camera is active (which shifts device indices).  Falls back to 0.
    """
    try:
        import AVFoundation as avf
        device_types = [avf.AVCaptureDeviceTypeBuiltInWideAngleCamera]
        for name in ('AVCaptureDeviceTypeContinuityCamera',
                     'AVCaptureDeviceTypeExternal',
                     'AVCaptureDeviceTypeExternalUnknown'):
            t = getattr(avf, name, None)
            if t:
                device_types.append(t)
        session = avf.AVCaptureDeviceDiscoverySession \
            .discoverySessionWithDeviceTypes_mediaType_position_(
                device_types,
                avf.AVMediaTypeVideo,
                avf.AVCaptureDevicePositionUnspecified,
            )
        for i, device in enumerate(session.devices()):
            if device.deviceType() == avf.AVCaptureDeviceTypeBuiltInWideAngleCamera:
                return i
    except Exception:
        pass
    return 0

ALWAYS_ON_TOP = True

ratioW = 16
ratioH = 9
camScalar = 120
displayScalar = 30  # adjust this to resize the window (60 = 960x540)

widthCam, heightCam = ratioW * camScalar, ratioH * camScalar
displayW, displayH = ratioW * displayScalar, ratioH * displayScalar

cap = cv2.VideoCapture(find_builtin_camera())
cap.set(cv2.CAP_PROP_FRAME_WIDTH, widthCam)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, heightCam)

handDetector = htm.handDetector(maxHands=2)
controller = htm.GestureController()
pTime = 0
running = True

root = tk.Tk()
root.title("CaClaude")
root.attributes('-topmost', ALWAYS_ON_TOP)
root.resizable(False, False)
root.geometry(f"{displayW}x{displayH}")
panel = tk.Label(root)
panel.pack(fill=tk.BOTH, expand=True)

def on_quit(*_):
    global running
    running = False

root.bind('q', on_quit)
root.protocol("WM_DELETE_WINDOW", on_quit)

while running:
    success, img = cap.read()
    if not success:
        print("Failed to grab frame — check camera permissions or try VideoCapture(1)")
        break

    img = cv2.flip(img, 1)
    img = cv2.resize(img, (widthCam, heightCam))

    img = handDetector.findHands(img)
    lmRight = handDetector.findPositionByHandedness(img, 'Right')
    lmLeft  = handDetector.findPositionByHandedness(img, 'Left')

    status = controller.update(img, lmRight, lmLeft)

    # --- HUD ---
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime

    cv2.putText(img, str(int(fps)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

    kbd_label = "KEYBOARD ON" if status['keyboardActive'] else "KEYBOARD OFF"
    kbd_color = (0, 255, 0) if status['keyboardActive'] else (0, 0, 255)
    cv2.putText(img, kbd_label, (10, 120), cv2.FONT_HERSHEY_PLAIN, 2, kbd_color, 2)

    if status['switcherOpen']:
        cv2.putText(img, "SWITCHER OPEN — pump to confirm", (10, 160),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 200, 255), 2)
    elif status['swipeCooldown'] > 0:
        cv2.putText(img, status['lastSwipe'], (10, 160), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)

    if status['fingersDebug']:
        cv2.putText(img, status['fingersDebug'], (10, 200), cv2.FONT_HERSHEY_PLAIN, 1.5, (200, 200, 0), 2)

    # --- Display in tkinter ---
    display_img = cv2.resize(img, (displayW, displayH))
    img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
    tk_img = ImageTk.PhotoImage(Image.fromarray(img_rgb))
    panel.configure(image=tk_img)
    panel.image = tk_img  # keep reference so garbage collector doesn't drop it

    try:
        root.update()
    except tk.TclError:
        break

controller.release()
cap.release()
root.destroy()
