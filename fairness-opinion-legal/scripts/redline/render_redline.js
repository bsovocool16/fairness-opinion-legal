// Litera-style comparison document: insertions blue double-underlined, deletions red struck, moved paragraphs green, a change
// bar at the left of every altered paragraph. Table rows (runs separated by `sep` runs) are drawn as real table rows, so a
// changed cell shows its old value struck and the new one underlined inside the cell. Direct formatting rather than tracked
// changes, so it opens the same in Word, LibreOffice and Google Docs. Called by redline.py:  node render_redline.js spec.json out.docx
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, UnderlineType, BorderStyle } = require("docx");
const [specPath, outPath] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const styleFor = (size) => {
  const base = { font: "Times New Roman", size };
  return {
    eq: (t) => new TextRun({ text: t, ...base }),
    ins: (t) => new TextRun({ text: t, color: "0000FF", underline: { type: UnderlineType.DOUBLE, color: "0000FF" }, ...base }),
    del: (t) => new TextRun({ text: t, color: "FF0000", strike: true, ...base }),
    mv: (t) => new TextRun({ text: t, color: "008000", underline: { type: UnderlineType.DOUBLE, color: "008000" }, ...base }),
    head: (t) => new TextRun({ text: t, bold: true, ...base }),
  };
};
const style = styleFor(22), small = styleFor(18);
const s = spec.stats, L = spec.labels || { original: "original", revised: "revised" };
const n = (x) => Number(x).toLocaleString("en-US");
const cap = (x) => x.charAt(0).toUpperCase() + x.slice(1);
const isRow = (para) => para.length > 0 && para[0][0] === "sep";
const cellsOf = (para) => {                       // runs between `sep` runs are one cell
  const cells = []; let cur = null;
  for (const [k, t] of para) { if (k === "sep") { if (cur !== null) cells.push(cur); cur = []; } else { if (cur === null) cur = []; cur.push([k, t]); } }
  if (cur !== null && cur.length) cells.push(cur);
  return cells;
};
const thin = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: thin, bottom: thin, left: thin, right: thin };
const children = [];
children.push(new Paragraph({ children: [new TextRun({ text: spec.title, bold: true, size: 28, font: "Times New Roman" })], spacing: { after: 120 } }));
children.push(new Paragraph({ children: [new TextRun({ text:
  `${cap(L.revised)} compared with the ${L.original}. Blue double underline: text in the ${L.revised} that is not in the ${L.original} (${n(s.inserted)} words). ` +
  `Red strikethrough: text in the ${L.original} that the ${L.revised} does not carry (${n(s.deleted)} words). Green: paragraphs the ${L.revised} carries in a different position (${n(s.moved)}). ` +
  `A bar in the left margin marks every paragraph with a change; in a table, a changed cell shows the old value struck and the new value underlined. ${cap(L.original)} ${n(s.original_words)} words; ${L.revised} ${n(s.revised_words)} words; ` +
  `${n(s.aligned)} of ${n(s.revised_paragraphs)} ${L.revised} paragraphs and rows matched to the ${L.original}; ${n(s.unchanged)} words unchanged. ` +
  `${cap(L.original)} paragraphs the ${L.revised} does not carry are listed at the end.`, italics: true, size: 20, font: "Times New Roman" })], spacing: { after: 240 } }));
let pending = [];
const flushTable = () => {
  if (!pending.length) return;
  const ncols = Math.max(...pending.map((c) => c.length));
  const first = ncols > 1 ? Math.floor(9360 * Math.min(0.34, 2.2 / (ncols + 1.2))) : 9360;   // the label column gets more room
  const rest = ncols > 1 ? Math.floor((9360 - first) / (ncols - 1)) : 0; const widths = Array.from({ length: ncols }, (_, i) => (i === 0 ? first : rest));
  const rows = pending.map((cells) => new TableRow({ children: Array.from({ length: ncols }, (_, i) => {
    const runs = (cells[i] || [["eq", ""]]).map(([k, t]) => (small[k] || small.eq)(t));
    return new TableCell({ children: [new Paragraph({ children: runs, alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT })], width: { size: widths[i], type: WidthType.DXA }, borders, margins: { top: 40, bottom: 40, left: 80, right: 80 } });
  }) }));
  children.push(new Table({ rows, width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths }));
  children.push(new Paragraph({ children: [], spacing: { after: 120 } }));
  pending = [];
};
for (const para of spec.paras) {
  if (isRow(para)) { pending.push(cellsOf(para)); continue; }
  flushTable();
  const changed = para.some(([k]) => k !== "eq" && k !== "head");
  const runs = para.map(([k, t]) => (style[k] || style.eq)(t));
  const opts = { children: runs, spacing: { after: 160, before: para[0][0] === "head" ? 240 : 0 }, alignment: AlignmentType.LEFT };
  if (changed) opts.border = { left: { style: BorderStyle.SINGLE, size: 12, space: 6, color: "000000" } };
  children.push(new Paragraph(opts));
}
flushTable();
const doc = new Document({ sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children }] });
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote " + outPath + " (" + spec.paras.length + " paragraphs)"); });
