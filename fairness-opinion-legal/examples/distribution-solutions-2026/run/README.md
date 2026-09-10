# A completed run, for the demo

The deal folder the plugin produced for the example deal on September 9, 2026: intake from the board book and the opinion
letter (with OCR of the slide images), the live EDGAR search for William Blair's filed sections, the shell built on ARC
Document Solutions (2024), the draft written by Opus in objective mode with its self-score and log, and the redline against
the shell. The draft was redrawn on September 10, 2026 after the reviewer found reference-only material (price targets, 52-week
range, sensitivity grids) that William Blair never files; the scorer and the task now follow the advisor's precedents, and
`history.md` records both runs. `filed/` adds what the plugin never sees while drafting: the section William Blair actually filed in the DSGR
proxy, and the draft's redline against it. `/fairness-opinion-legal:demo` replays this folder stage by stage; `--live` reruns
the chain on the same inputs into a fresh deal folder. Everything here is public EDGAR material or the plugin's own output.
