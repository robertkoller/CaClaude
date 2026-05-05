import cv2

cap = cv2.VideoCapture(0)
success, img = cap.read()
print("success:", success)
if success:
    print("frame shape:", img.shape)
    print("mean pixel value:", img.mean())
cap.release()
