// Generates one collectible art per species via the Prodia v2 inference API.
// The API key is read from PRODIA_KEY (never hard-coded, never committed).
//
//   PRODIA_KEY=... node scripts/animal-art/generate.mjs            # all missing
//   PRODIA_KEY=... node scripts/animal-art/generate.mjs lion fox   # only these codes
//   PRODIA_KEY=... node scripts/animal-art/generate.mjs --force …  # re-generate even if present
//
// Output: public/animals/<code>.png (1024×1024). Existing files are skipped unless --force.

import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, '..', '..');
const OUT_DIR = join(REPO, 'public', 'animals');
const ENDPOINT = 'https://inference.prodia.com/v2/job';
const TXT2IMG = 'inference.flux-fast.schnell.txt2img.v2';
// Chain txt2img → remove-background so every animal lands on a transparent background.
// FLUX renders an inconsistent backdrop each run (white, beige, peach…); stripping it is
// what makes the 40-strong set read as one collection on any UI surface.
const REMOVE_BG = 'inference.remove-background.v1';

const KEY = process.env.PRODIA_KEY;
if (!KEY) {
  console.error('PRODIA_KEY is not set');
  process.exit(1);
}

const args = process.argv.slice(2);
const force = args.includes('--force');
const only = args.filter(a => !a.startsWith('--'));

const manifest = JSON.parse(readFileSync(join(HERE, 'manifest.json'), 'utf8'));
const { prefix, suffix } = manifest.style;

function promptFor(sp) {
  return `${prefix} ${sp.subject}, ${suffix}`;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

const isPng = b => b.length > 1000 && b.subarray(1, 4).toString() === 'PNG';

// Minimal multipart/form-data parser over a Buffer. The remove-background job returns two
// PNG parts — `foreground` (transparent) and `mask`; we want the foreground.
function parseMultipart(buf, boundary) {
  const delim = Buffer.from(`--${boundary}`);
  const parts = [];
  let start = buf.indexOf(delim);
  while (start !== -1) {
    const from = start + delim.length;
    if (buf.subarray(from, from + 2).toString() === '--') break; // closing boundary
    const headerEnd = buf.indexOf('\r\n\r\n', from);
    if (headerEnd === -1) break;
    const headers = buf.subarray(from, headerEnd).toString();
    const next = buf.indexOf(delim, headerEnd);
    const bodyEnd = next === -1 ? buf.length : next - 2; // trim trailing \r\n
    parts.push({ headers, body: buf.subarray(headerEnd + 4, bodyEnd) });
    start = next;
  }
  return parts;
}

function pickForeground(buf, contentType) {
  // Chained response is multipart; a bare PNG means the chain returned a single image.
  if (isPng(buf)) return buf;
  const m = /boundary=([^;]+)/i.exec(contentType || '');
  if (!m) throw new Error(`no multipart boundary in "${contentType}"`);
  const parts = parseMultipart(buf, m[1].trim().replace(/^"|"$/g, ''));
  const named = parts.find(p => /name="?foreground"?/i.test(p.headers) && isPng(p.body));
  const chosen = named?.body ?? parts.find(p => isPng(p.body))?.body;
  if (!chosen) throw new Error(`no PNG part in ${parts.length} multipart parts`);
  return chosen;
}

async function generate(sp) {
  const body = JSON.stringify({
    type: 'workflow.serial.v1',
    config: {
      jobs: [
        { type: TXT2IMG, config: { prompt: promptFor(sp) } },
        { type: REMOVE_BG },
      ],
    },
  });
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${KEY}`,
          'Content-Type': 'application/json',
          Accept: 'multipart/form-data; image/png',
        },
        body,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${text.slice(0, 160)}`);
      }
      const buf = Buffer.from(await res.arrayBuffer());
      const png = pickForeground(buf, res.headers.get('content-type'));
      writeFileSync(join(OUT_DIR, `${sp.code}.png`), png);
      return png.length;
    } catch (e) {
      if (attempt === 4) throw e;
      await sleep(attempt * 2500);
    }
  }
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  let list = manifest.species;
  if (only.length) list = list.filter(s => only.includes(s.code));

  const todo = list.filter(s => force || !existsSync(join(OUT_DIR, `${s.code}.png`)));
  console.log(`${todo.length} to generate (${list.length - todo.length} already present)`);

  let ok = 0;
  for (const sp of todo) {
    process.stdout.write(`  ${sp.code} (${sp.name})… `);
    try {
      const bytes = await generate(sp);
      ok++;
      console.log(`ok ${(bytes / 1024).toFixed(0)}kb`);
    } catch (e) {
      console.log(`FAILED: ${e.message}`);
    }
    await sleep(1500); // gentle pacing between jobs (avoids 429 rate limits)
  }
  console.log(`\nDone: ${ok}/${todo.length} generated. Output: public/animals/`);
}

main();
