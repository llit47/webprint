from .images import prepare_image
from .office import prepare_office_document
from .pdf import prepare_pdf


def prepare_for_print(file_path, filename):
    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        return prepare_pdf(file_path, filename)
    if lower_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")):
        return prepare_image(file_path, filename)
    if lower_name.endswith((".doc", ".docx", ".odt")):
        return prepare_office_document(file_path, filename)
    return file_path
