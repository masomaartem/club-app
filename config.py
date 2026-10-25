import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ADMINS_FILE = BASE_DIR / "admins.json"
CONFIG_FILE = BASE_DIR / "settings.json"

BOT_TOKEN = "8962936269:AAGkRKTmVaIfE_6Jp6OSFxJ1_IXaLk0PGyk"

DEFAULT_SETTINGS = {
    "alert_cpu_threshold": 85.0,     # Alert when CPU > 85%
    "alert_ram_threshold": 90.0,     # Alert when RAM > 90%
    "alert_disk_threshold": 90.0,    # Alert when Disk > 90%
    "alert_interval_seconds": 60,    # Background check interval
    "alert_cooldown_minutes": 15,    # Minimum interval between duplicate alerts
    "alerts_enabled": True
}

def load_settings():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

def load_admins():
    if ADMINS_FILE.exists():
        try:
            with open(ADMINS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_admins(admins):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(admins), f, indent=2)

def add_admin(user_id: int):
    admins = load_admins()
    admins.add(user_id)
    save_admins(admins)

def remove_admin(user_id: int):
    admins = load_admins()
    admins.discard(user_id)
    save_admins(admins)

def is_admin(user_id: int) -> bool:
    admins = load_admins()
    # If no admins configured yet, we will allow registration
    return user_id in admins
