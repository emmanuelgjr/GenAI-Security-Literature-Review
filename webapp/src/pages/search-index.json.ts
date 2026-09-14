// Static search index fetched by the search island.
//
// Passing literature.json to the island as props inlined every field of every
// entry (external IDs, framework mappings, PDF links, ...) into the search page
// HTML as escaped JSON, which grew past 1.5 MB. This ships only what the search
// UI reads, as a separate cacheable file.
import type { APIRoute } from 'astro';
import literature from '../data/literature.json';

export interface SearchIndexEntry {
  id: string;
  type: string;
  title: string;
  authors: string[];
  year: number;
  venue?: string;
  abstract?: string;
  url: string;
  categories: string[];
  tags?: string[];
  citation_count?: number;
  reviewed: boolean;
}

export const GET: APIRoute = () => {
  const index: SearchIndexEntry[] = literature.entries.map((e: any) => ({
    id: e.id,
    type: e.type,
    title: e.title,
    authors: e.authors,
    year: e.year,
    venue: e.venue || undefined,
    abstract: e.abstract || undefined,
    url: e.url,
    categories: e.categories,
    tags: e.tags?.length ? e.tags : undefined,
    citation_count: e.citation_count || undefined,
    reviewed: e.reviewed,
  }));
  return new Response(JSON.stringify(index), {
    headers: { 'Content-Type': 'application/json' },
  });
};
