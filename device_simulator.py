import time
import random
import requests
import msvcrt
from datetime import datetime, timezone

SERVER_URL = "http://127.0.0.1:5000/api/battery-data"

# Initial simulated battery state
voltage = 52.0        # V (full)
soc = 20.0            # % (Start at ~20% SOC to trigger DTE ≈ 6-7km early for demo/judges)
temperature = 30.0    # °C
soh = 100.0           # %
speed = 0.0           # km/h
distance = 0.0        # km
time_step_sec = 1.0

# Simulated starting location (e.g., near a city for demo)
latitude = 37.7749   # San Francisco lat
longitude = -122.4194  # San Francisco lng

# Load initial mode from file
try:
    with open("mode.txt", "r") as f:
        mode = f.read().strip()
except FileNotFoundError:
    mode = "driving"

print(f"[SIM] Starting battery + IoT simulator in {mode} mode...")
while True:
    # Load mode from file in each iteration to sync with API changes
    try:
        with open("mode.txt", "r") as f:
            mode = f.read().strip()
    except FileNotFoundError:
        mode = "driving"

    # Check for keyboard input to switch modes
    if msvcrt.kbhit():
        key = msvcrt.getch().decode('utf-8').lower()
        if key == 'c':
            mode = "charging"
            with open("mode.txt", "w") as f:
                f.write(mode)
            print("[SIM] Switched to charging mode")
        elif key == 'd':
            mode = "driving"
            with open("mode.txt", "w") as f:
                f.write(mode)
            print("[SIM] Switched to driving mode")

    # ----- Simple battery behavior model -----
    if mode == "charging":
        # Charging mode: negative current, SoC increases
        current = -random.uniform(10, 20)  # Negative current for charging
        soc_increase = abs(current) * 0.02  # Increase SoC based on charging current
        soc = min(100.0, soc + soc_increase)
        speed = 0.0  # Stationary while charging
    else:
        # Driving mode: positive current, SoC decreases
        current = random.uniform(5, 25)
        soc_drop = current * 0.005  # Reduced drain rate so DTE stays visible longer
        soc = max(0.0, soc - soc_drop)
        # Reset SOC to 100% if it reaches 0% to simulate recharging and continuous demo
        if soc <= 0.0:
            soc = 100.0
        speed = random.uniform(0, 120)



    # Voltage based on SOC (42V at 0% SOC, 52V at 100% SOC)
    voltage = 42.0 + (soc / 100.0) * 10.0

    # SOH slowly decreases (long-term degradation)
    soh = max(70.0, soh - 0.0005)

    # Temperature changes slightly
    temperature += random.uniform(-0.05, 0.2)

    # Simulate distance traveled (km) - only in driving mode
    if mode == "driving":
        distance += speed * (time_step_sec / 3600)  # Convert speed to km per second

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "battery_id": "EV48V_SIM_01",
        "voltage_V": round(voltage, 2),
        "current_A": round(current, 2),
        "temperature_C": round(temperature, 2),
        "soc_percent": round(soc, 2),
        "soh_percent": round(soh, 2),
        "speed_kmph": round(speed, 2),
        "distance_travelled_km": round(distance, 2),
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6)
    }

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=2)
        print("[SIM] Sent:", payload, "| Status:", response.status_code)
    except Exception as e:
        print("[SIM] Error sending data:", e)

    time.sleep(2.0)  # Increased to 2 seconds for better performance
