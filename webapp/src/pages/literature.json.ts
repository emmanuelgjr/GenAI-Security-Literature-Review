// Dataset download: /literature.json (see src/lib/dataset.ts).
import type { APIRoute } from 'astro';
import { allEntries, download, toJson } from '../lib/dataset';

export const GET: APIRoute = () => download(toJson(allEntries), 'application/json');
