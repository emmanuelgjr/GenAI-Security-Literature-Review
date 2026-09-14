// Dataset download: /literature-reviewed.bib (see src/lib/dataset.ts).
import type { APIRoute } from 'astro';
import { reviewedEntries, download, toBibtex } from '../lib/dataset';

export const GET: APIRoute = () => download(toBibtex(reviewedEntries), 'application/x-bibtex');
