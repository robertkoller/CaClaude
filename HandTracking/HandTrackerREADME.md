# CaClaude Hand Tracker

Control your Mac with hand gestures using a webcam.

## Setup

```bash
source venv/bin/activate
pip install opencv-python mediapipe pyautogui pillow
curl -o Tracking/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
python Tracking/handTracker.py
```

## Hand Roles

| Hand | Role |
|------|------|
| Right hand | Pointer / gesture hand |
| Left hand | Clicker (keyboard mode only) |

---

## Gestures

### App Switcher

| Gesture | Action |
|---------|--------|
| Right hand open palm, swipe **left** | Open AltTab switcher (holds Cmd) |
| Right hand **index finger only** up | Move right in switcher |
| Right hand **thumb only** up | Move left in switcher |
| Right hand open palm, any swipe | Confirm selection (releases Cmd) |
| Right hand open palm, swipe **right** | Go back in current app (`Cmd+[`) |

### Virtual Keyboard

| Gesture | Action |
|---------|--------|
| Both hands open palm, pump toward camera | Toggle keyboard ON / OFF |
| Right hand index fingertip over a key | Hover / highlight key |
| Left hand pinch (thumb + index) | Press the hovered key |

### Keyboard Keys

| Key | Result |
|-----|--------|
| Letter keys | Type that letter |
| `SPACE` | Space |
| `BACK` | Delete |

---

## Quitting

Press `q` while the window is focused, or close the window.

---

## Configuration

Edit the top of `handTracker.py`:

| Variable | Default | Effect |
|----------|---------|--------|
| `ALWAYS_ON_TOP` | `True` | Keep the window floating above all other windows |
| `camScalar` | `120` | Internal processing resolution (`16*camScalar` × `9*camScalar`) |
| `displayScalar` | `30` | Window display size (`16*displayScalar` × `9*displayScalar`) |

Edit `HandTrackerModule.py` to tune gesture sensitivity:

| Parameter | Location | Effect |
|-----------|----------|--------|
| `threshold=1.25` | `detectPump()` | How hard to pump to toggle keyboard (lower = easier) |
| `threshold=100` | `detectSwipe()` | How far to swipe in pixels (lower = easier) |
| `navCooldown = 20` | `_handleNavigation()` | Frames between switcher navigation steps |
