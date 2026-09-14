/**
 * Whole-dataset downloads (JSON, CSV, BibTeX), rendered at build time by the
 * endpoints in src/pages/literature*.ts.
 */
import literature from '../data/literature.json';
import { generateBibtex, uniqueCitationKeys, type BibEntry } from './bibtex';

export const REPOSITORY_URL = 'https://github.com/emmanuelgjr/GenAI-Security-Literature-Review';

export type Entry = (typeof literature.entries)[number] & Record<string, any>;

export const allEntries: Entry[] = literature.entries as Entry[];
export const reviewedEntries: Entry[] = allEntries.filter((e) => e.reviewed);

// Computed once per build: entry pages and the combined .bib must agree on keys.
export const citationKeys = uniqueCitationKeys(allEntries as unknown as BibEntry[]);

const FRAMEWORKS = ['owasp_llm_top10', 'owasp_agentic_top10', 'mitre_atlas', 'nist_ai_rmf', 'iso_42001'] as const;

export const CSV_COLUMNS = [
  'id', 'type', 'title', 'authors', 'year', 'month', 'venue', 'doi', 'arxiv_id', 'url', 'pdf_url',
  'categories', ...FRAMEWORKS, 'tags', 'reviewed', 'added_date', 'source_api', 'abstract',
] as const;

/**
 * One RFC 4180 field. Titles and abstracts come from external APIs, so cells a
 * spreadsheet would evaluate as a formula (= + - @, tab, CR) get a leading
 * apostrophe (OWASP CSV injection guidance).
 */
export function csvCell(value: unknown): string {
  let text = value === undefined || value === null ? '' : String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function csvRow(entry: Entry): string {
  const list = (values?: string[]) => (values ?? []).join('; ');
  const mappings: Record<string, string[]> = entry.framework_mappings ?? {};
  const doi = entry.doi || entry.external_ids?.doi;
  const row: Record<(typeof CSV_COLUMNS)[number], unknown> = {
    id: entry.id,
    type: entry.type,
    title: entry.title,
    authors: list(entry.authors),
    year: entry.year,
    month: entry.month,
    venue: entry.venue,
    doi,
    arxiv_id: entry.external_ids?.arxiv_id,
    url: entry.url,
    pdf_url: entry.pdf_url,
    categories: list(entry.categories),
    owasp_llm_top10: list(mappings.owasp_llm_top10),
    owasp_agentic_top10: list(mappings.owasp_agentic_top10),
    mitre_atlas: list(mappings.mitre_atlas),
    nist_ai_rmf: list(mappings.nist_ai_rmf),
    iso_42001: list(mappings.iso_42001),
    tags: list(entry.tags),
    reviewed: entry.reviewed ? 'true' : 'false',
    added_date: entry.added_date,
    source_api: entry.source_api,
    abstract: entry.abstract,
  };
  return CSV_COLUMNS.map((column) => csvCell(row[column])).join(',');
}

/** CSV with a UTF-8 BOM so Excel detects the encoding of non-ASCII titles. */
export function toCsv(entries: Entry[]): string {
  return '﻿' + [CSV_COLUMNS.join(','), ...entries.map(csvRow)].join('\r\n') + '\r\n';
}

export function toBibtex(entries: Entry[]): string {
  const header = [
    `% GenAI Security Literature Review -- ${entries.length} entries`,
    `% ${REPOSITORY_URL} (MIT License), generated ${new Date().toISOString().slice(0, 10)}`,
    '% Entries with reviewed=false in literature.json were added automatically and are not yet curated.',
  ].join('\n');
  const body = entries.map((e) => generateBibtex(e as unknown as BibEntry, citationKeys.get(e.id)));
  return `${header}\n\n${body.join('\n\n')}\n`;
}

export function toJson(entries: Entry[]): string {
  return JSON.stringify({
    name: 'GenAI Security Literature Review',
    source: REPOSITORY_URL,
    license: 'MIT',
    generated_at: new Date().toISOString(),
    entry_count: entries.length,
    reviewed_count: entries.filter((e) => e.reviewed).length,
    entries,
  });
}

export function download(body: string, contentType: string): Response {
  return new Response(body, { headers: { 'Content-Type': `${contentType}; charset=utf-8` } });
}
