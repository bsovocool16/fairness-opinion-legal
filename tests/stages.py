"""The pipeline's deterministic stages, declared once so that the golden tests (and any later end-to-end test) can run them
in order on a deal folder and snapshot what each one writes.

To cover a new stage (for example a ticker-to-model or model-to-deck step), add a Stage here with the command it runs and the
files it writes, then run `make golden-update` once and review the new files under tests/golden/expected/<stage name>/.
Stages run in list order inside one deal folder, so a stage may read what an earlier stage wrote.

Stages that call the network or a model (precedent search, drafting) are not here: the example deal ships their outputs
(precedents/, draft/section.txt) and the stages below start from those."""
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

@dataclass
class Stage:
    name: str                                   # also the folder under tests/golden/expected/
    argv: Sequence[str] = ()                    # script and arguments, run with cwd = the deal folder ("." is the deal)
    outputs: Sequence[str] = ()                 # files the stage writes, relative to the deal folder, snapshotted
    stdout: bool = False                        # snapshot stdout too
    fn: Optional[Callable] = None               # in-process stage instead of a script: fn(deal_dir) -> {snapshot name: text}
    needs: Sequence[str] = field(default_factory=tuple)   # conftest capability flags: "node", "soffice"

def redline_text(deal):
    """The comparison of the draft with the shell as text ([-deleted-] {+inserted+}), the same alignment make_outputs and the
    Word renderer use, so a change in the diff shows up here as a readable golden diff without node."""
    import json, redline as RL
    O, mo = RL.split_paragraphs((deal / "shell" / "shell_composite_eligible.txt").read_text(), "auto")
    R, mr = RL.split_paragraphs((deal / "draft" / "section.txt").read_text(), "auto")
    paras, al = RL.diff_aligned(O, R); lines = []
    for p in paras:
        lines.append("".join(t if k in ("eq", "mv", "sep") else ("[-" + t.rstrip() + "-] " if k == "del" else ("{+" + t.rstrip() + "+} " if k == "ins" else "## " + t)) for k, t in p).strip())
    return {"redline_vs_shell.txt": "\n\n".join(lines) + "\n", "stats.json": json.dumps({**al, "reflow": {"original": mo, "revised": mr}}, indent=1) + "\n"}

STAGES = [
    Stage("classify_book", ["classify_book.py", "."], ["deck_analyses.json"], stdout=True),
    Stage("build_shell", ["build_shell.py", "."], ["shell/rationale.json", "shell/provenance.json", "shell/shell_suggested.txt", "shell/shell_composite.txt", "shell/shell_composite_eligible.txt"], stdout=True),
    Stage("selfscore", ["selfscore.py", ".", "draft/section.txt"], ["draft/selfscore.json"]),
    Stage("redline", fn=redline_text),
    Stage("make_outputs", ["make_outputs.py", "."], ["redline/section.txt"]),
]
