import cv2
from ultralytics import YOLO
import time
import threading
import requests
import urllib.request
import numpy as np
from datetime import datetime

# Set Cam IP address
cam_ip = '172.20.10.2:8080'

# ─── Schedule state ────────────────────────────────────────────────────────────
schedule_thread = None
schedule_stop_event = threading.Event()


def cam_connect():
    url = f'http://{cam_ip}/'
    message = 'Python connected to ESP32CAM'
    print("Attempting to connect to CAM")
    try:
        response = requests.post(url, data={'message': message})
        print(response.text)
        FLASHOFFresponse = requests.post(url, data={'message': 'FLASHOFF'})
        print(FLASHOFFresponse.text)
    except:
        print("Error: Could not connect to CAM.")


def flash(status):
    url = f'http://{cam_ip}/'
    if status == 'on' or status == 'ON':
        FLASHONresponse = requests.post(url, data={'message': 'FLASHON'})
        print(FLASHONresponse.text)
    else:
        FLASHOFFresponse = requests.post(url, data={'message': 'FLASHOFF'})
        print(FLASHOFFresponse.text)


def send_feed_command(portion):
    url = f'http://{cam_ip}/'
    try:
        FEEDresponse = requests.post(url, data={'message': portion})
        print(FEEDresponse.text)
    except:
        print("Error: FEED command not sent.")
        return
    if portion == 'LARGE':
        time.sleep(8)
    elif portion == 'MED':
        time.sleep(6)
    else:
        time.sleep(1)


# ─── Interval schedule ─────────────────────────────────────────────────────────

def _interval_worker(interval_seconds, portion_getter, stop_event):
    print(f"Interval schedule started: every {interval_seconds}s")
    while not stop_event.wait(interval_seconds):
        portion = portion_getter()
        print(f"Interval schedule: feeding {portion}")
        send_feed_command(portion)
    print("Interval schedule stopped")


# ─── Time-of-day schedule ──────────────────────────────────────────────────────

def _timed_worker(times_list, portion_getter, stop_event):
    print(f"Timed schedule started: {times_list}")
    fired_today = set()

    while not stop_event.is_set():
        now = datetime.now()
        today_key = now.strftime("%Y-%m-%d")
        current_hm = now.strftime("%H:%M")

        if not fired_today or not list(fired_today)[0].startswith(today_key):
            fired_today = set()

        for t in times_list:
            tag = f"{today_key}_{t}"
            if current_hm == t and tag not in fired_today:
                portion = portion_getter()
                print(f"Timed schedule: {t} → feeding {portion}")
                send_feed_command(portion)
                fired_today.add(tag)

        stop_event.wait(20)

    print("Timed schedule stopped")


# ─── Schedule control ──────────────────────────────────────────────────────────

def start_schedule(settings):
    global schedule_thread, schedule_stop_event

    stop_schedule()
    schedule_stop_event = threading.Event()

    mode = settings.get("schedule_mode")

    if mode == "interval":
        interval = int(settings.get("interval_seconds", 3600))
        portion_getter = lambda: settings.get("schedule_portion", "SMALL")
        schedule_thread = threading.Thread(
            target=_interval_worker,
            args=(interval, portion_getter, schedule_stop_event),
            daemon=True
        )
        schedule_thread.start()

    elif mode == "timed":
        times = settings.get("feed_times", [])
        if not times:
            print("No feed times configured, schedule not started")
            return
        portion_getter = lambda: settings.get("schedule_portion", "SMALL")
        schedule_thread = threading.Thread(
            target=_timed_worker,
            args=(times, portion_getter, schedule_stop_event),
            daemon=True
        )
        schedule_thread.start()

    else:
        print("Schedule mode is 'off', no schedule started")


def stop_schedule():
    global schedule_thread, schedule_stop_event
    if schedule_thread and schedule_thread.is_alive():
        print("Stopping existing schedule...")
        schedule_stop_event.set()
        schedule_thread.join(timeout=5)
    schedule_thread = None


def schedule_is_running():
    return schedule_thread is not None and schedule_thread.is_alive()


# ─── Video stream ──────────────────────────────────────────────────────────────

def generate_frames(pet_id, accuracy):
    model = YOLO("yolov8n.pt")
    url = f'http://{cam_ip}/cam-mid.jpg'

    ret = True
    while ret:
        img_resp = urllib.request.urlopen(url)
        imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        im = cv2.imdecode(imgnp, -1)

        detections = model(im)[0]
        for detection in detections.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = detection

            if int(class_id) == pet_id:
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                score_val = round(score, 2)
                score_str = str(score_val)

                cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(im, score_str, (x1 + 40, y1 - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 4)

                if score_val >= accuracy:
                    if int(class_id) == 14:
                        label = "Bird Detected"
                    elif int(class_id) == 15:
                        label = "Cat Detected"
                    else:
                        label = "Dog Detected"
                    cv2.putText(im, label, (x1 + 40, y2 + 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 4)
                    print("FOUND")

        ret, buffer = cv2.imencode('.jpg', im)
        im = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + im + b'\r\n')


def calc_delay(seconds, minutes, hours):
    seconds = int(seconds) if str(seconds).isdigit() else 0
    minutes = int(minutes) if str(minutes).isdigit() else 0
    hours = int(hours) if str(hours).isdigit() else 0
    return seconds + (minutes * 60) + (hours * 3600)