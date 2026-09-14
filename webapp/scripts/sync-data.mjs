// Copy the canonical data files from ../data into src/data so pages can import
// them. src/data is gitignored: data/ at the repo root is the single source of
// truth, and a committed copy here silently drifts out of date.
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const webapp = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(webapp, '..', 'data');
const target = join(webapp, 'src', 'data');

mkdirSync(target, { recursive: true });
for (const name of ['literature.json', 'taxonomy.json', 'frameworks.json']) {
  copyFileSync(join(source, name), join(target, name));
  console.log(`synced data/${name} -> webapp/src/data/${name}`);
}
