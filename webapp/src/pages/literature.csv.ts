// Dataset download: /literature.csv (see src/lib/dataset.ts).
import type { APIRoute } from 'astro';
import { allEntries, download, toCsv } from '../lib/dataset';

export const GET: APIRoute = () => download(toCsv(allEntries), 'text/csv');
