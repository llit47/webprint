from .images import prepare_image
from .office import prepare_office_document
from .pdf import create_pdf_from_html, prepare_pdf


def prepare_for_print(file_path, filename, dpi=300):
    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        return prepare_pdf(file_path, filename, dpi=dpi)
    if lower_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")):
        return prepare_image(file_path, filename, dpi=dpi)
    if lower_name.endswith((".doc", ".docx", ".odt")):
        return prepare_office_document(file_path, filename, dpi=dpi)
    return {
        "print_paths": [file_path],
        "preview_paths": [file_path],
        "source_path": file_path,
        "kind": "passthrough",
    }


def prepare_custom_content(content_html, dpi=300, title="custom-content"):
    pdf_path = create_pdf_from_html(content_html, title=title)
    return prepare_pdf(pdf_path, f"{title}.pdf", dpi=dpi)
