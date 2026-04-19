def prepare_image(file_path, filename, dpi=300):
    return {
        "print_paths": [file_path],
        "preview_paths": [file_path],
        "source_path": file_path,
        "kind": "image",
    }
