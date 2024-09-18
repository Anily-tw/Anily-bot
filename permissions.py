import os
import json

PERMISSIONS_FILE = os.getenv("ANILY_BOT_PERMISSIONS_FILE", "permissions.json")

def load_permissions():
    if not os.path.exists(PERMISSIONS_FILE):
        return {}
    with open(PERMISSIONS_FILE, "r") as f:
        return json.load(f)

def save_permissions(permissions):
    with open(PERMISSIONS_FILE, "w") as f:
        json.dump(permissions, f, indent=4)

def has_permission(user_id, category, permissions):
    if str(user_id) in permissions:
        return category in permissions[str(user_id)]
    return False