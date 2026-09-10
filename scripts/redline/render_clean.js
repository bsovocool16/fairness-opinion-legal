// Clean draft as .docx: paragraphs, headings and real Word tables from a JSON spec written by make_outputs.py.
// node render_clean.js spec.json out.docx
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle } = require("docx");
const [specPath, outPath] = process.argv.slice(2); const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const base = { font: "Times New Roman", size: 22 }; const children = [];
if (spec.header) children.push(new Paragraph({ children: [new TextRun({ text: spec.header, bold: true, size: 18, font: "Times New Roman" })], alignment: AlignmentType.CENTER, spacing: { after: 240 } }));
for (const b of spec.blocks) {
  if (b.type === "h") children.push(new Paragraph({ children: [new TextRun({ text: b.text, bold: true, ...base })], spacing: { before: 200, after: 120 }, keepNext: true }));
  else if (b.type === "table") {
    const cols = Math.max(...b.rows.map(r => r.length)); const width = 9360; const cw = Math.floor(width / cols);
    const rows = b.rows.map((r, i) => new TableRow({ children: Array.from({ length: cols }, (_, j) => new TableCell({ width: { size: cw, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: r[j] || "", bold: i === 0, font: "Times New Roman", size: 18 })], alignment: j === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT })] })) }));
    children.push(new Table({ rows, width: { size: width, type: WidthType.DXA }, columnWidths: Array(cols).fill(cw) })); children.push(new Paragraph({ children: [], spacing: { after: 120 } }));
  } else children.push(new Paragraph({ children: [new TextRun({ text: b.text, ...base })], spacing: { after: 160 }, alignment: AlignmentType.JUSTIFIED }));
}
const doc = new Document({ sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children }] });
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(outPath, buf); console.log("wrote " + outPath); });
