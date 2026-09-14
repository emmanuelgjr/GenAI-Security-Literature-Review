// Dataset download: /literature.bib (see src/lib/dataset.ts).
import type { APIRoute } from 'astro';
import { allEntries, download, toBibtex } from '../lib/dataset';

export const GET: APIRoute = () => download(toBibtex(allEntries), 'application/x-bibtex');
