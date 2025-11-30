import logging
import os
import json
from flask import Flask, request, jsonify, render_template, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

# MATLAB integration (optional; falls back to Python if unavailable)
try:
    from matlab_integration import estimate_with_matlab
    MATLAB_AVAILABLE = True
except ImportError:
    MATLAB_AVAILABLE = False
    logger_init = logging.getLogger(__name__)
    logger_init.info("[APP] MATLAB integration not available; using Python-only digital twin.")

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store latest data per battery_id
latest_data = {}

# Simple user store path
USERS_PATH = 'users.json'

def load_users():
    if not os.path.exists(USERS_PATH):
        return []
    try:
        with open(USERS_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_users(users):
    with open(USERS_PATH, 'w') as f:
        json.dump(users, f, indent=2)

def find_user(username):
    users = load_users()
    for u in users:
        if u.get('username') == username:
            return u
    return None

def get_batteries_for_company(company):
    users = load_users()
    ids = set()
    for u in users:
        if u.get('company') == company and u.get('battery_id'):
            ids.add(u.get('battery_id'))
    return list(ids)

# ----------------- 🧠 Digital Twin Logic (MATLAB + Python Fallback) -----------------
def estimate_dte_and_soh(data: dict) -> dict:
    """
    Cloud-side digital twin with MATLAB advanced modeling + Python fallback:
    - Calls MATLAB for temperature-aware, aging-aware battery estimation if available
    - Falls back to simple Python logic if MATLAB unavailable (graceful degradation)
    - Returns DTE, remaining energy, SoH, and health category
    """

    # Extract battery data
    voltage = float(data.get("voltage_V", 48.0))
    current = float(data.get("current_A", 0.0))
    soc = float(data.get("soc_percent", 50.0))
    soh = float(data.get("soh_percent", 100.0))
    temperature = float(data.get("temperature_C", 25.0))  # Celsius

    # Use MATLAB if available; otherwise Python fallback
    if MATLAB_AVAILABLE:
        try:
            matlab_result = estimate_with_matlab(voltage, current, soc, soh, temperature)
            data["dte_km"] = round(matlab_result.get("dte_km", 0.0), 1)
            data["soh_refined"] = round(matlab_result.get("soh_refined", soh), 1)
            data["health_estimate"] = matlab_result.get("health_estimate", "Unknown")
            data["remaining_energy_kwh"] = round(
                matlab_result.get("remaining_energy_wh", 0.0) / 1000.0, 2
            )
            data["estimation_source"] = matlab_result.get("source", "matlab_engine")
            app.logger.info(f"[DIGITAL TWIN] MATLAB estimation: DTE={data['dte_km']} km, "
                           f"SoH={data['soh_refined']}%, Health={data['health_estimate']}")
        except Exception as e:
            app.logger.warning(f"[DIGITAL TWIN] MATLAB call failed, falling back to Python: {e}")
            _estimate_dte_and_soh_python(data)
    else:
        _estimate_dte_and_soh_python(data)

    # ensure battery_id present
    if "battery_id" not in data or data.get('battery_id') is None:
        data['battery_id'] = data.get('battery_id', 'unknown')

    return data


def _estimate_dte_and_soh_python(data: dict) -> None:
    """
    Python-only fallback for DTE/SoH estimation (simple logic, no MATLAB dependency)
    Updates data dict in-place
    """
    # Assumed battery pack specs
    NOMINAL_PACK_VOLTAGE = 48.0    # Volts
    NOMINAL_CAPACITY_AH = 100.0    # Ah
    WH_PER_KM = 150.0              # Wh/km (vehicle consumption)

    soc = float(data.get("soc_percent", 50.0))
    soh = float(data.get("soh_percent", 100.0))

    # Effective capacity considering SoH
    effective_capacity_ah = NOMINAL_CAPACITY_AH * (soh / 100.0)

    # Remaining energy in Wh
    remaining_energy_wh = NOMINAL_PACK_VOLTAGE * effective_capacity_ah * (soc / 100.0)

    # Distance to Empty
    dte_km = remaining_energy_wh / WH_PER_KM if WH_PER_KM > 0 else 0.0

    data["remaining_energy_kwh"] = round(remaining_energy_wh / 1000.0, 2)
    data["dte_km"] = round(dte_km, 1)
    data["soh_refined"] = round(soh, 1)
    data["health_estimate"] = "Standard"
    data["estimation_source"] = "python_fallback"

    app.logger.info(f"[DIGITAL TWIN] Python fallback: DTE={data['dte_km']} km, "
                   f"SoH={data['soh_refined']}%")

# ----------------- ☁️ Cloud API -----------------

@app.route("/api/battery-data", methods=["POST"])
def receive_battery_data():
    global latest_data
    incoming = request.get_json()

    if not incoming:
        return jsonify({"error": "No JSON body provided"}), 400

    # Attach server processing timestamp
    incoming["server_timestamp"] = datetime.now(timezone.utc).isoformat()

    # Run through digital twin engine
    processed = estimate_dte_and_soh(incoming)
    bid = processed.get('battery_id', 'unknown')
    latest_data[bid] = processed

    # Removed print for performance; uncomment for debugging
    # print("[API] Received + processed:", latest_data)
    return jsonify({"status": "ok"}), 200


@app.route("/api/latest", methods=["GET"])
def get_latest():
    # Require login to fetch latest data
    if 'username' not in session:
        return jsonify({"error": "Authentication required"}), 401

    user = find_user(session.get('username'))
    if not user:
        return jsonify({"error": "User not found"}), 401

    role = user.get('role', 'user')

    if role == 'company':
        # return all batteries for this company
        company = user.get('company')
        ids = get_batteries_for_company(company)
        result = {bid: latest_data.get(bid) for bid in ids if bid in latest_data}
        return jsonify(result), 200
    else:
        # regular user: return their assigned battery
        bid = user.get('battery_id')
        if not bid:
            return jsonify({"error": "No battery assigned to user"}), 404
        if bid not in latest_data:
            return jsonify({"message": "No data yet for user's battery"}), 200
        return jsonify(latest_data[bid]), 200


@app.route("/api/welcome", methods=["GET"])
def welcome():
    logger.info(f"Request: {request.method} {request.path}")
    return jsonify({"message": "Welcome to the Flask API Service!"}), 200


@app.route("/api/mode", methods=["GET"])
def get_mode():
    try:
        with open("mode.txt", "r") as f:
            mode = f.read().strip()
        return jsonify({"mode": mode}), 200
    except FileNotFoundError:
        return jsonify({"mode": "driving"}), 200


@app.route("/api/mode", methods=["POST"])
def set_mode():
    data = request.get_json()
    if not data or "mode" not in data:
        return jsonify({"error": "Mode not specified"}), 400
    mode = data["mode"]
    if mode not in ["driving", "charging"]:
        return jsonify({"error": "Invalid mode"}), 400
    with open("mode.txt", "w") as f:
        f.write(mode)
    print(f"Mode set to: {mode}")
    return jsonify({"status": "ok", "mode": mode}), 200


# ----------------- 📊 Dashboard & Auth Routes -----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    # POST
    username = request.form.get('username') or (request.json and request.json.get('username'))
    password = request.form.get('password') or (request.json and request.json.get('password'))
    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400
    user = find_user(username)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    if not check_password_hash(user.get('password_hash',''), password):
        return jsonify({"error": "Invalid username or password"}), 401
    # Set session
    session['username'] = username
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    username = request.form.get('username') or (request.json and request.json.get('username'))
    password = request.form.get('password') or (request.json and request.json.get('password'))
    company = request.form.get('company') or (request.json and request.json.get('company'))
    role = request.form.get('role') or (request.json and request.json.get('role')) or 'user'
    battery_id = request.form.get('battery_id') or (request.json and request.json.get('battery_id'))

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    if find_user(username):
        return jsonify({"error": "User already exists"}), 400

    users = load_users()
    new = {
        'username': username,
        'password_hash': generate_password_hash(password),
        'company': company,
        'role': role,
        'battery_id': battery_id
    }
    users.append(new)
    save_users(users)
    session['username'] = username
    return redirect('/')


@app.route("/")
def dashboard():
    # Require login for dashboard
    if 'username' not in session:
        # Show the login page at root so users can access login without a redirect
        return render_template('login.html')
    return render_template("dashboard.html")


if __name__ == "__main__":
    # When deploying, honor environment variables for host/port and debug
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug_env = os.environ.get('FLASK_DEBUG', '')
    debug = True if debug_env.lower() in ['1', 'true', 'yes', 'on'] else False
    app.run(host=host, port=port, debug=debug)
