from flask import Blueprint, jsonify, request
import json, os
from auth.auth_utils import token_required, admin_required

admin_bp = Blueprint("admin", __name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "config", "thresholds.json")

# ---------- GET THRESHOLDS ----------
@admin_bp.route("/thresholds", methods=["GET"])
@token_required
@admin_required
def get_thresholds():
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return jsonify(data)

# ---------- UPDATE THRESHOLDS ----------
@admin_bp.route("/thresholds", methods=["POST"])
@token_required
@admin_required
def update_thresholds():
    data = request.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)
    return jsonify({"message": "Thresholds updated successfully"})
