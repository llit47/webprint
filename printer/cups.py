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


def print_file(file_path, filename):
    try:
        subprocess.run(
            ["lp", "-d", PRINTER_NAME, file_path],
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
