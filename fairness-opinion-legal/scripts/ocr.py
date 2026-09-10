#!/usr/bin/env python3
"""OCR for image-only board books. python3 ocr.py <pdf | image | folder of images> <out.txt> [--backend auto|vision|rapidocr|tesseract] [--dpi 200]
Pages are separated by -----PAGE-----; within a page, text boxes on one line are joined with "  |  " so table rows survive.
Backends, tried in this order under auto: Apple Vision (macOS; scripts/ocr/ocr.swift compiled once with swiftc; about 0.5 s a
page, clean spacing), tesseract (if installed), RapidOCR (pip install rapidocr-onnxruntime; any platform, no system dependency,
fast, but its English model runs words together on dense slides, so numbers survive and prose needs the text layer). PDF pages are rendered with
pdftoppm when present, else with pypdfium2 (pip install pypdfium2)."""
import sys, os, re, shutil, subprocess, tempfile, argparse, platform
from pathlib import Path
HERE = Path(__file__).resolve().parent; SWIFT = HERE / "ocr" / "ocr.swift"; BIN = HERE / "ocr" / "ocr"
def render_pdf(pdf, td, dpi):
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(Path(td) / "pg")], capture_output=True); return sorted(Path(td).glob("pg*.png"))
    try: import pypdfium2 as pdfium
    except ImportError: sys.exit("rendering PDF pages needs pdftoppm (poppler) or `pip install pypdfium2`")
    out = []; doc = pdfium.PdfDocument(str(pdf))
    for i in range(len(doc)):
        img = doc[i].render(scale=dpi / 72).to_pil(); p = Path(td) / f"pg-{i + 1:04d}.png"; img.save(p); out.append(p)
    return out
def vision_available():
    if platform.system() != "Darwin": return False
    if BIN.exists(): return True
    if not shutil.which("swiftc"): return False
    r = subprocess.run(["swiftc", "-O", str(SWIFT), "-o", str(BIN)], capture_output=True, text=True); return r.returncode == 0 and BIN.exists()
def ocr_vision(images):
    pages = {}
    for i in range(0, len(images), 25):
        r = subprocess.run([str(BIN)] + [str(x) for x in images[i:i + 25]], capture_output=True, text=True, timeout=3600)
        cur = None
        for line in r.stdout.split("\n"):
            if line.startswith("=====FILE "): cur = line[10:].strip(); pages[cur] = []
            elif cur is not None: pages[cur].append(line)
    return ["\n".join(pages.get(str(x), [])).strip() for x in images]
def rows_from_boxes(items):
    """items: (y_center, x_left, height, text) in image coordinates; group into rows, left to right."""
    items = sorted(items, key=lambda t: t[0]); rows = []
    for it in items:
        if rows and abs(rows[-1][0][0] - it[0]) < max(rows[-1][0][2], it[2]) * 0.6: rows[-1].append(it)
        else: rows.append([it])
    return "\n".join("  |  ".join(t[3] for t in sorted(r, key=lambda t: t[1])) for r in rows)
def ocr_rapid(images):
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np
    from PIL import Image
    eng = RapidOCR(); out = []
    for x in images:
        im = Image.open(x).convert("RGB")
        if im.width < 2400: f = 3 if im.width < 1000 else 2; im = im.resize((im.width * f, im.height * f), Image.LANCZOS)   # slide images are small; the recognizer wants ~2,400 px wide
        res, _ = eng(np.array(im)); items = []
        for box, text, score in (res or []):
            ys = [p[1] for p in box]; xs = [p[0] for p in box]; items.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), text))
        out.append(rows_from_boxes(items))
    return out
def ocr_tesseract(images):
    return [subprocess.run(["tesseract", str(x), "-", "--psm", "6"], capture_output=True, text=True).stdout.strip() for x in images]
def run(src, backend="auto", dpi=200, log=print):
    src = Path(src)
    with tempfile.TemporaryDirectory() as td:
        if src.is_dir(): images = sorted(p for p in src.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif"))
        elif src.suffix.lower() == ".pdf": images = render_pdf(src, td, dpi)
        else: images = [src]
        if not images: sys.exit("no pages to OCR")
        if backend == "auto": backend = "vision" if vision_available() else ("tesseract" if shutil.which("tesseract") else ("rapidocr" if __import__("importlib").util.find_spec("rapidocr_onnxruntime") else None))
        if backend is None: sys.exit("no OCR backend: on macOS install the Xcode command line tools (swiftc); elsewhere install tesseract, or `pip install rapidocr-onnxruntime pypdfium2` (fast, but it runs words together on dense slides)")
        if backend == "vision" and not vision_available(): sys.exit("Apple Vision backend needs macOS and swiftc")
        log(f"OCR backend {backend}, {len(images)} pages")
        pages = {"vision": ocr_vision, "rapidocr": ocr_rapid, "tesseract": ocr_tesseract}[backend](images)
    return "\n-----PAGE-----\n".join(pages), backend
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--backend", default="auto", choices=["auto", "vision", "rapidocr", "tesseract"]); ap.add_argument("--dpi", type=int, default=200); a = ap.parse_args()
    text, backend = run(a.src, a.backend, a.dpi); Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(text)
    print(f"wrote {a.out} ({len(text):,} characters, {text.count('-----PAGE-----') + 1} pages, backend {backend})")
