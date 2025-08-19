import time
import numpy as np
import cv2
from picamera2 import Picamera2
import board
import neopixel
import mediapipe as mp
import RPi.GPIO as GPIO
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import threading

# --- 하드웨어 설정 ---
NUM_PIXELS = 9
PIXEL_PIN = board.D18
MODE_SIZE_THRESHOLD = 12000
k = 0.7
IR_SENSOR_PIN = 2

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(IR_SENSOR_PIN, GPIO.IN)

# NeoPixel 준비
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=k, auto_write=True)

# Picamera2 준비
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(camera_config)
picam2.start()
time.sleep(2)

# MediaPipe 초기화
mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

MODE = {"a1": (255, 255, 255), "a2": (255, 200, 100), "a3": (100, 100, 255),"a4":(237, 0, 133), "a5": (160, 212, 104), "off": (0, 0, 0)}
brightness = 0

# EAR 계산 함수
def get_ear(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

eye_closed_start = None
eye_closed_duration = 0
last_blink_time = 0

# 깜빡임 함수
def blink_party(duration=10, interval=0.3):
    end_time = time.time() + duration
    colors = [
    (255, 0, 0),     # 빨강
    (0, 255, 0),     # 초록
    (0, 0, 255),     # 파랑
    (255, 255, 0),   # 노랑
    (0, 255, 255),   # 청록
    (255, 0, 255),   # 보라
    (255, 255, 255)  # 흰색
    ]
    color_index = 0

    while time.time() < end_time:
        color = colors[color_index % len(colors)]
        pixels.fill(color)
        pixels.show()
        time.sleep(interval)

        pixels.fill((0, 0, 0))
        pixels.show()
        time.sleep(interval)

        color_index += 1

def blink_red(duration=10, interval=0.3):
    end_time = time.time() + duration
    while time.time() < end_time:
        pixels.fill((255, 0, 0))
        pixels.show()
        time.sleep(interval)

        pixels.fill((0, 0, 0))
        pixels.show()
        time.sleep(interval)


def blink_morning(duration=10, interval=0.3):
    end_time = time.time() + duration
    while time.time() < end_time:
        pixels.fill((255, 255, 255))
        pixels.show()
        time.sleep(interval)

        pixels.fill((0, 0, 0))
        pixels.show()
        time.sleep(interval)


def count_fingers(hand_landmarks, hand_label):
    finger_tips = [4, 8, 12, 16, 20]
    finger_status = []

    if hand_label == "Right":
        finger_status.append(hand_landmarks.landmark[finger_tips[0]].x < hand_landmarks.landmark[finger_tips[0] - 1].x)
    else:
        finger_status.append(hand_landmarks.landmark[finger_tips[0]].x > hand_landmarks.landmark[finger_tips[0] - 1].x)

    for tip in finger_tips[1:]:
        finger_status.append(hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip - 2].y)
    
    return finger_status.count(True)

def get_hand_area(hand_landmarks, img_shape):
    h, w, _ = img_shape
    points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]
    return cv2.contourArea(cv2.convexHull(np.array(points)))

# Update clock label
def update_clock():
    current_time = time.strftime("%H:%M:%S")
    clock_label.config(text=current_time)
    clock_label.after(1000, update_clock)

# Set alarm
def set_alarm():
    t = threading.Thread(target=check_alarm)
    mode = mode_var.get()
    t.daemon = True
    t.start()
    messagebox.showinfo("Alarm Set", f"Alarm is set for {alarm_time.get()} in {mode} mode")

ranonce = False
def check_alarm():
    global ranonce
    now = datetime.now().strftime("%H:%M")
    mode = mode_var.get()
    if now == alarm_time.get():
        messagebox.showinfo("Wake Up!", f"Alarm {mode}")
        blink_funcs = {
            "party": blink_party,
            "red": blink_red,
            "morning": blink_morning
        }
        if mode in blink_funcs:
            blink_funcs[mode](duration=10, interval=0.3)
        ranonce = True
def setup_gui():
    global clock_label, alarm_time, window, mode_var, mode
    # Create main window
    window = tk.Tk()
    w, h = window.winfo_screenwidth(), window.winfo_screenheight()
    window.title("Clock with Alarm")
    window.geometry("1000x800")

    # Clock label
    clock_label = tk.Label(window, text="", font=("Noto Sans", 80))
    clock_label.pack(pady=100)

    # Alarm time entry
    alarm_time = tk.StringVar()
    alarm_entry = tk.Entry(window, textvariable=alarm_time, font=("Noto Sans", 40), justify="center")
    alarm_entry.insert(0, "07:00")  # Default alarm time
    alarm_entry.pack()
    
    # Mode selection
    mode_var = tk.StringVar(value="morning")
    alarm_mode_label = tk.OptionMenu(window, mode_var, "party", "red", "morning")
    alarm_mode_label.config(font=("Noto Sans", 20))
    alarm_mode_label.pack(pady=10)
    alarm_mode_label.place(x=w//2 - 500, y=h//2 - 100)

    # Set button
    set_button = tk.Button(window, text="Set Alarm", command=set_alarm)
    set_button.pack(pady=180)
    set_button.place(x=w//2 - 500, y=h//2 + 100)

    return window
windo = setup_gui()
update_clock()
windo.mainloop()
try:
    while True:
        if not ranonce:
            check_alarm()
        frame = picam2.capture_array()
        frame = cv2.flip(frame, 0)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape

        if GPIO.input(IR_SENSOR_PIN) == 0:
            print("IR sensor triggered")
            pixels.fill(MODE["a1"])
        # 얼굴 및 손 인식
        face_results = face_mesh.process(rgb_frame)
        hand_results = hands.process(rgb_frame)

        # --- 얼굴 (눈 감음 감지) ---
        if face_results.multi_face_landmarks:
            landmarks = face_results.multi_face_landmarks[0]

            def get_eye_coords(indices):
                return np.array([
                    (int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h))
                    for i in indices
                ], dtype=np.float32)

            left_eye = get_eye_coords(LEFT_EYE_IDX)
            right_eye = get_eye_coords(RIGHT_EYE_IDX)
            ear = (get_ear(left_eye) + get_ear(right_eye)) / 2.0

            if ear < 0.2:
                if eye_closed_start is None:
                    eye_closed_start = time.time()
                if time.time() - last_blink_time > 1:
                    last_blink_time = time.time()
                    eye_closed_duration = time.time() - eye_closed_start
            else:
                if eye_closed_duration > 0 and time.time() - last_blink_time > 1:
                    eye_closed_start = None
                    eye_closed_duration = 0

            if eye_closed_duration >= 6:
                pixels.fill((0, 0, 0))
                print("sleep")
                continue  # 조명 꺼진 상태에서 손가락도 무시

        # --- 손 인식 및 NeoPixel 제어 ---
        if hand_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                    hand_results.multi_hand_landmarks,
                    hand_results.multi_handedness):
                label = handedness.classification[0].label
                finger_count = count_fingers(hand_landmarks, label)
                print(f"Detected {finger_count} fingers on {label} hand.")
                area = get_hand_area(hand_landmarks, frame.shape)
                if area > MODE_SIZE_THRESHOLD:
                    if label == "Left" and 1 <= finger_count <= 5:
                        mode_key = f"a{finger_count}"
                        if mode_key in MODE:
                            pixels.fill(MODE[mode_key])
                    elif label == "Right":
                        if finger_count == 0:
                            pixels.fill(MODE["off"])
                        elif 1 <= finger_count <= 5:
                            k = finger_count / 5
                            pixels.brightness = k
                            pixels.show()

except KeyboardInterrupt:
    print("종료됨")

finally:
    pixels.fill((0, 0, 0))
    picam2.close()
    cv2.destroyAllWindows()
    GPIO.cleanup()
