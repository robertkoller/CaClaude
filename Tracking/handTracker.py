import os
# this stuff is to not clog your terminal
os.environ['GLOG_minloglevel'] = '3'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import HandTrackerModule as htm
import time

ratioW = 16
ratioH = 9

camScalar = 120 # 120 = 1920:1080

widthCam, heightCam = ratioW * camScalar, ratioH * camScalar

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, widthCam)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, heightCam)

handDetector = htm.handDetector(detectionCon = 0.75)

while True:
    success, img = cap.read()
    if not success:
        print("Failed to grab frame — check camera permissions or try VideoCapture(1)")
        break

    img = cv2.resize(img, (widthCam, heightCam))


    img = handDetector.findHands(img)
    hands = handDetector.findPosition(img, draw=False)

    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()