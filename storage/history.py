import json
import os

HISTORY_FILE = "/opt/webprint/history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as handle:
            return json.load(handle)
    except:
        return []


def save_history(entry):
    data = load_history()
    data.insert(0, entry)
    data = data[:50]
    with open(HISTORY_FILE, "w") as handle:
        json.dump(data, handle, indent=2)
