// Server statico minimale per l'export web di Expo (`npx expo export --platform web`).
//
// Perché non `npx serve`: è una dipendenza in più da scaricare a ogni verifica,
// mentre Node è già richiesto da Expo. In più qui il fallback SPA è esplicito:
// se un percorso non esiste (deep link di react-navigation su web) rispondiamo
// con `index.html`, come farebbe un host reale.
//
// Uso: node scripts/serve-web.mjs <cartella-export> [porta]

import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { extname, join, normalize, resolve } from 'node:path';

const [, , dirArg, portArg] = process.argv;
if (!dirArg) {
  console.error('Uso: node scripts/serve-web.mjs <cartella-export> [porta]');
  process.exit(1);
}

const ROOT = resolve(dirArg);
const PORT = Number(portArg || process.env.PORT || 3000);

if (!existsSync(join(ROOT, 'index.html'))) {
  console.error(`Nessun index.html in ${ROOT}: manca l'export web?`);
  process.exit(1);
}

// Tipi serviti dall'export di Expo/Metro.
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.ttf': 'font/ttf',
  '.otf': 'font/otf',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.map': 'application/json; charset=utf-8',
};

// True solo se il percorso risolto resta dentro ROOT: evita il path traversal.
const isInsideRoot = (target) =>
  target === ROOT || target.startsWith(ROOT + (process.platform === 'win32' ? '\\' : '/'));

const server = createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  const candidate = resolve(join(ROOT, normalize(urlPath)));

  let file = isInsideRoot(candidate) ? candidate : null;
  if (file && existsSync(file) && statSync(file).isDirectory()) {
    file = join(file, 'index.html');
  }
  // Fallback SPA: qualunque rotta sconosciuta torna index.html.
  if (!file || !existsSync(file)) {
    file = join(ROOT, 'index.html');
  }

  res.writeHead(200, {
    'Content-Type': MIME[extname(file).toLowerCase()] || 'application/octet-stream',
    'Cache-Control': 'no-store',
  });
  createReadStream(file).pipe(res);
});

server.listen(PORT, () => {
  console.log(`Export web su http://localhost:${PORT} (da ${ROOT})`);
  console.log('Ctrl+C per fermare.');
});
