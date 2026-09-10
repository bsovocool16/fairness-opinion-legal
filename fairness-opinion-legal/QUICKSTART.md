# Quickstart

1. In Claude Code: `/plugin marketplace add /path/to/fairness-opinion-legal`, then `/plugin install fairness-opinion-legal@fairness-opinion-legal` (user scope). From a shell the same two commands work as `claude plugin marketplace add ...` and `claude plugin install ...`. The Word renderer's npm package installs itself on first use.
2. `/fairness-opinion-legal:cold-start-interview` — two minutes: your name, the SEC contact identity, defaults.
3. `/fairness-opinion-legal:pipeline` — it asks whether the deal is a Rule 13e-3 going-private, then for the board book and
   the opinion letter, and walks through search, shell, draft and redline, stopping at each gate.

Outputs land in `~/.claude/plugins/config/fairness-opinion-legal/deals/<code>/`: `draft/section.txt`, `draft/log.md`,
`redline/section.docx`, `redline/redline_vs_shell.docx` and `.pdf`.
