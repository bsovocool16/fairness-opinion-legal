# Quickstart

0. Prerequisites are in the README: Claude Code, Python with `requests` and `beautifulsoup4`, poppler, node; on a Mac `xcode-select --install` for OCR.
1. In a Claude Code terminal session: `/plugin marketplace add bsovocool16/fairness-opinion-legal`, then `/plugin install fairness-opinion-legal@fairness-opinion-legal` (user scope); from a clone or the zip, give the folder path instead. The desktop app's Code tab picks the plugin up in its next session. From a shell the same two commands work as `claude plugin marketplace add ...` and `claude plugin install ...`. The Word renderer's npm package installs itself on first use.
2. `/fairness-opinion-legal:demo` — no setup needed: the whole path replayed on the bundled public deal, ending with the redline
   against the section as filed. `--live` runs it for real (about ten minutes; EDGAR and Opus).
3. `/fairness-opinion-legal:cold-start-interview` — two minutes: your name, the SEC contact identity, defaults, the drafter model.
4. `/fairness-opinion-legal:pipeline` — it asks whether the deal is a Rule 13e-3 going-private, then for the board book and
   the opinion letter, and walks through search, shell, draft and redline, stopping at each gate.

Outputs land in `~/.claude/plugins/config/fairness-opinion-legal/deals/<code>/`: `draft/section.txt`, `draft/log.md`,
`redline/section.docx`, `redline/redline_vs_shell.docx` and `.pdf`.

License: PolyForm Noncommercial 1.0.0 (see LICENSE.md in this folder). Required Notice: Copyright 2026 Benjamin Sovocool

An independent project by Benjamin Sovocool, not affiliated with or endorsed by Anthropic; built to the conventions of the claude-for-legal plugins.
