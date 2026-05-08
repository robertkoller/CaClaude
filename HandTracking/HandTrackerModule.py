import os
import math
import cv2
import mediapipe as mp
import pyautogui
import time

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),        # Thumb
    (0,5),(5,6),(6,7),(7,8),        # Index
    (5,9),(9,10),(10,11),(11,12),   # Middle
    (9,13),(13,14),(14,15),(15,16), # Ring
    (13,17),(17,18),(18,19),(19,20),# Pinky
    (0,17)                          # Palm base connection
]

keys = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    list("ZXCVBNM"),
    ["SPACE", "BACK"]
]


class handDetector():
    def __init__(self, maxHands=2, detectionCon=0.5, trackCon=0.5,
                 modelPath=_MODEL_PATH):
        self.results = None

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=modelPath),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_hands=maxHands,
            min_hand_detection_confidence=detectionCon,
            min_tracking_confidence=trackCon
        )
        self.detector = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def findHands(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)
        self.results = self.detector.detect(mp_image)

        if draw and self.results.hand_landmarks:
            h, w, _ = img.shape
            for hand_landmarks in self.results.hand_landmarks:
                for start_idx, end_idx in HAND_CONNECTIONS:
                    start = hand_landmarks[start_idx]
                    end = hand_landmarks[end_idx]
                    cv2.line(img,
                             (int(start.x * w), int(start.y * h)),
                             (int(end.x * w), int(end.y * h)),
                             (0, 255, 0), 2)
                for lm in hand_landmarks:
                    cv2.circle(img, (int(lm.x * w), int(lm.y * h)), 5, (255, 0, 255), cv2.FILLED)
        return img

    def findPosition(self, img, handNo=0, draw=False):
        lmList = []
        if self.results and self.results.hand_landmarks:
            if handNo < len(self.results.hand_landmarks):
                h, w, _ = img.shape
                for id, lm in enumerate(self.results.hand_landmarks[handNo]):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lmList.append([id, cx, cy])
                    if draw:
                        cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
        return lmList

    def findPositionByHandedness(self, img, hand='Right'):
        """Returns lmList for the given hand from the user's perspective.
        Accounts for the horizontally flipped image (flip inverts mediapipe labels)."""
        if not self.results or not self.results.hand_landmarks:
            return []
        mp_label = 'Left' if hand == 'Right' else 'Right'
        h, w, _ = img.shape
        for i, handedness in enumerate(self.results.handedness):
            if handedness[0].category_name == mp_label:
                return [[id, int(lm.x * w), int(lm.y * h)]
                        for id, lm in enumerate(self.results.hand_landmarks[i])]
        return []


class GestureController():
    def __init__(self):
        self.scaleHistory = []
        self.pumpCooldown = 0
        self.wristHistory = []
        self.swipeCooldown = 0
        self.navCooldown = 0
        self.lastSwipe = ''
        self.switcherOpen = False
        self.keyboardActive = False
        self.prevX = 0
        self.prevY = 0
        self.clickCooldown = 0

    def update(self, img, lmRight, lmLeft):
        """Run all gesture logic for the current frame. Returns a status dict for the HUD."""
        self._handlePump(lmRight, lmLeft)
        self._handleSwipe(lmRight)
        if self.switcherOpen:
            self._handleNavigation(lmRight)
        if self.keyboardActive:
            self._handleKeyboard(img, lmRight, lmLeft)

        fingersDebug = ''
        if lmRight:
            fingers = fingersUp(lmRight)
            fingersDebug = f"fingers:{fingers} hist:{len(self.wristHistory)}"

        return {
            'keyboardActive': self.keyboardActive,
            'switcherOpen': self.switcherOpen,
            'lastSwipe': self.lastSwipe,
            'swipeCooldown': self.swipeCooldown,
            'fingersDebug': fingersDebug,
        }

    def release(self):
        """Release any held keys — call on program exit."""
        if self.switcherOpen:
            pyautogui.keyUp('command')

    def _handlePump(self, lmRight, lmLeft):
        if self.pumpCooldown > 0:
            self.pumpCooldown -= 1

        if not self.switcherOpen:
            if lmRight and lmLeft:
                self.scaleHistory.append((getHandScale(lmRight), getHandScale(lmLeft)))
                if len(self.scaleHistory) > 15:
                    self.scaleHistory.pop(0)
                if self.pumpCooldown == 0 and detectPump(self.scaleHistory):
                    self.keyboardActive = not self.keyboardActive
                    self.pumpCooldown = 45
                    self.swipeCooldown = 45
                    self.scaleHistory.clear()
                    self.wristHistory.clear()
            else:
                self.scaleHistory.clear()

    def _handleSwipe(self, lmRight):
        if self.swipeCooldown > 0:
            self.swipeCooldown -= 1

        if lmRight:
            fingers = fingersUp(lmRight)
            if fingers[1:] == [1, 1, 1, 1]:
                self.wristHistory.append(lmRight[0][1])
                if len(self.wristHistory) > 15:
                    self.wristHistory.pop(0)
            else:
                self.wristHistory.clear()
        else:
            self.wristHistory.clear()

        if self.swipeCooldown == 0:
            swipe = detectSwipe(self.wristHistory)
            if swipe and self.switcherOpen:
                # Any swipe while switcher is open = confirm selection
                self.lastSwipe = 'CONFIRM'
                pyautogui.keyUp('command')
                self.switcherOpen = False
                self.swipeCooldown = 40
                self.wristHistory.clear()
            elif swipe == 'right':  # real-world left swipe (image is flipped)
                self.lastSwipe = 'OPEN SWITCHER'
                pyautogui.keyDown('command')
                pyautogui.press('tab')
                self.switcherOpen = True
                self.swipeCooldown = 40
                self.wristHistory.clear()
            elif swipe == 'left':  # real-world right swipe (image is flipped)
                self.lastSwipe = 'GO BACK'
                pyautogui.hotkey('command', '[')
                self.swipeCooldown = 40
                self.wristHistory.clear()

    def _handleNavigation(self, lmRight):
        if self.navCooldown > 0:
            self.navCooldown -= 1
            return
        if not lmRight:
            return
        fingers = fingersUp(lmRight)
        if fingers[1:] == [1, 0, 0, 0]:                    # index only → move right
            pyautogui.press('tab')
            self.navCooldown = 20
        elif fingers[0] == 1 and fingers[1:] == [0, 0, 0, 0]:  # thumb only → move left
            pyautogui.keyDown('shift')
            pyautogui.press('tab')
            pyautogui.keyUp('shift')
            self.navCooldown = 20

    def _handleKeyboard(self, img, lmRight, lmLeft):
        keyList = drawKeyboard(img, keys)

        if not (lmRight and lmLeft):
            return

        x, y = lmRight[8][1], lmRight[8][2]
        smoothX = self.prevX + (x - self.prevX) / 5
        smoothY = self.prevY + (y - self.prevY) / 5
        self.prevX, self.prevY = smoothX, smoothY

        cv2.circle(img, (int(smoothX), int(smoothY)), 10, (0, 255, 255), cv2.FILLED)

        clickDist = findDistance(4, 8, lmLeft)

        if self.clickCooldown > 0:
            self.clickCooldown -= 1

        for key, kx, ky, w, h in keyList:
            if kx < smoothX < kx + w and ky < smoothY < ky + h:
                cv2.rectangle(img, (kx, ky), (kx + w, ky + h), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, key, (kx + 10, ky + 45),
                            cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 2)

                if clickDist < 40 and self.clickCooldown == 0:
                    if key == "SPACE":
                        pyautogui.press("space")
                    elif key == "BACK":
                        pyautogui.press("delete")
                    else:
                        pyautogui.press(key.lower())
                    self.clickCooldown = 10


def fingersUp(lmList):
    fingers = []
    if lmList[4][1] > lmList[3][1]:
        fingers.append(1)
    else:
        fingers.append(0)
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for tip, pip in zip(tips, pips):
        fingers.append(1 if lmList[tip][2] < lmList[pip][2] else 0)
    return fingers

def drawKeyboard(img, keys):
    keyList = []
    boxW, boxH = 70, 70
    gap = 10
    imgH, imgW, _ = img.shape
    maxKeys = max(len(row) for row in keys)
    totalW = maxKeys * (boxW + gap) - gap
    startX = (imgW - totalW) // 2
    startY = int(imgH * 0.62)

    for i, row in enumerate(keys):
        for j, key in enumerate(row):
            if key == "SPACE":
                w = boxW * 5
            elif key == "BACK":
                w = boxW * 2
            else:
                w = boxW
            x = startX + j * (boxW + gap)
            y = startY + i * (boxH + gap)
            cv2.rectangle(img, (x, y), (x + w, y + boxH), (255, 0, 255), 2)
            cv2.putText(img, key, (x + 10, y + 45), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)
            keyList.append((key, x, y, w, boxH))
    return keyList

def findDistance(p1, p2, lmList):
    x1, y1 = lmList[p1][1], lmList[p1][2]
    x2, y2 = lmList[p2][1], lmList[p2][2]
    return math.hypot(x2 - x1, y2 - y1)

def getHandScale(lmList):
    if len(lmList) < 13:
        return 0
    return findDistance(0, 12, lmList)

def detectPump(scaleHistory, window=10, threshold=1.25):
    if len(scaleHistory) < window:
        return False
    s0_start, s1_start = scaleHistory[-window]
    s0_end, s1_end = scaleHistory[-1]
    if s0_start == 0 or s1_start == 0:
        return False
    return s0_end / s0_start > threshold and s1_end / s1_start > threshold

def detectSwipe(posHistory, threshold=100):
    if len(posHistory) < 8:
        return None
    delta = posHistory[-1] - posHistory[-8]
    if delta < -threshold:
        return 'left'
    if delta > threshold:
        return 'right'
    return None
