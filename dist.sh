#!/bin/bash
# Build a distributable zip of this marketplace: dist/fairness-opinion-legal-<version>.zip, unzipping to one folder that
# `/plugin marketplace add <folder>` accepts. Leaves out node_modules, .git, caches and the compiled OCR binary.
set -e
cd "$(dirname "$0")"
V=$(python3 -c "import json; print(json.load(open('fairness-opinion-legal/.claude-plugin/plugin.json'))['version'])")
OUTDIR="${1:-dist}"; mkdir -p "$OUTDIR"; OUT="$OUTDIR/fairness-opinion-legal-$V.zip"; rm -f "$OUT"
T=$(mktemp -d); mkdir -p "$T/fairness-opinion-legal"
rsync -a --exclude node_modules --exclude .git --exclude __pycache__ --exclude .DS_Store --exclude dist --exclude "*.spec.json" --exclude "scripts/ocr/ocr" ./ "$T/fairness-opinion-legal/"
(cd "$T" && zip -qr "$OLDPWD/$OUT" fairness-opinion-legal)
rm -rf "$T"
echo "$OUT ($(du -h "$OUT" | cut -f1), $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files)"
