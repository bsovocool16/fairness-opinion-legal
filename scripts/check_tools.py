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
rows.append(("node + docx package", has("node") and (HERE / "redline" / "node_modules" / "docx").exists(), "docx outputs; run `npm install` in scripts/redline"))
so = has("soffice") or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists(); rows.append(("LibreOffice", so, "PDF outputs"))
rows.append(("OCR (ocrmypdf or tesseract)", has("ocrmypdf") or has("tesseract"), "image-only board books"))
print("| tool | present | used for |"); print("|---|---|---|")
for name, ok, note in rows: print(f"| {name} | {'yes' if ok else 'no'} | {note} |")
