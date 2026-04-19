import os

from flask import jsonify, redirect, render_template, request, send_file, url_for

from converters import prepare_custom_content, prepare_for_print
from printer import cancel_job, get_printer, get_queue, print_file
from storage import UPLOAD_DIR, load_history, save_upload


def register_routes(app):
    def get_print_options():
        copies = request.form.get("copies", "1")
        quality = request.form.get("quality", "Normal")
        scale = request.form.get("scale", "100")
        color = request.form.get("color", "color")
        dpi = request.form.get("dpi", "300")

        return {
            "copies": copies,
            "quality": quality,
            "scale": scale,
            "color": color,
            "dpi": dpi,
        }

    def split_print_options():
        options = get_print_options()
        dpi = options.pop("dpi")
        return options, dpi

    def get_preview_payload():
        if "file" in request.files and request.files["file"].filename:
            upload = request.files["file"]
            path = save_upload(upload)
            return prepare_for_print(path, upload.filename, dpi=request.form.get("dpi", "300"))

        custom_html = request.form.get("content_html", "")
        if custom_html.strip():
            return prepare_custom_content(custom_html, dpi=request.form.get("dpi", "300"), title="custom-preview")
        raise ValueError("Brak danych do podglądu")

    @app.route("/")
    def home():
        return render_template("index.html", page="basic")

    @app.route("/advanced", methods=["GET", "POST"])
    def advanced():
        if request.method == "POST":
            upload = request.files["file"]
            path = save_upload(upload)
            print_options, dpi = split_print_options()
            printable_path = prepare_for_print(path, upload.filename, dpi=dpi)

            print_file(printable_path, upload.filename, **print_options)
            return redirect(url_for("home"))

        return render_template("index.html", page="advanced")

    @app.route("/custom", methods=["GET", "POST"])
    def custom():
        if request.method == "POST":
            print_options, dpi = split_print_options()
            printable_path = prepare_custom_content(
                request.form.get("content_html", ""),
                dpi=dpi,
                title="custom-document",
            )
            print_file(printable_path, "custom-document.pdf", **print_options)
            return redirect(url_for("home"))

        return render_template("index.html", page="custom")

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
        print_options, dpi = split_print_options()
        printable_path = prepare_for_print(path, upload.filename, dpi=dpi)

        ok, msg = print_file(printable_path, upload.filename, **print_options)
        return jsonify({"ok": ok, "msg": msg})

    @app.route("/api/preview", methods=["POST"])
    def api_preview():
        try:
            printable = get_preview_payload()
            preview_paths = printable.get("preview_paths", [])[:3]
            return jsonify(
                {
                    "ok": True,
                    "pages": [
                        url_for("api_preview_file", filename=os.path.basename(path))
                        for path in preview_paths
                    ],
                }
            )
        except Exception as exc:
            return jsonify({"ok": False, "msg": str(exc), "pages": []}), 400

    @app.route("/api/preview/<path:filename>")
    def api_preview_file(filename):
        safe_name = os.path.basename(filename)
        return send_file(os.path.join(UPLOAD_DIR, safe_name))

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
