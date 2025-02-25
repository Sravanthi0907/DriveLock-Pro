import cv2
import numpy as np
import pygame
import time

# Initialize pygame for audio alerts
pygame.mixer.init()
audio_path = "1.mp3"
alert_sound = pygame.mixer.Sound(audio_path)

# Video Path
video_path = "1.mp4"
cap = cv2.VideoCapture(video_path)

# Constants
FOCAL_LENGTH = 800
KNOWN_WIDTH = 20
ALERT_DISTANCE = 50
HORIZON_LINE = 200  # Pixels above which objects will be ignored
ROAD_REGION = (100, 400, 300, 700)  # (y1, y2, x1, x2) - Crop only road area

prev_pothole_detected = False
last_alert_time = 0


def process_frame(frame):
    """Performs lane detection and overlay."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    height, width = frame.shape[:2]
    mask = np.zeros_like(edges)
    curve_rect = np.array([[(300, height), (width // 3 + 70, height // 1.6), (2 * width // 3 - 70, height // 1.6),
                            (width - 300, height)]], np.int32)
    cv2.fillPoly(mask, curve_rect, 255)
    masked_edges = cv2.bitwise_and(edges, mask)

    lines = cv2.HoughLinesP(masked_edges, 1, np.pi / 180, 50, minLineLength=100, maxLineGap=50)
    lane_mask = np.zeros_like(frame)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(lane_mask, (x1, y1), (x2, y2), (0, 255, 0), thickness=10)

    lane_overlay = np.zeros_like(frame)
    cv2.fillPoly(lane_overlay, [curve_rect], (50, 205, 50))
    blended = cv2.addWeighted(frame, 0.7, lane_overlay, 0.3, 0)
    cv2.polylines(blended, [curve_rect], isClosed=True, color=(0, 0, 255), thickness=5)
    return blended


def segment_road(frame):
    """Applies refined road masking to eliminate non-road objects."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_gray = np.array([0, 0, 40])
    upper_gray = np.array([180, 50, 180])
    mask = cv2.inRange(hsv, lower_gray, upper_gray)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    segmented = cv2.bitwise_and(frame, frame, mask=mask)
    return segmented, mask


def estimate_distance(width_in_pixels):
    """Improves pothole distance estimation using bounding box width."""
    if width_in_pixels == 0:
        return float("inf")
    distance = (KNOWN_WIDTH * FOCAL_LENGTH) / width_in_pixels
    return max(distance * 0.0833, 5)


def detect_potholes(frame):
    """Detects potholes with optimized filtering and better accuracy."""
    global prev_pothole_detected, last_alert_time

    y1, y2, x1, x2 = ROAD_REGION
    frame = frame[y1:y2, x1:x2]
    road_segment, road_mask = segment_road(frame)
    gray = cv2.cvtColor(road_segment, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    road_only = cv2.bitwise_and(thresh, road_mask)

    contours, _ = cv2.findContours(road_only, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    potholes_detected = False

    for cnt in contours:
        area = cv2.contourArea(cnt)
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            continue
        solidity = area / hull_area
        perimeter = cv2.arcLength(cnt, True)
        circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
        x, y, w, h = cv2.boundingRect(cnt)
        distance = estimate_distance(w)
        if y < HORIZON_LINE:
            continue
        if (400 < area < 10000 and 0.15 < solidity < 0.8 and circularity < 0.6 and distance <= ALERT_DISTANCE):
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, f"POTHOLE ({int(distance)} ft)", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255),
                        2)
            potholes_detected = True
            if not prev_pothole_detected and (time.time() - last_alert_time > 3):
                alert_sound.play()
                last_alert_time = time.time()
    prev_pothole_detected = potholes_detected
    return frame


while True:
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        lane_frame = process_frame(frame)
        pothole_frame = detect_potholes(lane_frame)
        cv2.imshow("Lane & Pothole Detection", pothole_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()
cap.release()
cv2.destroyAllWindows()
