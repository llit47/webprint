import os
import uuid

UPLOAD_DIR = "/tmp/webprint"

os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload(file_storage):
    path = os.path.join(UPLOAD_DIR, str(uuid.uuid4()) + "_" + file_storage.filename)
    file_storage.save(path)
    return path
