import os
import cv2
import HandTrackerModule as htm
import time

ratioW = 16
ratioH = 9

camScalar = 120 # 120 = 1920:1080

widthCam, heightCam = ratioW * camScalar, ratioH * camScalar

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, widthCam)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, heightCam)

handDetector = htm.handDetector()
pTime = 0

while True:
    success, img = cap.read()
    if not success:
        print("Failed to grab frame — check camera permissions or try VideoCapture(1)")
        break

    img = cv2.resize(img, (widthCam, heightCam))


    img = handDetector.findHands(img)
    lmList = handDetector.findPosition(img)
    htm.relayHandGestures(lmList)

    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime

    cv2.putText(img, str(int(fps)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3,
                    (255, 0, 255), 3)

    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()