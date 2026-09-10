"""Report which external tools the plugin can use. python3 check_tools.py"""
import shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = []
def has(cmd): return shutil.which(cmd) is not None
rows.append(("python3 requests + beautifulsoup4", all(__import__(m) for m in []) and True, ""))
try: import requests; import bs4; rows[-1] = ("python3 requests + beautifulsoup4", True, "")
except Exception as e: rows[-1] = ("python3 requests + beautifulsoup4", False, "pip install requests beautifulsoup4 lxml (precedent search needs both)")
rows.append(("pdftotext (poppler)", has("pdftotext"), "board books as PDF; without it supply text"))
rows.append(("pandoc or python-docx", has("pandoc") or (__import__("importlib").util.find_spec("docx") is not None), "Word inputs"))
rows.append(("node + docx package", has("node") and (HERE / "redline" / "node_modules" / "docx").exists(), "docx outputs; " + ("installs itself on first use (npm install in scripts/redline)" if has("node") and has("npm") else "needs node and npm")))
so = has("soffice") or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists(); rows.append(("LibreOffice", so, "PDF outputs"))
import platform
vision = platform.system() == "Darwin" and (has("swiftc") or (HERE / "ocr" / "ocr").exists()); rapid = __import__("importlib").util.find_spec("rapidocr_onnxruntime") is not None
rows.append(("OCR: Apple Vision (macOS, swiftc)", vision, "image-only board books, best quality"))
rows.append(("OCR: tesseract", has("tesseract"), "image-only board books off a Mac"))
rows.append(("OCR: RapidOCR (pip)", rapid, "last resort on any platform: pip install rapidocr-onnxruntime pypdfium2; runs words together on dense slides"))
print("| tool | present | used for |"); print("|---|---|---|")
for name, ok, note in rows: print(f"| {name} | {'yes' if ok else 'no'} | {note} |")
