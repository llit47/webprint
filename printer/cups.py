import subprocess
import time
import traceback
from datetime import datetime

from storage import CACHE_TTL, QUEUE_CACHE, save_history

PRINTER_NAME = "brother"


def get_printer():
    try:
        return subprocess.check_output(
            ["lpstat", "-p", PRINTER_NAME],
            timeout=2,
        ).decode()
    except:
        return "Brak danych"


def get_queue():
    now = time.time()

    if now - QUEUE_CACHE["time"] < CACHE_TTL:
        return QUEUE_CACHE["data"]

    try:
        out = subprocess.check_output(
            ["lpstat", "-o", PRINTER_NAME],
            timeout=2,
        ).decode()
    except:
        out = "Brak kolejki"

    QUEUE_CACHE["data"] = out
    QUEUE_CACHE["time"] = now
    return out


def cancel_job(job):
    try:
        subprocess.run(["cancel", job], timeout=2)
        return True
    except:
        return False


def normalize_copies(copies):
    try:
        return str(max(1, int(copies)))
    except:
        return "1"


def normalize_scale(scale):
    try:
        return str(max(1, int(scale)))
    except:
        return "100"


def normalize_quality(quality):
    value = (quality or "Normal").strip()
    quality_map = {
        "plainfast": "3",
        "fast": "3",
        "plainnormal": "4",
        "normal": "4",
        "best": "5",
    }
    return quality_map.get(value.lower(), "4")


def normalize_color(color):
    value = (color or "color").strip().lower()
    if value == "mono":
        return "Mono"
    return "Color"


def build_print_command(file_path, copies, quality, scale, color):
    return [
        "lp",
        "-d",
        PRINTER_NAME,
        "-n",
        normalize_copies(copies),
        "-o",
        f"print-quality={normalize_quality(quality)}",
        "-o",
        f"scaling={normalize_scale(scale)}",
        "-o",
        f"ColorModel={normalize_color(color)}",
        file_path,
    ]


def print_file(file_path, filename, copies="1", quality="Normal", scale="100", color="color"):
    try:
        subprocess.run(
            build_print_command(file_path, copies, quality, scale, color),
            check=True,
            timeout=10,
        )

        save_history(
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file": filename,
            }
        )

        return True, "Wysłano do drukarki ✔"
    except:
        return False, traceback.format_exc()
