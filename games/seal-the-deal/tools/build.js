// Inline src/ into two single-file builds:
//   dist/seal-the-deal.html  — standalone page, open it straight from disk
//   dist/artifact.html       — same content without the document skeleton (for the Claude artifact viewer)
const fs = require('fs'), path = require('path');
const src = (f) => fs.readFileSync(path.join(__dirname, '..', 'src', f), 'utf8');
let tpl = src('index.html')
  .replace('/*STYLE*/', () => src('style.css'))
  .replace('/*ENGINE*/', () => src('engine.js'))
  .replace('/*GAME*/', () => src('game.js'));
const [head, body] = tpl.split('<!--BODY-->');
const dist = path.join(__dirname, '..', 'dist');
fs.mkdirSync(dist, { recursive: true });
fs.writeFileSync(path.join(dist, 'artifact.html'), head + body);
fs.writeFileSync(path.join(dist, 'seal-the-deal.html'),
  `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n${head}</head>\n<body>\n${body}</body>\n</html>\n`);
console.log('built', fs.statSync(path.join(dist, 'seal-the-deal.html')).size, 'bytes');
