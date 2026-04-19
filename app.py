from flask import Flask, request, render_template_string, jsonify
import os
import subprocess
import uuid
import json
from datetime import datetime
import traceback
import time

UPLOAD_DIR = "/tmp/webprint"
HISTORY_FILE = "/opt/webprint/history.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# ---------------- CACHE ----------------

QUEUE_CACHE = {"data": "", "time": 0}
CACHE_TTL = 2


# ---------------- HISTORY ----------------

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_history(entry):
    data = load_history()
    data.insert(0, entry)
    data = data[:50]
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------------- CUPS ----------------

def get_printer():
    try:
        return subprocess.check_output(
            ["lpstat", "-p", "brother"],
            timeout=2
        ).decode()
    except:
        return "Brak danych"


def get_queue():
    global QUEUE_CACHE
    now = time.time()

    if now - QUEUE_CACHE["time"] < CACHE_TTL:
        return QUEUE_CACHE["data"]

    try:
        out = subprocess.check_output(
            ["lpstat", "-o", "brother"],
            timeout=2
        ).decode()
    except:
        out = "Brak kolejki"

    QUEUE_CACHE = {"data": out, "time": now}
    return out


def cancel_job(job):
    try:
        subprocess.run(["cancel", job], timeout=2)
        return True
    except:
        return False


# ---------------- PRINT ----------------

def print_file(file_path, filename):
    try:
        subprocess.run(
            ["lp", "-d", "brother", file_path],
            check=True,
            timeout=10
        )

        save_history({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file": filename
        })

        return True, "Wysłano do drukarki ✔"
    except:
        return False, traceback.format_exc()


# ---------------- FILES ----------------

def save_upload(file):
    path = os.path.join(UPLOAD_DIR, str(uuid.uuid4()) + "_" + file.filename)
    file.save(path)
    return path


# ---------------- UI ----------------

HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
:root {
    --bg:#0f1115;
    --card:#171a21;
    --text:#e6e6e6;
    --muted:#9aa0a6;
    --accent:#4f9cff;
    --ok:#39d98a;
    --err:#ff4f4f;
}

body {
    margin:0;
    font-family:system-ui;
    background:var(--bg);
    color:var(--text);
    display:flex;
    justify-content:center;
}

.container { width:100%; max-width:650px; padding:20px; }

.card {
    background:var(--card);
    padding:18px;
    border-radius:14px;
}

.tabs {
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:6px;
    margin-bottom:15px;
}

.tab {
    text-align:center;
    padding:10px;
    border-radius:10px;
    background:#0d0f14;
    color:var(--muted);
    text-decoration:none;
    font-size:13px;
}

.tab.active {
    background:var(--accent);
    color:white;
}

input, select {
    width:100%;
    box-sizing:border-box;
    padding:10px;
    margin:6px 0 12px;
    border-radius:10px;
    border:1px solid #2a2f3a;
    background:#0d0f14;
    color:var(--text);
}

button {
    width:100%;
    padding:12px;
    border:0;
    border-radius:10px;
    background:var(--accent);
    color:white;
    font-weight:600;
}

.status {
    margin-top:12px;
    padding:10px;
    border-radius:10px;
    white-space:pre-wrap;
}

.ok { background:rgba(57,217,138,0.15); color:var(--ok); }
.err { background:rgba(255,79,79,0.15); color:var(--err); }

pre {
    background:#0d0f14;
    padding:10px;
    border-radius:10px;
    overflow:auto;
    font-size:12px;
}

.small { font-size:12px; color:var(--muted); }
</style>
</head>

<body>
<div class="container">
<div class="card">

<div class="tabs">
<a class="tab {{'active' if page=='basic'}}" href="/">Podstawowy</a>
<a class="tab {{'active' if page=='advanced'}}" href="/advanced">Zaawansowany</a>
<a class="tab {{'active' if page=='history'}}" href="/history">Historia</a>
<a class="tab {{'active' if page=='queue'}}" href="/queue">Kolejka</a>
</div>

{% if page == "basic" %}

<form id="printForm">
<input type="file" name="file" required>
<button>DRUKUJ</button>
</form>

<div id="status"></div>

<script>
document.getElementById("printForm").onsubmit = async (e) => {
    e.preventDefault();

    let form = new FormData(e.target);

    let res = await fetch("/api/print", {
        method: "POST",
        body: form
    });

    let data = await res.json();

    document.getElementById("status").innerHTML =
        `<div class='status ${data.ok ? "ok":"err"}'>${data.msg}</div>`;
};
</script>

{% elif page == "advanced" %}

<form method="post" enctype="multipart/form-data">
<input type="file" name="file" required>

<label>Kopie</label>
<input name="copies" value="1">

<label>Skala</label>
<input name="scale" value="100">

<label>Orientacja</label>
<select name="orientation">
<option value="portrait">Pionowa</option>
<option value="landscape">Pozioma</option>
</select>

<label>Kolor</label>
<select name="color">
<option value="Color">Kolor</option>
<option value="Mono">Mono</option>
</select>

<label>Jakość</label>
<select name="quality">
<option value="PlainNormal">Normal</option>
<option value="PlainFast">Fast</option>
<option value="Best">Best</option>
</select>

<button>DRUKUJ</button>
</form>

{% elif page == "history" %}

<h3>Historia</h3>
<pre id="hist"></pre>

<script>
async function loadHist(){
    let r = await fetch("/api/history");
    let d = await r.json();

    document.getElementById("hist").innerText =
        d.map(x => `${x.time} | ${x.file}`).join("\\n");
}

loadHist();
setInterval(loadHist, 3000);
</script>

{% elif page == "queue" %}

<h3>Drukarka</h3>
<pre id="printer"></pre>

<h3>Kolejka</h3>
<pre id="queue"></pre>

<h4>Anuluj zadanie</h4>
<input id="job" placeholder="job-id">
<button onclick="cancel()">Cancel</button>

<script>

async function refresh(){
    let r = await fetch("/api/status");
    let d = await r.json();

    document.getElementById("printer").innerText = d.printer;
    document.getElementById("queue").innerText = d.queue;
}

async function cancel(){
    let job = document.getElementById("job").value;

    await fetch("/api/cancel", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({job})
    });

    refresh();
}

refresh();
setInterval(refresh, 2000);

</script>

{% endif %}

</div>
</div>
</body>
</html>
"""


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template_string(HTML, page="basic")


@app.route("/advanced", methods=["GET", "POST"])
def advanced():
    if request.method == "POST":
        f = request.files["file"]
        path = save_upload(f)

        ok, msg = print_file(path, f.filename)
        return msg

    return render_template_string(HTML, page="advanced")


@app.route("/history")
def history():
    return render_template_string(HTML, page="history")


@app.route("/queue")
def queue():
    return render_template_string(HTML, page="queue")


# ---------------- API ----------------

@app.route("/api/print", methods=["POST"])
def api_print():
    f = request.files["file"]
    path = save_upload(f)

    ok, msg = print_file(path, f.filename)

    return jsonify({"ok": ok, "msg": msg})


@app.route("/api/history")
def api_history():
    return jsonify(load_history())


@app.route("/api/status")
def api_status():
    return jsonify({
        "printer": get_printer(),
        "queue": get_queue()
    })


@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    job = request.json.get("job")
    cancel_job(job)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
