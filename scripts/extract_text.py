"""Text from a board book, letter or proxy: python3 extract_text.py <input> <output.txt> [--ocr]
PDF via pdftotext with a -----PAGE----- marker between pages, reporting pages with no text layer; --ocr also writes
<out stem>_ocr.txt through ocr.py (Apple Vision on macOS, else RapidOCR, else tesseract); PPTX via markitdown or python-pptx;
DOCX via python-docx (tables as | rows |); HTML via the redline reader; text copied."""
import sys, re, subprocess, shutil, tempfile, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "redline"))
def _pdf_pages(p):
    if not shutil.which("pdftotext"): sys.exit("pdftotext (poppler) is not installed; supply the document as text")
    return subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout.split("\f")
def extract(src, ocr=False, log=print):
    src = Path(src); ext = src.suffix.lower()
    if ext == ".pdf":
        pages = _pdf_pages(src); thin = [i + 1 for i, p in enumerate(pages) if len(p.strip()) < 200]
        if thin: log(f"NOTE: {len(thin)} of {len(pages)} pages have little or no text layer (pages {thin[:15]}{'...' if len(thin) > 15 else ''}); run ocr.py on the PDF to produce book_ocr.txt")
        return "\n-----PAGE-----\n".join(p.strip("\n") for p in pages)
    if ext == ".pptx":
        if shutil.which("markitdown"): return subprocess.run(["markitdown", str(src)], capture_output=True, text=True).stdout.replace("<!-- Slide number:", "-----PAGE-----\n<!-- Slide number:")
        from pptx import Presentation
        return "\n-----PAGE-----\n".join("\n".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame) for s in Presentation(str(src)).slides)
    if ext == ".docx":
        from redline import read_docx; return read_docx(src)
    if ext in (".htm", ".html", ".xhtml"):
        from redline import read_html; return read_html(src)
    if ext in (".doc", ".rtf", ".odt"):
        from redline import read_input; return read_input(str(src))
    return src.read_text(errors="ignore")
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--ocr", action="store_true", help="also OCR the pages (PDF or images) into <out stem>_ocr.txt with ocr.py's auto backend"); a = ap.parse_args()
    text = extract(a.src, a.ocr); out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text)
    if a.ocr and Path(a.src).suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        from ocr import run as ocr_run; otext, backend = ocr_run(a.src); op = out.with_name(out.stem + "_ocr.txt"); op.write_text(otext); print(f"wrote {op} ({len(otext):,} characters, backend {backend})")
    n = text.count("-----PAGE-----") + 1 if "-----PAGE-----" in text else None
    print(f"wrote {out} ({len(text):,} characters{', ' + str(n) + ' pages' if n else ''})")
