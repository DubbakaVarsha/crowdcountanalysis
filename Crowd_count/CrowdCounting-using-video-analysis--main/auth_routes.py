from flask import Blueprint, request, jsonify, make_response
import jwt
from datetime import datetime, timedelta
import json
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
USERS_PATH = os.path.join(BASE_DIR, "..", "users.json")

SECRET_KEY = "supersecretkey"

# ---------------- LOAD / SAVE USERS ----------------
def load_users():
    with open(USERS_PATH, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_PATH, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    users = load_users()

    for user in users:
        if user["username"] == data.get("username"):
            # 🔒 Block disabled users
            if user.get("status") == "disabled":
                return jsonify({"success": False, "message": "User disabled"}), 403

            # ✅ UPDATE ACTIVITY STATUS
            user["status"] = "active"
            user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_users(users)

            # ✅ CREATE JWT
            token = jwt.encode(
                {
                    "username": user["username"],
                    "role": user["role"],
                    "exp": datetime.utcnow() + timedelta(hours=2)
                },
                SECRET_KEY,
                algorithm="HS256"
            )

            resp = make_response(jsonify({"success": True}))
            resp.set_cookie("token", token, httponly=True)
            return resp

    return jsonify({"success": False, "message": "Invalid credentials"}), 401
