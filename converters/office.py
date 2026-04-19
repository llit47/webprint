import os
import subprocess
import uuid

from storage import UPLOAD_DIR

from .pdf import prepare_pdf


def prepare_office_document(file_path, filename, dpi=300):
    output_dir = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_office")
    os.makedirs(output_dir, exist_ok=True)

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            file_path,
        ],
        check=True,
        timeout=120,
    )

    pdf_filename = os.path.splitext(os.path.basename(filename))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)
    return prepare_pdf(pdf_path, pdf_filename, dpi=dpi)
