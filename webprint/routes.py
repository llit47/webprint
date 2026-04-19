from flask import jsonify, render_template, request

from converters import prepare_for_print
from printer import cancel_job, get_printer, get_queue, print_file
from storage import load_history, save_upload


def register_routes(app):
    @app.route("/")
    def home():
        return render_template("index.html", page="basic")

    @app.route("/advanced", methods=["GET", "POST"])
    def advanced():
        if request.method == "POST":
            upload = request.files["file"]
            path = save_upload(upload)
            printable_path = prepare_for_print(path, upload.filename)

            ok, msg = print_file(printable_path, upload.filename)
            return msg

        return render_template("index.html", page="advanced")

    @app.route("/history")
    def history():
        return render_template("index.html", page="history")

    @app.route("/queue")
    def queue():
        return render_template("index.html", page="queue")

    @app.route("/api/print", methods=["POST"])
    def api_print():
        upload = request.files["file"]
        path = save_upload(upload)
        printable_path = prepare_for_print(path, upload.filename)

        ok, msg = print_file(printable_path, upload.filename)
        return jsonify({"ok": ok, "msg": msg})

    @app.route("/api/history")
    def api_history():
        return jsonify(load_history())

    @app.route("/api/status")
    def api_status():
        return jsonify({"printer": get_printer(), "queue": get_queue()})

    @app.route("/api/cancel", methods=["POST"])
    def api_cancel():
        job = request.json.get("job")
        cancel_job(job)
        return jsonify({"ok": True})
