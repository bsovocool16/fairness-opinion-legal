"""Deliverables for a deal: clean draft (.docx and .txt), redline of the draft against the shell (and against a prior draft),
as .docx and .pdf, with the profile's work-product header. python3 make_outputs.py <deal dir> [--prior <file>]"""
import sys, re, json, argparse, subprocess, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent; RED = HERE / "redline"
PROFILE = Path.home() / ".claude" / "plugins" / "config" / "fairness-opinion-legal" / "CLAUDE.md"
def header():
    if PROFILE.exists():
        for line in PROFILE.read_text().splitlines():
            if "Work-product header" in line and ":" in line:
                v = line.split(":", 1)[1].strip(); v = re.sub(r"^\[DEFAULT:\s*|\]$", "", v).strip().strip('"'); return v
    return "DRAFT — ATTORNEY WORK PRODUCT — FOR REVIEW — NOT FOR FILING"
def blocks_of(text):
    out, rows = [], []
    def flush():
        nonlocal rows
        if rows: out.append({"type": "table", "rows": rows}); rows = []
    for para in re.split(r"\n\s*\n", text):
        lines = [l for l in para.split("\n") if l.strip()]
        for l in lines:
            s = l.strip()
            if s.startswith("|"):
                if re.match(r"^\|(\s*:?-+:?\s*\|)+\s*$", s): continue
                rows.append([c.strip() for c in s.strip("|").split("|")]); continue
            flush()
            if len(s) < 90 and not re.search(r"[.;:,]$", s) and not s.startswith("•") and len(s.split()) <= 12: out.append({"type": "h", "text": s})
            else: out.append({"type": "p", "text": s})
        flush()
    return out
ap = argparse.ArgumentParser(); ap.add_argument("deal"); ap.add_argument("--prior", default=None); a = ap.parse_args()
deal = Path(a.deal); draft = deal / "draft" / "section.txt"; out = deal / "redline"; out.mkdir(exist_ok=True)
if not draft.exists(): sys.exit("no draft/section.txt")
def ensure_docx():
    """The Word renderer's one npm dependency, installed on first use so the plugin works straight from the marketplace copy."""
    if (RED / "node_modules" / "docx").exists(): return True
    if not (shutil.which("node") and shutil.which("npm")): return False
    print("installing the docx package for the Word renderer (once: npm install in scripts/redline)...")
    try: r = subprocess.run(["npm", "install", "--silent", "--no-audit", "--no-fund"], cwd=RED, capture_output=True, text=True, timeout=300)
    except Exception as e: print(f"npm install failed: {e}"); return False
    if r.returncode: print("npm install failed: " + (r.stderr.strip()[-300:] or r.stdout.strip()[-300:]))
    return (RED / "node_modules" / "docx").exists()
text = draft.read_text(); hdr = header(); node_ok = ensure_docx()
(out / "section.txt").write_text(hdr + "\n\n" + text)
markers = re.findall(r"\[REVIEWER:[^\]]*\]", text)
if node_ok:
    spec = out / "section.spec.json"; json.dump({"header": hdr, "blocks": blocks_of(text)}, open(spec, "w")); r = subprocess.run(["node", str(RED / "render_clean.js"), str(spec), str(out / "section.docx")], capture_output=True, text=True); spec.unlink(missing_ok=True); print(r.stdout.strip() or r.stderr.strip()[:200])
else: print("docx skipped: node or the docx package is missing (run `npm install` in scripts/redline)")
shell = deal / "shell" / "shell_composite_eligible.txt"
if not shell.exists(): shell = deal / "shell" / "shell_suggested.txt"
pairs = [("redline_vs_shell", shell, "shell")] + ([("redline_vs_prior", Path(a.prior), "prior draft")] if a.prior else [])
for name, orig, label in pairs:
    if not orig.exists(): print(f"{name}: {orig} missing"); continue
    if node_ok:
        r = subprocess.run([sys.executable, str(RED / "redline.py"), str(orig), str(draft), str(out / f"{name}.docx"), "--pdf", "--title", f"{hdr} — draft compared with the {label}", "--label-original", label, "--label-revised", "draft"], capture_output=True, text=True)
        lines = [l for l in r.stdout.strip().splitlines() if l.strip()]; print(f"{name}: " + (lines[-1] if lines else r.stderr.strip()[:200]))
    else:
        sys.path.insert(0, str(RED)); import redline as RL
        O, _ = RL.split_paragraphs(orig.read_text(), "auto"); R, _ = RL.split_paragraphs(text, "auto"); paras, al = RL.diff_aligned(O, R); lines = []
        for p in paras:
            s = "".join(t if k in ("eq", "mv") else ("[-" + t.rstrip() + "-] " if k == "del" else ("{+" + t.rstrip() + "+} " if k == "ins" else "\n## " + t)) for k, t in p); lines.append(s.strip()); lines.append("")
        (out / f"{name}.txt").write_text("\n".join(lines)); print(f"{name}: text redline only ({al}); docx needs node and `npm install` in scripts/redline")
print(f"reviewer markers in the draft: {len(markers)}" + (": " + "; ".join(markers[:10]) if markers else ""))
