# CaClaude

Hands free control over claude clode so you can vibe whenever or wherever you want ;)

---

## How it works

CaClaude runs a floating overlay window on your camera feed. It tracks your face and hands simultaneously and translates gestures into keystrokes sent directly to a Claude Code tmux session. Claude is instructed to end every response with a numbered menu (1–4), so you navigate by gesture instead of typing.

**Face gestures** select numbered options:
- Right wink + nod → sends `1`
- Right wink + shake → sends `2`
- Left wink + nod → sends `3`
- Left wink + shake → sends `4`

**Hand gestures** control the OS:
- Both hands pump (open → close) → toggle virtual keyboard
- Four fingers extended + swipe left → open app switcher (Cmd+Tab)
- Swipe again to confirm selection → release Cmd
- Four fingers + swipe right → go back (Cmd+[)
- While switcher open: index finger → Tab (next), thumb → Shift+Tab (previous)

---

## Setup

**Prerequisites:** Python 3, pip, tmux

```bash
# Clone and create a virtual environment
git clone https://github.com/yourname/CaClaude
cd CaClaude
python3 -m venv venv
source venv/bin/activate
pip install opencv-python mediapipe pillow pyautogui pyobjc-framework-AVFoundation
```

**Add the `caclaude` alias** (already in `~/.zshrc` if you ran setup):

```bash
echo "alias caclaude='bash ~/CodingProjects/CaClaude/scripts/launch.sh'" >> ~/.zshrc
source ~/.zshrc
```

---

## Usage

```bash
# Launch in the current project directory
caclaude

# Launch in a specific project
caclaude ~/myproject
```

What happens on launch:
1. A `CLAUDE.md` is injected into the target project directory (instructing Claude to use numbered menus). The original is restored on exit.
2. A tmux session named `caclaude` starts with Claude Code running in the project.
3. A Terminal window opens attached to that session.
4. The gesture overlay window appears (floating, always on top by default).

Close the overlay window or press `q` to end the session cleanly.

---

## Overlay window

The overlay shows your camera feed with gesture overlays drawn on top.

**Buttons (bottom bar):**

| Button | Default | What it does |
|--------|---------|--------------|
| CAM | On | Show/hide the camera feed |
| HUD | On | Show/hide face wireframe, hand skeleton, and status text |
| TOP | On | Toggle always-on-top |

The window is resizable — everything scales with it.

**Status dot (top-right corner):**
- Green = face detected
- Red = no face detected

**HUD text:**
- Top-left: FPS
- Below FPS: active gesture mode (e.g. `R-WINK  NOD=1  SHAKE=2`)
- Below that: last option sent to Claude (e.g. `-> 1`)
- Gesture flash: large colored text when a gesture fires (green for nod, blue for shake)
- Bottom-left: keyboard mode status, swipe/switcher status

---

## Gesture reference

### Face gestures

Winking activates gesture mode. While winking, move your head:

| Wink | Motion | Sends | Claude action |
|------|--------|-------|---------------|
| Right wink | Nod down | `1` | Option 1 |
| Right wink | Shake left/right | `2` | Option 2 |
| Left wink | Nod down | `3` | Option 3 |
| Left wink | Shake left/right | `4` | Option 4 |

Tips:
- Hold the wink while performing the motion — releasing too early resets the detector.
- Nod = dip your chin and bring it back up.
- Shake = move your head left, right, left (two reversals minimum).
- There is a cooldown after each gesture fires to prevent double-sends.

### Hand gestures

All hand gestures use your **right hand** (from your perspective). The left hand is used for keyboard click detection.

| Gesture | Action |
|---------|--------|
| Both hands open → close together (pump) | Toggle virtual keyboard on/off |
| Right hand, 4 fingers up, swipe left (your left) | Open app switcher (Cmd+Tab held) |
| Right hand, 4 fingers up, swipe right (your right) | Go back (Cmd+[) |
| While switcher open: index finger only | Tab to next app |
| While switcher open: thumb only | Shift+Tab to previous app |
| Any 4-finger swipe while switcher is open | Confirm (release Cmd) |

Virtual keyboard: when active, your right index fingertip hovers over keys. Pinch your left thumb and index finger together to click the hovered key.

---

## Project structure

```
CaClaude/
├── tracker.py                  # Main entry point — single combined overlay window
├── scripts/
│   ├── launch.sh               # Launcher: tmux + Terminal + tracker
│   └── CLAUDE.md               # Injected into target projects during sessions
├── FaceTracking/
│   ├── FaceTrackerModule.py    # All face detection logic, gesture detection, utilities
│   ├── FaceTracker.py          # Standalone face-only tracker window
│   └── face_landmarker.task    # MediaPipe model file
└── HandTracking/
    ├── HandTrackerModule.py    # All hand detection and gesture control logic
    ├── handTracker.py          # Standalone hand-only tracker window
    └── hand_landmarker.task    # MediaPipe model file
```

`tracker.py` imports from both modules and runs both detectors on the same camera frame in a single window. Use the standalone trackers (`FaceTracker.py`, `handTracker.py`) to test each system independently.

---

## Architecture

**Input pipeline:**

```
Camera frame → flip horizontal → FaceDetector.findFace() → handDetector.findHands()
     → resize to window → HUD text overlay → tkinter panel
```

Both detectors draw their wireframes directly onto the same `img` array before the final resize. The face wireframe (green outline + cyan nose dot) and hand skeleton (green lines + pink joints) layer on top of each other.

**Gesture → Claude:**

```
HeadGestureController.update() → gesture name → GESTURE_MAP → tmux send-keys -t caclaude
```

`send_to_tmux()` calls `tmux send-keys` directly — no window focus required. The tmux session runs independently and receives keystrokes regardless of what is focused on screen.

**Camera selection:**

On launch, `find_builtin_camera()` uses AVFoundation (PyObjC) to enumerate video devices and find the one with type `AVCaptureDeviceTypeBuiltInWideAngleCamera`. This prevents iPhone Continuity Camera from being selected even when it appears at index 0.

**CLAUDE.md injection:**

`launch.sh` copies `scripts/CLAUDE.md` into the target project before starting Claude, and restores the original on exit via `trap cleanup EXIT`. The CLAUDE.md instructs Claude to always end responses with a numbered 1–4 menu matching the gesture map. When running `caclaude` from inside the CaClaude repo itself, injection is skipped.
