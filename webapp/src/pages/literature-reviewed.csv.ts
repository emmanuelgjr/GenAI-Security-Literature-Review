// Dataset download: /literature-reviewed.csv (see src/lib/dataset.ts).
import type { APIRoute } from 'astro';
import { reviewedEntries, download, toCsv } from '../lib/dataset';

export const GET: APIRoute = () => download(toCsv(reviewedEntries), 'text/csv');
