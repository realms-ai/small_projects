#!/usr/bin/env python3
import psutil
import subprocess
import time
import os
from datetime import datetime

LOWEST_BATTERY_THRESHOLD = 21       # %
LOW_BATTERY_THRESHOLD = 81          # %
FULL_BATTERY_THRESHOLD = 98         # %
MAX_FULL_DURATION = 90 * 60         # 90 minutes
CHECK_INTERVAL = 60                 # seconds
previous_plugged = None
LOG_FILE = os.path.expanduser("/tmp/battery_alerter.log")

zenity_process = None
time_at_full = 0
mode = "normal"  # or 'waiting_discharge'

def log_event(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')

def close_alert():
    global zenity_process
    if zenity_process and zenity_process.poll() is None:
        zenity_process.terminate()
        try:
            zenity_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            zenity_process.kill()
        zenity_process = None

def show_alert(message):
    global zenity_process
    close_alert()
    zenity_process = subprocess.Popen(['zenity', '--warning', '--timeout=10', '--text', message])


while True:
    battery = psutil.sensors_battery()
    percent = battery.percent
    plugged = battery.power_plugged
    
    # Log charger plug/unplug event
    if previous_plugged is not None and plugged != previous_plugged:
        state = "Plugged in" if plugged else "Unplugged"
        log_event(f"{state} at {percent}%")
    previous_plugged = plugged

    # Case: Plugged in and 100% charged
    if plugged and percent >= FULL_BATTERY_THRESHOLD:
        time_at_full += CHECK_INTERVAL
        if time_at_full >= MAX_FULL_DURATION and mode == "full":
            show_alert("⚠️ Battery has been at 100% for 90 minutes.\nPlease unplug the charger.")
            mode = "waiting_discharge"
    elif plugged and percent < 100:
        time_at_full = 0

    # Case: Discharge mode after full
    if not plugged and mode == "waiting_discharge":
        mode = "normal"
        time_at_full = 0

    # Standard lowest battery alert
    if not plugged and percent <= LOWEST_BATTERY_THRESHOLD and mode == "normal":
        show_alert(f"⚠️ Battery is too low ({percent}%). Please plug in the charger immediately!")
        
    # Standard low battery alert        
    elif not plugged and percent <= LOW_BATTERY_THRESHOLD and mode == "normal":
        show_alert(f"⚠️ Battery is at ({percent}%). Please plug in the charger to increase the battery life!")    

    # Standard full alert
    elif plugged and percent >= FULL_BATTERY_THRESHOLD and mode == "normal":
        mode="full"

    elif percent < FULL_BATTERY_THRESHOLD and percent > LOW_BATTERY_THRESHOLD and mode == "normal":
        close_alert()

    time.sleep(CHECK_INTERVAL)
