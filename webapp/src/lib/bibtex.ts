/**
 * BibTeX export for a literature entry.
 *
 * Picks an entry type that matches the resource (a tool is not an @article),
 * escapes LaTeX specials so titles like "S&P" or "top_k" compile, and builds a
 * conventional author-year-word citation key.
 */

export interface BibEntry {
  id: string;
  type: string;
  title: string;
  authors: string[];
  year: number;
  month?: number;
  venue?: string;
  url?: string;
  doi?: string;
  external_ids?: { arxiv_id?: string; [key: string]: string | undefined };
}

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

const LATEX_SPECIALS: Record<string, string> = {
  '\\': '\\textbackslash{}',
  '{': '\\{',
  '}': '\\}',
  '&': '\\&',
  '%': '\\%',
  '$': '\\$',
  '#': '\\#',
  '_': '\\_',
  '~': '\\textasciitilde{}',
  '^': '\\textasciicircum{}',
};

const CONFERENCE_RE =
  /conference|proceedings|symposium|workshop|usenix|neurips|nips|icml|iclr|acl|emnlp|naacl|ccs|s&p|ndss|aaai|ijcai|cvpr|iccv|eccv|kdd|www/i;

const JOURNAL_RE = /journal|transactions|letters|review|magazine|computing surveys/i;

// Corporate authors must be braced or BibTeX splits them into first/last names.
const ORGANIZATION_RE =
  /\b(foundation|institute|university|agency|organi[sz]ation|council|committee|group|team|lab|labs|inc|corp|nist|owasp|mitre|cisa|google|microsoft|openai|anthropic|deepmind|meta|ai)\b/i;

export function escapeLatex(value: string): string {
  return value.replace(/[\\{}&%$#_~^]/g, (ch) => LATEX_SPECIALS[ch]);
}

function formatAuthor(name: string): string {
  const escaped = escapeLatex(name.trim());
  return ORGANIZATION_RE.test(name) ? `{${escaped}}` : escaped;
}

function asciiWord(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

const STOPWORDS = new Set(['a', 'an', 'the', 'on', 'of', 'in', 'for', 'and', 'to', 'towards', 'toward', 'via', 'with']);

export function citationKey(entry: BibEntry): string {
  const firstAuthor = entry.authors[0] ?? '';
  const surname = asciiWord(ORGANIZATION_RE.test(firstAuthor) ? firstAuthor.split(/\s+/)[0] : firstAuthor.split(/\s+/).pop() ?? '');
  const word = entry.title
    .split(/\s+/)
    .map(asciiWord)
    .find((w) => w.length > 0 && !STOPWORDS.has(w)) ?? '';
  const key = `${surname}${entry.year}${word}`;
  return surname && word ? key : entry.id.replace(/-/g, '');
}

function entryType(entry: BibEntry): { kind: string; venueField?: string } {
  switch (entry.type) {
    case 'book':
      return { kind: 'book', venueField: 'publisher' };
    case 'report':
    case 'standard':
      return entry.venue ? { kind: 'techreport', venueField: 'institution' } : { kind: 'misc' };
    case 'paper':
      if (!entry.venue || /^arxiv/i.test(entry.venue)) return { kind: 'misc' };
      if (ORGANIZATION_RE.test(entry.venue) && !CONFERENCE_RE.test(entry.venue) && !JOURNAL_RE.test(entry.venue)) {
        return { kind: 'techreport', venueField: 'institution' };
      }
      return CONFERENCE_RE.test(entry.venue)
        ? { kind: 'inproceedings', venueField: 'booktitle' }
        : { kind: 'article', venueField: 'journal' };
    default:
      return { kind: 'misc' };
  }
}

export function generateBibtex(entry: BibEntry): string {
  const { kind, venueField } = entryType(entry);
  const fields: [string, string][] = [
    // Double braces keep acronyms like "LLM" from being lower-cased by styles.
    ['title', `{${escapeLatex(entry.title)}}`],
    ['author', entry.authors.map(formatAuthor).join(' and ')],
    ['year', String(entry.year)],
  ];
  if (entry.month && entry.month >= 1 && entry.month <= 12) fields.push(['month', MONTHS[entry.month - 1]]);
  if (venueField && entry.venue) fields.push([venueField, escapeLatex(entry.venue)]);

  const arxiv = entry.external_ids?.arxiv_id;
  if (arxiv) {
    fields.push(['eprint', arxiv], ['archivePrefix', 'arXiv']);
  }
  if (entry.doi) fields.push(['doi', entry.doi]);
  if (entry.url) fields.push(['url', entry.url]);

  const body = fields
    .map(([name, value]) => (name === 'month' ? `  ${name} = ${value}` : `  ${name} = {${value}}`))
    .join(',\n');
  return `@${kind}{${citationKey(entry)},\n${body}\n}`;
}
