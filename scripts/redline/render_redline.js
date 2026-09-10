// Litera-style comparison document: insertions blue double-underlined, deletions red struck, moved paragraphs green, a change
// bar at the left of every altered paragraph. Direct formatting rather than tracked changes, so it opens the same in Word,
// LibreOffice and Google Docs. Called by redline.py:  node render_redline.js spec.json out.docx
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, AlignmentType, UnderlineType, BorderStyle } = require("docx");
const [specPath, outPath] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const base = { font: "Times New Roman", size: 22 };
const style = {
  eq: (t) => new TextRun({ text: t, ...base }),
  ins: (t) => new TextRun({ text: t, color: "0000FF", underline: { type: UnderlineType.DOUBLE, color: "0000FF" }, ...base }),
  del: (t) => new TextRun({ text: t, color: "FF0000", strike: true, ...base }),
  mv: (t) => new TextRun({ text: t, color: "008000", underline: { type: UnderlineType.DOUBLE, color: "008000" }, ...base }),
  head: (t) => new TextRun({ text: t, bold: true, ...base }),
};
const s = spec.stats, L = spec.labels || { original: "original", revised: "revised" };
const n = (x) => Number(x).toLocaleString("en-US");
const cap = (x) => x.charAt(0).toUpperCase() + x.slice(1);
const children = [];
children.push(new Paragraph({ children: [new TextRun({ text: spec.title, bold: true, size: 28, font: "Times New Roman" })], spacing: { after: 120 } }));
children.push(new Paragraph({ children: [new TextRun({ text:
  `${cap(L.revised)} compared with the ${L.original}. Blue double underline: text in the ${L.revised} that is not in the ${L.original} (${n(s.inserted)} words). ` +
  `Red strikethrough: text in the ${L.original} that the ${L.revised} does not carry (${n(s.deleted)} words). Green: paragraphs the ${L.revised} carries in a different position (${n(s.moved)}). ` +
  `A bar in the left margin marks every paragraph with a change. ${cap(L.original)} ${n(s.original_words)} words; ${L.revised} ${n(s.revised_words)} words; ` +
  `${n(s.aligned)} of ${n(s.revised_paragraphs)} ${L.revised} paragraphs matched to ${L.original} paragraphs; ${n(s.unchanged)} words unchanged. ` +
  `${cap(L.original)} paragraphs the ${L.revised} does not carry are listed at the end.`, italics: true, size: 20, font: "Times New Roman" })], spacing: { after: 240 } }));
for (const para of spec.paras) {
  const changed = para.some(([k]) => k !== "eq" && k !== "head");
  const runs = para.map(([k, t]) => (style[k] || style.eq)(t));
  const opts = { children: runs, spacing: { after: 160, before: para[0][0] === "head" ? 240 : 0 }, alignment: AlignmentType.LEFT };
  if (changed) opts.border = { left: { style: BorderStyle.SINGLE, size: 12, space: 6, color: "000000" } };
  children.push(new Paragraph(opts));
}
const doc = new Document({ sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children }] });
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote " + outPath + " (" + spec.paras.length + " paragraphs)"); });
