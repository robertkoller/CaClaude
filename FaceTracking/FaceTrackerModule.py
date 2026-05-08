import os
import subprocess
import cv2
import mediapipe as mp

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'face_landmarker.task')

# Key landmark indices
NOSE_TIP     = 4
FACE_OUTLINE = [10,338,297,332,284,251,389,356,454,323,361,288,
                397,365,379,378,400,377,152,148,176,149,150,136,
                172,58,132,93,234,127,162,21,54,103,67,109]

BLINK_THRESHOLD = 0.4

# Gesture to key sent to Claude
TMUX_SESSION = 'caclaude'
GESTURE_MAP  = {
    'nod_a':   '1',
    'shake_a': '2',
    'nod_b':   '3',
    'shake_b': '4',
}


_EXTERNAL_KEYWORDS = ('iphone', 'ipad', 'continuity', 'android', 'droidcam')

def find_builtin_camera():
    try:
        from cv2_enumerate_cameras import enumerate_cameras
        import cv2
        for cam in enumerate_cameras(cv2.CAP_AVFOUNDATION):
            if not any(k in cam.name.lower() for k in _EXTERNAL_KEYWORDS):
                return cam.index
    except Exception:
        pass
    return 0


def send_to_tmux(text, session=TMUX_SESSION):
    subprocess.run(['tmux', 'send-keys', '-t', session, text, 'Enter'],
                   capture_output=True)


def hud(img, text, pos, scale, color, thickness=2):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_PLAIN, scale, (0, 0, 0), thickness + 2)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_PLAIN, scale, color, thickness)


class FaceDetector():
    def __init__(self, detectionCon=0.5, modelPath=_MODEL_PATH):
        self.results = None
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=modelPath),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=detectionCon,
            min_face_presence_confidence=detectionCon,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=False,
        )
        self.detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def findFace(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)
        self.results = self.detector.detect(mp_image)

        if draw and self.results.face_landmarks:
            h, w, _ = img.shape
            lms = self.results.face_landmarks[0]
            pts = [(int(lms[i].x * w), int(lms[i].y * h)) for i in FACE_OUTLINE]
            for i in range(len(pts)):
                cv2.line(img, pts[i], pts[(i + 1) % len(pts)], (0, 200, 0), 1)
            nx, ny = int(lms[NOSE_TIP].x * w), int(lms[NOSE_TIP].y * h)
            cv2.circle(img, (nx, ny), 6, (0, 255, 255), cv2.FILLED)
        return img

    def getNoseTip(self, img):
        if not self.results or not self.results.face_landmarks:
            return None
        h, w, _ = img.shape
        lm = self.results.face_landmarks[0][NOSE_TIP]
        return int(lm.x * w), int(lm.y * h)

    def getEyeStates(self):
        if not self.results or not self.results.face_blendshapes:
            return None, None
        scores = {b.category_name: b.score for b in self.results.face_blendshapes[0]}
        # Image is flipped, so mediapipe's Left = user's Right and vice versa
        left_open  = scores.get('eyeBlinkRight', 0) < BLINK_THRESHOLD
        right_open = scores.get('eyeBlinkLeft',  0) < BLINK_THRESHOLD
        return left_open, right_open

    def faceDetected(self):
        return bool(self.results and self.results.face_landmarks)


class HeadGestureController():
    def __init__(self):
        self.noseHistory     = []
        self.gestureCooldown = 0
        self.lastGesture     = ''

    def update(self, noseTip, leftEyeOpen=True, rightEyeOpen=True):
        if self.gestureCooldown > 0:
            self.gestureCooldown -= 1

        right_wink = leftEyeOpen and not rightEyeOpen
        left_wink  = not leftEyeOpen and rightEyeOpen

        if noseTip is None or not (right_wink or left_wink):
            self.noseHistory.clear()
            return None

        self.noseHistory.append(noseTip)
        if len(self.noseHistory) > 30:
            self.noseHistory.pop(0)

        if self.gestureCooldown > 0:
            return None

        xs     = [p[0] for p in self.noseHistory]
        ys     = [p[1] for p in self.noseHistory]
        suffix = '_a' if right_wink else '_b'

        if detectNod(ys):
            self.lastGesture     = f'NOD{suffix.upper()}'
            self.gestureCooldown = 45
            self.noseHistory.clear()
            return f'nod{suffix}'

        if detectShake(xs):
            self.lastGesture     = f'SHAKE{suffix.upper()}'
            self.gestureCooldown = 45
            self.noseHistory.clear()
            return f'shake{suffix}'

        return None


def detectNod(yHistory, dip=40, window=20):
    if len(yHistory) < window:
        return False
    segment  = yHistory[-window:]
    baseline = segment[0]
    peak     = max(segment)
    end      = segment[-1]
    return peak - baseline > dip and peak - end > dip * 0.5


def detectShake(xHistory, amplitude=45, reversals=2):
    if len(xHistory) < 16:
        return False
    velocities   = [xHistory[i + 1] - xHistory[i] for i in range(len(xHistory) - 1)]
    sign_changes = sum(1 for i in range(len(velocities) - 1)
                       if velocities[i] * velocities[i + 1] < 0)
    spread = max(xHistory) - min(xHistory)
    return sign_changes >= reversals and spread > amplitude
