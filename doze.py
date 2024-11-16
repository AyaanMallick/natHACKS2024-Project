from scipy.spatial import distance as dist
from imutils.video import VideoStream
from imutils import face_utils
from threading import Thread
import numpy as np
import argparse
import imutils
import time
import cv2
import os
import dlib
import math

# Alarm function to just print the messages
def alarm(msg):
    global alarm_status
    global alarm_status2
    global saying

    # Remove espeak and just print the message
    print(msg)  # This will print the alarm message instead of using espeak

    if alarm_status2:
        saying = True
        print(msg)  # Print the message again if the second alarm is triggered
        saying = False

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])

    C = dist.euclidean(eye[0], eye[3])

    ear = (A + B) / (2.0 * C)

    return ear

def final_ear(shape):
    (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
    (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

    leftEye = shape[lStart:lEnd]
    rightEye = shape[rStart:rEnd]

    leftEAR = eye_aspect_ratio(leftEye)
    rightEAR = eye_aspect_ratio(rightEye)

    ear = (leftEAR + rightEAR) / 2.0
    return (ear, leftEye, rightEye)

def lip_distance(shape):
    top_lip = shape[50:53]
    top_lip = np.concatenate((top_lip, shape[61:64]))

    low_lip = shape[56:59]
    low_lip = np.concatenate((low_lip, shape[65:68]))

    top_mean = np.mean(top_lip, axis=0)
    low_mean = np.mean(low_lip, axis=0)

    distance = abs(top_mean[1] - low_mean[1])
    return distance

# Function to detect head tilt
def head_tilt_angle(shape):
    chin = shape[8]  # Chin
    nose = shape[30]  # Nose tip

    # Calculate distance between chin and nose
    horizontal_distance = chin[0] - nose[0]
    vertical_distance = (chin[1] - nose[1])

    # Angle calculation (in degrees)
    angle = math.atan2(vertical_distance, horizontal_distance) * 180.0 / math.pi

    # If the angle is negative (head up), we'll consider that as "tilting down" when the angle becomes positive
    return angle
ap = argparse.ArgumentParser()
ap.add_argument("-w", "--webcam", type=int, default=0,
                help="index of webcam on system")
args = vars(ap.parse_args())

EYE_AR_THRESH = 0.3
EYE_AR_CONSEC_FRAMES = 30
YAWN_THRESH = 20
ALERT_TILT_ANGLE = 30  # Degrees, you can change this threshold to match your needs
alarm_status = False
alarm_status2 = False
saying = False
COUNTER = 0
drowsiness_start_time = None  # Variable to track when EAR goes below threshold

print("-> Loading the predictor and detector...")
detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")  # Faster but less accurate
predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

print("-> Starting Video Stream")
vs = VideoStream(src=args["webcam"]).start()
time.sleep(1.0)

while True:
    frame = vs.read()
    frame = imutils.resize(frame, width=450)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    rects = detector.detectMultiScale(gray, scaleFactor=1.1, 
                                      minNeighbors=5, minSize=(30, 30),
                                      flags=cv2.CASCADE_SCALE_IMAGE)

    for (x, y, w, h) in rects:
        rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))
        
        shape = predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)

        eye = final_ear(shape)
        ear = eye[0]
        leftEye = eye[1]
        rightEye = eye[2]

        distance = lip_distance(shape)

        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

        lip = shape[48:60]
        cv2.drawContours(frame, [lip], -1, (0, 255, 0), 1)

        # Detect drowsiness
        if ear < EYE_AR_THRESH:
            COUNTER += 1

            if COUNTER >= EYE_AR_CONSEC_FRAMES:
                if drowsiness_start_time is None:
                    drowsiness_start_time = time.time()

                if time.time() - drowsiness_start_time >= 4:
                    if not alarm_status:
                        alarm_status = True
                        t = Thread(target=alarm, args=('wake up sir',))
                        t.daemon = True
                        t.start()

                    cv2.putText(frame, "DROWSINESS ALERT!", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            COUNTER = 0
            alarm_status = False
            drowsiness_start_time = None

        # Detect yawn
        if distance > YAWN_THRESH:
            cv2.putText(frame, "Yawn Alert", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            if alarm_status2 == False and saying == False:
                alarm_status2 = True
                t = Thread(target=alarm, args=('take some fresh air sir',))
                t.daemon = True
                t.start()
        else:
            alarm_status2 = False


                # Detect head tilt
        tilt_angle = head_tilt_angle(shape)

        # If the head is tilting down past the threshold
        if tilt_angle > ALERT_TILT_ANGLE:  # This means head is tilting down (past the threshold)
            alarm_status2 = True  # Reset the alarm status if tilt angle is within the threshold
        else:
            cv2.putText(frame, "Head Tilt Alert!", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            if alarm_status2 == False and saying == False:
                alarm_status2 = True
            print("Head tilt is over the threshold, triggering alert.")  # Debugging the alert trigger
            t = Thread(target=alarm, args=('your head is falling off, sir!',))
            t.daemon = True
            t.start()



        # Show EAR and yawn values
        cv2.putText(frame, "EAR: {:.2f}".format(ear), (300, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, "YAWN: {:.2f}".format(distance), (300, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cv2.destroyAllWindows()
vs.stop()
