#!/usr/bin/env python3
"""Reviewer feedback notes: corrections and preferences the user gives after seeing an output, kept for later runs.
  python3 feedback.py add "<note>" [--scope all|advisor:<name>|deal:<code>] [--stage intake|search|shell|draft|redline|all] [--from <deal code>] [--deal-level <deal dir>]
  python3 feedback.py list [--for <deal dir>] [--stage <stage>]
  python3 feedback.py for <deal dir> [--stage <stage>]        the notes that apply to this deal and stage, as a block for a prompt
  python3 feedback.py remove <id>
The user's file is ~/.claude/plugins/config/fairness-opinion-legal/feedback.md (all of this user's deals); a deal folder may hold its own
feedback.md, read alongside it. --file overrides the user's file (tests). Entries are one line each and can be edited by hand."""
import sys, re, json, argparse, datetime, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from bankname import bank_key
USER_FILE = Path.home() / ".claude" / "plugins" / "config" / "fairness-opinion-legal" / "feedback.md"
STAGES = ["intake", "search", "shell", "draft", "redline", "all"]
HEADER = """# Feedback notes for fairness-opinion-legal

Corrections and preferences the reviewer gave after seeing outputs. Every stage reads the notes that apply before it starts
(`scripts/feedback.py for <deal dir> --stage <stage>`); a note scoped to an advisor or a deal applies only there. Edit or delete
lines freely; the id in brackets is only a handle for `feedback.py remove`. A note cannot add a fact the inputs lack.

Format: - [id] date · stage · scope · note (from deal)

"""
LINE = re.compile(r"^- \[([0-9a-f]{6})\] (\d{4}-\d{2}-\d{2}) · (\w+) · (all|advisor:[^·]+?|deal:[^·]+?) · (.+)$")
def parse(path, default_scope=None):
    out = []
    if not path.exists(): return out
    for l in path.read_text().splitlines():
        m = LINE.match(l.strip())
        if m: out.append({"id": m.group(1), "date": m.group(2), "stage": m.group(3), "scope": m.group(4).strip(), "note": m.group(5).strip(), "file": str(path)})
    if default_scope:
        for e in out:
            if e["scope"] == "all": e["scope"] = default_scope
    return out
def line_of(e): return f"- [{e['id']}] {e['date']} · {e['stage']} · {e['scope']} · {e['note']}"
def applies(e, advisor, code, stage):
    if stage and e["stage"] not in ("all", stage): return False
    s = e["scope"]
    if s == "all": return True
    if s.startswith("advisor:"): return bool(advisor) and bank_key(s[8:].strip()) == bank_key(advisor)
    if s.startswith("deal:"): return bool(code) and s[5:].strip().lower() == code.lower()
    return False
def deal_context(deal):
    deal = Path(deal); facts = json.load(open(deal / "facts.json")) if (deal / "facts.json").exists() else {}
    return facts.get("advisor", ""), deal.name, deal
def add(a):
    target = Path(a.deal_level) / "feedback.md" if a.deal_level else a.file
    note = a.note.strip().rstrip(".") + "."
    if a.frm and "(from " not in note: note += f" (from {a.frm})"
    e = {"id": hashlib.sha1((a.date + note).encode()).hexdigest()[:6], "date": a.date, "stage": a.stage, "scope": a.scope, "note": note}
    if not target.exists(): target.parent.mkdir(parents=True, exist_ok=True); target.write_text(HEADER)
    with open(target, "a") as f: f.write(line_of(e) + "\n")
    print(line_of(e)); print(f"saved to {target}")
def entries_for(a, deal, stage):
    advisor, code, dp = deal_context(deal)
    ents = [e for e in parse(a.file) if applies(e, advisor, code, stage)]
    ents += [e for e in parse(dp / "feedback.md", default_scope=f"deal:{code}") if applies(e, advisor, code, stage)]
    return ents
def show_for(a):
    ents = entries_for(a, a.deal, a.stage)
    if not ents: print("No feedback notes apply." if a.stage else "No feedback notes apply to this deal."); return
    print(f"Feedback notes that apply ({len(ents)}; the reviewer's corrections from earlier runs: follow them and record in the log which you applied):")
    for e in ents: print(line_of(e))
def lst(a):
    ents = entries_for(a, a.for_deal, a.stage) if a.for_deal else [e for e in parse(a.file) if not a.stage or e["stage"] in ("all", a.stage)]
    if not ents: print("No feedback notes." + (" (%s)" % a.file if not a.file.exists() else "")); return
    for e in ents: print(line_of(e) + (f"   [{Path(e['file']).parent.name}/feedback.md]" if a.for_deal and not e["file"].endswith(str(a.file)) else ""))
def remove(a):
    if not a.file.exists(): sys.exit("no notes file")
    lines = a.file.read_text().splitlines(); keep = [l for l in lines if not l.strip().startswith(f"- [{a.id}]")]
    if len(keep) == len(lines): sys.exit(f"no note with id {a.id} in {a.file}")
    a.file.write_text("\n".join(keep) + "\n"); print(f"removed {a.id}")
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--file", type=Path, default=USER_FILE); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("note"); s.add_argument("--scope", default="all"); s.add_argument("--stage", default="all", choices=STAGES); s.add_argument("--from", dest="frm", default=None); s.add_argument("--deal-level", default=None); s.add_argument("--date", default=datetime.date.today().isoformat())
    s = sub.add_parser("list"); s.add_argument("--for", dest="for_deal", default=None); s.add_argument("--stage", default=None, choices=STAGES[:-1])
    s = sub.add_parser("for"); s.add_argument("deal"); s.add_argument("--stage", default=None, choices=STAGES[:-1])
    s = sub.add_parser("remove"); s.add_argument("id")
    a = ap.parse_args()
    if a.cmd == "add":
        if not re.match(r"^(all|advisor:.+|deal:.+)$", a.scope): sys.exit("--scope must be all, advisor:<name> or deal:<code>")
        add(a)
    elif a.cmd == "list": lst(a)
    elif a.cmd == "for": show_for(a)
    else: remove(a)
