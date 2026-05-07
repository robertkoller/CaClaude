# CaClaude — Face Gesture Interface

Control Claude Code with your face. No keyboard required once a session is running.

---

## How to start

```bash
# From inside a project you want to work on:
cd ~/CodingProjects/MyProject
caclaude

# Or pass a path directly from anywhere:
caclaude ~/CodingProjects/MyProject
```

This does three things automatically:
1. Creates a tmux session called `caclaude` and starts Claude inside it, in your project directory
2. Opens a Terminal window attached to that session
3. Launches the floating camera overlay window

When you close the camera overlay (or press `q` in it), the tmux session is killed and any injected `CLAUDE.md` is cleaned up.

---

## Setup (one time)

**Shell alias** — add to `~/.zshrc` so `caclaude` works from any terminal:
```bash
alias caclaude='bash ~/CodingProjects/CaClaude/launch.sh'
```
Then run `source ~/.zshrc`.

**Dependencies** — install inside the venv:
```bash
cd ~/CodingProjects/CaClaude
source venv/bin/activate
pip install opencv-python mediapipe pillow numpy pyobjc-framework-AVFoundation
```

---

## The camera overlay window

A small floating window appears in the top-right corner of your screen. It is always on top by default and shows your face with the gesture HUD overlaid. The window is freely resizable — drag any corner or edge and everything scales with it.

### Buttons

| Button | Color | What it does |
|--------|-------|--------------|
| **● CAM** | Green | Toggle camera feed on/off. Detection keeps running when off — you see a dark screen instead of video. |
| **● HUD** | Blue | Toggle the text overlay and face wireframe on/off. |
| **● TOP** | Orange | Toggle always-on-top. Click to let other windows cover the overlay. |

### Status dot

A small dot in the top-right corner of the video area is always visible regardless of HUD/CAM state:
- **Green** — face detected, tracking active
- **Red** — no face detected

---

## Gesture controls

Gestures only register when you hold a wink. This prevents accidental triggers during normal blinking.

### Activation

You must hold a wink the entire time you want gestures to count. Releasing the wink immediately clears the gesture buffer.

| Wink | Options available |
|------|------------------|
| **Right wink** (close right eye, keep left open) | Options 1 and 2 |
| **Left wink** (close left eye, keep right open) | Options 3 and 4 |

### Gestures

| Wink held + movement | Sends to Claude |
|----------------------|-----------------|
| Right wink + **nod** (chin down and back up) | `1` + Enter |
| Right wink + **shake** (head left–right–left) | `2` + Enter |
| Left wink + **nod** | `3` + Enter |
| Left wink + **shake** | `4` + Enter |

After a gesture fires there is a short cooldown (~1.5 seconds) before the next one can register, shown as a flashing label in the HUD.

### Tips for reliable detection

- **Nod**: move your chin down 3–4cm and back up in one smooth motion. The gesture needs a clear down-then-up arc.
- **Shake**: move your head left then right (or right then left) with enough amplitude — roughly ear-width travel total.
- Hold the wink firmly. A half-blink may not register or may register as the wrong eye.
- Keep your face centred in the frame and well-lit.

---

## How Claude responds

When CaClaude injects `CLAUDE.md` into your project, it instructs Claude to end every response with a numbered option menu:

```
---
1) Yes / most likely next step
2) No / stop
3) Alternative
4) Different approach
```

You select by gesture. Claude never needs you to type a full answer — just gesture your choice.

If you need to type something that isn't a numbered option, you can always type freely in the Terminal window. The face relay only injects input via `tmux send-keys` and never interferes with your keyboard.

---

## How it works internally

```
Camera (built-in Mac)
    └─▶ FaceTrackerModule.py
            ├─ find_builtin_camera() — queries AVFoundation via PyObjC to find the
            │                          physical built-in camera, ignoring iPhone
            │                          Continuity Camera which can shift indices
            ├─ FaceDetector          — MediaPipe FaceLandmarker model
            │    ├─ findFace()       — runs inference, optionally draws wireframe + nose dot
            │    ├─ getNoseTip()     — returns (x, y) pixel coords of landmark #4
            │    └─ getEyeStates()   — reads eyeBlinkLeft/Right blendshape scores
            ├─ HeadGestureController
            │    └─ update()         — buffers last 30 nose positions, detects nod/shake
            │                          only when a wink is held
            ├─ send_to_tmux()        — calls `tmux send-keys -t caclaude <key> Enter`
            │                          No window focus needed. Cannot type into anything
            │                          other than the named tmux session.
            ├─ hud()                 — draws outlined text readable on any background
            └─ GESTURE_MAP           — maps gesture names to keys ('nod_a' → '1', etc.)

FaceTracker.py
    └─ UI + main loop — tkinter window, toggle buttons, frame display
                        All logic lives in FaceTrackerModule; this file is display only.

launch.sh
    ├─ Copies CLAUDE.md into the project directory
    ├─ Creates tmux session `caclaude` with Claude running in the project
    ├─ Opens Terminal.app attached to that session
    └─ On exit: deletes injected CLAUDE.md, restores any original, kills tmux session
```

### Nod detection (`detectNod`)

Looks at the last 20 frames of nose Y-position. A nod is confirmed when:
- The peak displacement from baseline exceeds 40px (at capture resolution)
- The nose returns at least 20px back toward baseline by the end of the window

### Shake detection (`detectShake`)

Looks at the last 16+ frames of nose X-position. A shake is confirmed when:
- There are at least 2 direction reversals in the velocity signal
- Total horizontal spread exceeds 45px

### Camera selection

On macOS, iPhone Continuity Camera can insert itself as a higher-priority device and shift OpenCV's index mapping. `find_builtin_camera()` uses PyObjC to query `AVCaptureDeviceDiscoverySession` and finds the device explicitly typed as `AVCaptureDeviceTypeBuiltInWideAngleCamera`, then returns its position index for use with `cv2.VideoCapture()`.

---

## Files

| File | Purpose |
|------|---------|
| `launch.sh` | Entry point — sets up tmux, injects CLAUDE.md, runs FaceTracker |
| `FaceTracking/FaceTracker.py` | Tkinter overlay window, buttons, main display loop |
| `FaceTracking/FaceTrackerModule.py` | All logic — camera selection, detection, gestures, tmux relay |
| `FaceTracking/face_landmarker.task` | MediaPipe model file (bundled) |
| `CLAUDE.md` | Instructions injected into target projects |
