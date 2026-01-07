from flask import (
    Flask, render_template, Response, jsonify,
    send_file, request, redirect, make_response
)
import cv2
import random
import os
import json
import csv
import jwt
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from auth.auth_utils import token_required, admin_required
from auth.auth_routes import auth_bp

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"
app.register_blueprint(auth_bp)

# --------------------------------------------------
# PATHS
# --------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

USERS_PATH = os.path.join(BASE_DIR, "users.json")
ZONES_PATH = os.path.join(BASE_DIR, "zones.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

CSV_PATH = os.path.join(UPLOAD_FOLDER, "logs.csv")
PDF_PATH = os.path.join(UPLOAD_FOLDER, "report.pdf")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------------------
# JSON HELPERS
# --------------------------------------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# --------------------------------------------------
# USERS
# --------------------------------------------------
def load_users():
    return load_json(
        USERS_PATH,
        [
            {"username": "admin", "role": "admin", "status": "inactive", "last_login": None},
            {"username": "operator", "role": "user", "status": "inactive", "last_login": None}
        ]
    )

def save_users(users):
    save_json(USERS_PATH, users)

def update_last_login(username):
    users = load_users()
    for u in users:
        if u["username"] == username:
            u["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            u["status"] = "active"
            break
    save_users(users)

def mark_user_inactive(username):
    users = load_users()
    for u in users:
        if u["username"] == username:
            u["status"] = "inactive"
            break
    save_users(users)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
def load_config():
    return load_json(
        CONFIG_PATH,
        {"alert_enabled": True, "alert_cooldown": 5, "max_logs": 500}
    )

def save_config(cfg):
    save_json(CONFIG_PATH, cfg)

# --------------------------------------------------
# ZONES
# --------------------------------------------------
def load_zones():
    return load_json(ZONES_PATH, [])

def save_zones(zones):
    save_json(ZONES_PATH, zones)

# --------------------------------------------------
# VIDEO
# --------------------------------------------------
cap = cv2.VideoCapture("video/crowd.mp4")

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        zones = load_zones()
        x = 50

        for z in zones:
            if z["status"] != "active":
                continue
            cv2.rectangle(frame, (x, 60), (x + 200, 300), (0, 255, 0), 2)
            cv2.putText(frame, z["name"], (x + 10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            x += 250

        _, buffer = cv2.imencode(".jpg", frame)
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )

# --------------------------------------------------
# LIVE LOG
# --------------------------------------------------
live_log = []

# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
@token_required
def dashboard():
    return render_template("index.html")

@app.route("/video_feed")
@token_required
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# --------------------------------------------------
# ANALYTICS API
# --------------------------------------------------
@app.route("/analytics")
@token_required
def analytics_api():
    zones = load_zones()
    cfg = load_config()

    zone_counts = {}
    total = 0
    alert = False

    for z in zones:
        if z["status"] != "active":
            continue

        count = random.randint(2, 20)
        zone_counts[z["name"]] = count
        total += count

        if cfg["alert_enabled"] and count > z["threshold"]:
            alert = True

    log = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "zones": zone_counts,
        "total": total,
        "alert": alert
    }

    live_log.append(log)
    live_log[:] = live_log[-cfg["max_logs"]:]

    return jsonify(log)

# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------
@app.route("/admin")
@token_required
@admin_required
def admin_home():
    users = load_users()
    zones = load_zones()

    alerts_today = sum(1 for l in live_log if l["alert"])
    thresholds = [z["threshold"] for z in zones if z["status"] == "active"]
    current_threshold = min(thresholds) if thresholds else 0

    return render_template(
        "admin_dashboard.html",
        total_users=len(users),
        active_cameras=len(zones),
        alerts_today=alerts_today,
        current_threshold=current_threshold
    )

# --------------------------------------------------
# ADMIN USERS
# --------------------------------------------------
@app.route("/admin/users")
@token_required
@admin_required
def admin_users():
    return render_template("admin_users.html", users=load_users())

# --------------------------------------------------
# ADMIN ZONES
# --------------------------------------------------
@app.route("/admin/zones")
@token_required
@admin_required
def admin_zones():
    return render_template("admin_zones.html", zones=load_zones())

@app.route("/admin/zones/add", methods=["POST"])
@token_required
@admin_required
def add_zone():
    zones = load_zones()
    zones.append({
        "id": max([z["id"] for z in zones], default=0) + 1,
        "camera": request.form["camera"],
        "name": request.form["name"],
        "threshold": int(request.form["threshold"]),
        "status": "active"
    })
    save_zones(zones)
    return redirect("/admin/zones")

@app.route("/admin/zones/edit/<int:zone_id>", methods=["POST"])
@token_required
@admin_required
def edit_zone(zone_id):
    zones = load_zones()
    for z in zones:
        if z["id"] == zone_id:
            z["camera"] = request.form["camera"]
            z["name"] = request.form["name"]
            z["threshold"] = int(request.form["threshold"])
            z["status"] = request.form["status"]
    save_zones(zones)
    return redirect("/admin/zones")

@app.route("/admin/zones/delete/<int:zone_id>", methods=["POST"])
@token_required
@admin_required
def delete_zone(zone_id):
    save_zones([z for z in load_zones() if z["id"] != zone_id])
    return redirect("/admin/zones")

# --------------------------------------------------
# ADMIN SETTINGS
# --------------------------------------------------
@app.route("/admin/settings", methods=["GET", "POST"])
@token_required
@admin_required
def admin_settings():
    cfg = load_config()
    if request.method == "POST":
        cfg["alert_enabled"] = "alert_enabled" in request.form
        cfg["alert_cooldown"] = int(request.form["alert_cooldown"])
        cfg["max_logs"] = int(request.form["max_logs"])
        save_config(cfg)
        return redirect("/admin/settings")
    return render_template("admin_settings.html", config=cfg)

# --------------------------------------------------
# ADMIN ANALYTICS
# --------------------------------------------------
@app.route("/admin/analytics")
@token_required
@admin_required
def admin_analytics():
    return render_template("admin_analytics.html")

# --------------------------------------------------
# CSV DOWNLOAD
# --------------------------------------------------
@app.route("/download_csv")
@token_required
def download_csv():
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "Zone", "Count", "Total", "Alert"])
        for log in live_log:
            for zone, count in log["zones"].items():
                writer.writerow([log["time"], zone, count, log["total"], log["alert"]])
    return send_file(CSV_PATH, as_attachment=True)

# --------------------------------------------------
# PDF DOWNLOAD
# --------------------------------------------------
@app.route("/generate_pdf")
@token_required
def generate_pdf():
    c = canvas.Canvas(PDF_PATH, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Crowd Monitoring Report")
    y -= 30

    c.setFont("Helvetica", 10)
    for log in live_log[-30:]:
        c.drawString(
            40, y,
            f'{log["time"]} | Total: {log["total"]} | Alert: {log["alert"]}'
        )
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    return send_file(PDF_PATH, as_attachment=True)

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
@app.route("/logout")
def logout():
    token = request.cookies.get("token")

    if token:
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            mark_user_inactive(data.get("username"))
        except:
            pass

    resp = make_response(redirect("/"))
    resp.set_cookie("token", "", expires=0)
    return resp

# --------------------------------------------------
# RUN
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
