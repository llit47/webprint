import os
import re
import uuid
from html import unescape
from html.parser import HTMLParser

from pdf2image import convert_from_path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from storage import UPLOAD_DIR


DEFAULT_DPI = 300
PREVIEW_PAGE_LIMIT = 3
PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN = 36
LINE_HEIGHT = 20
FONT_SIZES = {"small": 10, "medium": 12, "large": 16}


class SimpleEditorHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.current_fragments = []
        self.inline_state = {"bold": False, "size": "medium"}
        self.list_stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"b", "strong"}:
            self.inline_state["bold"] = True
        elif tag == "span":
            size = self.extract_font_size(attrs.get("style", ""))
            if size:
                self.inline_state["size"] = size
        elif tag == "br":
            self.flush_block()
        elif tag in {"p", "div"}:
            self.flush_block()
        elif tag == "ul":
            self.flush_block()
            self.list_stack.append("ul")
        elif tag == "li":
            self.flush_block()
            self.current_fragments.append({"text": "• ", "bold": False, "size": "medium"})

    def handle_endtag(self, tag):
        if tag in {"b", "strong"}:
            self.inline_state["bold"] = False
        elif tag == "span":
            self.inline_state["size"] = "medium"
        elif tag in {"p", "div", "li"}:
            self.flush_block()
        elif tag == "ul":
            self.flush_block()
            if self.list_stack:
                self.list_stack.pop()

    def handle_data(self, data):
        text = unescape(data)
        if not text.strip() and "\n" not in text:
            return
        normalized = re.sub(r"\s+", " ", text)
        if normalized.strip():
            self.current_fragments.append(
                {
                    "text": normalized,
                    "bold": self.inline_state["bold"],
                    "size": self.inline_state["size"],
                }
            )

    def extract_font_size(self, style):
        lowered = style.lower()
        if "font-size" not in lowered:
            return None
        if "small" in lowered or "12px" in lowered:
            return "small"
        if "large" in lowered or "20px" in lowered:
            return "large"
        return "medium"

    def flush_block(self):
        cleaned = [fragment for fragment in self.current_fragments if fragment["text"].strip()]
        if cleaned:
            self.blocks.append(cleaned)
        self.current_fragments = []


def rasterize_pdf(file_path, filename, dpi=DEFAULT_DPI):
    pages = convert_from_path(file_path, dpi=normalize_dpi(dpi), fmt="png")
    base_name = os.path.splitext(os.path.basename(filename))[0]
    raster_paths = []

    for index, page in enumerate(pages, start=1):
        raster_path = os.path.join(
            UPLOAD_DIR,
            f"{uuid.uuid4()}_{base_name}_page_{index}.png",
        )
        page.save(raster_path, "PNG")
        raster_paths.append(raster_path)

    return {
        "print_paths": raster_paths,
        "preview_paths": raster_paths[:PREVIEW_PAGE_LIMIT],
        "source_path": file_path,
        "kind": "raster",
    }


def prepare_pdf(file_path, filename, dpi=DEFAULT_DPI):
    return rasterize_pdf(file_path, filename, dpi=dpi)


def create_pdf_from_html(content_html, title="custom-content"):
    parser = SimpleEditorHTMLParser()
    parser.feed(content_html or "")
    parser.flush_block()

    pdf_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{title}.pdf")
    pdf_canvas = canvas.Canvas(pdf_path, pagesize=A4)
    cursor_y = PAGE_HEIGHT - PAGE_MARGIN

    if not parser.blocks:
        parser.blocks = [[{"text": " ", "bold": False, "size": "medium"}]]

    for block in parser.blocks:
        cursor_y = draw_block(pdf_canvas, block, cursor_y)
        cursor_y -= 8
        if cursor_y <= PAGE_MARGIN:
            pdf_canvas.showPage()
            cursor_y = PAGE_HEIGHT - PAGE_MARGIN

    pdf_canvas.save()
    return pdf_path


def draw_block(pdf_canvas, fragments, cursor_y):
    line_x = PAGE_MARGIN
    max_height = LINE_HEIGHT

    for fragment in fragments:
        font_size = FONT_SIZES.get(fragment["size"], FONT_SIZES["medium"])
        font_name = "Helvetica-Bold" if fragment["bold"] else "Helvetica"
        words = fragment["text"].split(" ")
        max_height = max(max_height, font_size + 6)

        for word in words:
            token = word + " "
            token_width = pdf_canvas.stringWidth(token, font_name, font_size)
            if line_x + token_width > PAGE_WIDTH - PAGE_MARGIN:
                cursor_y -= max_height
                line_x = PAGE_MARGIN
                max_height = font_size + 6

            if cursor_y <= PAGE_MARGIN:
                pdf_canvas.showPage()
                cursor_y = PAGE_HEIGHT - PAGE_MARGIN
                line_x = PAGE_MARGIN

            pdf_canvas.setFont(font_name, font_size)
            pdf_canvas.drawString(line_x, cursor_y, token)
            line_x += token_width

    return cursor_y - max_height


def normalize_dpi(dpi):
    try:
        value = int(dpi)
    except:
        return DEFAULT_DPI
    if value in {150, 300, 600}:
        return value
    return DEFAULT_DPI
