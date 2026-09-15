import { useState, useMemo, useEffect } from 'preact/hooks';
import Fuse from 'fuse.js';
import taxonomy from '../data/taxonomy.json';

// Category -> domain and label, from the same taxonomy the static pages use
const categoryDomain: Record<string, string> = {};
const categoryLabel: Record<string, string> = {};
for (const domain of taxonomy.domains) {
  for (const cat of domain.categories) {
    categoryDomain[cat.id] = domain.id;
    categoryLabel[cat.id] = cat.label;
  }
}

// Shape of search-index.json (see src/pages/search-index.json.ts)
interface Entry {
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

interface Props {
  basePath: string;
}

const PAGE_SIZE = 50;

function ResultCard({ entry, basePath }: { entry: Entry; basePath: string }) {
  const authors = `${entry.authors.slice(0, 3).join(', ')}${entry.authors.length > 3 ? ` +${entry.authors.length - 3}` : ''}`;
  return (
    <article class="surface-interactive group relative p-5 sm:p-6">
      <div class="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        <span class="meta-label">{entry.type}</span>
        <span class="text-gray-300" aria-hidden="true">/</span>
        <span class="num font-mono text-[11px] text-gray-500">{entry.year}</span>
        {entry.venue && (
          <span class="max-w-[16rem] truncate text-xs text-gray-500" title={entry.venue}>{entry.venue}</span>
        )}
        <span class="ml-auto">
          {entry.reviewed ? (
            <span class="status-reviewed" title="Human-reviewed">
              <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M6.4 11.2 3.2 8l1-1 2.2 2.2 5.4-5.4 1 1z" /></svg>
              Reviewed
            </span>
          ) : (
            <span class="status-unreviewed" title="Added automatically; not yet human-reviewed">Unreviewed</span>
          )}
        </span>
      </div>
      <h3 class="mt-2.5 text-[17px] font-semibold leading-snug tracking-[-0.01em] text-gray-900">
        <a
          href={`${basePath}entry/${entry.id}/`}
          class="text-gray-900 no-underline after:absolute after:inset-0 after:rounded-2xl after:content-[''] group-hover:text-primary-800"
        >
          {entry.title}
        </a>
      </h3>
      <p class="mt-1 text-sm text-gray-600">{authors}</p>
      {entry.abstract && <p class="mt-2.5 line-clamp-2 text-sm leading-relaxed text-gray-600">{entry.abstract}</p>}
      <div class="relative z-10 mt-4 flex flex-wrap items-center gap-1.5">
        {entry.categories.slice(0, 4).map((cat) => (
          <a key={cat} href={`${basePath}browse/${cat}/`} class={`chip domain-${categoryDomain[cat] ?? ''}`}>
            {categoryLabel[cat] ?? cat.replace(/-/g, ' ')}
          </a>
        ))}
        <span class="ml-auto flex items-center gap-3 pl-2">
          {(entry.citation_count ?? 0) > 0 && (
            <span class="num font-mono text-[11px] text-gray-500" title="Citation count">
              {entry.citation_count!.toLocaleString('en-US')} cit.
            </span>
          )}
          <a
            href={entry.url}
            target="_blank"
            rel="noopener noreferrer"
            class="rounded-md p-1 text-gray-400 no-underline transition-colors hover:bg-gray-100 hover:text-gray-900"
            title="Open resource"
            aria-label={`Open resource: ${entry.title} (new tab)`}
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14 5h5v5M19 5l-8 8M17 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h4" />
            </svg>
          </a>
        </span>
      </div>
    </article>
  );
}

function SkeletonCard() {
  return (
    <div class="surface p-6" aria-hidden="true">
      <div class="skeleton h-3 w-28" />
      <div class="skeleton mt-4 h-4 w-4/5" />
      <div class="skeleton mt-2 h-3 w-1/3" />
      <div class="skeleton mt-4 h-3 w-full" />
      <div class="skeleton mt-2 h-3 w-2/3" />
    </div>
  );
}

export default function SearchBar({ basePath }: Props) {
  const [entries, setEntries] = useState<Entry[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [yearFilter, setYearFilter] = useState('all');
  const [reviewedFilter, setReviewedFilter] = useState('all');
  const [limit, setLimit] = useState(PAGE_SIZE);

  useEffect(() => {
    // Support shareable links such as /search/?q=prompt+injection
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) setQuery(q);

    fetch(`${basePath}search-index.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: Entry[]) => setEntries(data))
      .catch(() => setLoadError(true));
  }, [basePath]);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (query.trim()) url.searchParams.set('q', query);
    else url.searchParams.delete('q');
    window.history.replaceState(null, '', url);
    setLimit(PAGE_SIZE);
  }, [query, typeFilter, yearFilter, reviewedFilter]);

  const list = useMemo(() => entries ?? [], [entries]);

  const fuse = useMemo(
    () =>
      new Fuse(list, {
        keys: [
          { name: 'title', weight: 0.4 },
          { name: 'abstract', weight: 0.2 },
          { name: 'authors', weight: 0.15 },
          { name: 'categories', weight: 0.1 },
          { name: 'tags', weight: 0.1 },
          { name: 'venue', weight: 0.05 },
        ],
        // By default Fuse only scores matches near the start of a field, so a
        // term past the first ~100 characters of an abstract was never found.
        ignoreLocation: true,
        threshold: 0.25,
        minMatchCharLength: 2,
      }),
    [list]
  );

  const years = useMemo(() => [...new Set(list.map((e) => e.year))].sort((a, b) => b - a), [list]);
  const types = useMemo(() => [...new Set(list.map((e) => e.type))].sort(), [list]);

  const filteredResults = useMemo(() => {
    let results: Entry[];

    if (query.trim().length >= 2) {
      results = fuse.search(query).map((r) => r.item);
    } else {
      results = [...list].sort((a, b) => b.year - a.year || (b.citation_count || 0) - (a.citation_count || 0));
    }

    if (typeFilter !== 'all') {
      results = results.filter((e) => e.type === typeFilter);
    }
    if (yearFilter !== 'all') {
      results = results.filter((e) => e.year === parseInt(yearFilter));
    }
    if (reviewedFilter !== 'all') {
      const isReviewed = reviewedFilter === 'true';
      results = results.filter((e) => e.reviewed === isReviewed);
    }

    return results;
  }, [query, typeFilter, yearFilter, reviewedFilter, fuse, list]);

  const filtersActive = typeFilter !== 'all' || yearFilter !== 'all' || reviewedFilter !== 'all';
  const resetFilters = () => {
    setTypeFilter('all');
    setYearFilter('all');
    setReviewedFilter('all');
  };

  return (
    <div>
      {/* Search input */}
      <label for="search-query" class="sr-only">Search resources</label>
      <div class="field flex items-center gap-3 px-4 focus-within:border-primary-600 focus-within:ring-4 focus-within:ring-primary-600/15">
        <svg class="h-5 w-5 shrink-0 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" />
          <path stroke-linecap="round" d="m20 20-4.2-4.2" />
        </svg>
        <input
          id="search-query"
          type="search"
          value={query}
          onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
          placeholder="Search titles, abstracts, authors, topics…"
          class="min-w-0 flex-1 border-0 bg-transparent py-4 text-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-0"
          autoFocus
        />
      </div>

      {/* Filters */}
      <div class="mt-4 flex flex-wrap items-center gap-2.5">
        <select
          aria-label="Filter by resource type"
          value={typeFilter}
          onChange={(e) => setTypeFilter((e.target as HTMLSelectElement).value)}
          class="select"
        >
          <option value="all">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>

        <select
          aria-label="Filter by year"
          value={yearFilter}
          onChange={(e) => setYearFilter((e.target as HTMLSelectElement).value)}
          class="select"
        >
          <option value="all">All years</option>
          {years.map((y) => (
            <option key={y} value={y.toString()}>{y}</option>
          ))}
        </select>

        <select
          aria-label="Filter by review status"
          value={reviewedFilter}
          onChange={(e) => setReviewedFilter((e.target as HTMLSelectElement).value)}
          class="select"
        >
          <option value="all">All entries</option>
          <option value="true">Reviewed only</option>
          <option value="false">Unreviewed only</option>
        </select>

        {filtersActive && (
          <button type="button" onClick={resetFilters} class="rounded-lg px-2 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-900/[0.04] hover:text-gray-900">
            Reset
          </button>
        )}

        <span class="num ml-auto font-mono text-xs text-gray-500" role="status" aria-live="polite">
          {entries
            ? `${filteredResults.length.toLocaleString('en-US')} result${filteredResults.length !== 1 ? 's' : ''}`
            : loadError ? '' : 'Loading index…'}
        </span>
      </div>

      <div class="mt-6 space-y-3">
        {!entries && !loadError && [0, 1, 2].map((i) => <SkeletonCard key={i} />)}

        {loadError && (
          <div class="surface px-6 py-14 text-center" role="alert">
            <p class="display text-2xl">The search index didn't load</p>
            <p class="mt-2 text-gray-600">
              Check your connection and reload, or <a href={`${basePath}browse/`}>browse by category</a>.
            </p>
          </div>
        )}

        {filteredResults.slice(0, limit).map((entry) => (
          <ResultCard key={entry.id} entry={entry} basePath={basePath} />
        ))}

        {filteredResults.length > limit && (
          <div class="flex flex-col items-center gap-3 py-6">
            <p class="num font-mono text-xs text-gray-500">
              Showing {limit} of {filteredResults.length.toLocaleString('en-US')}
            </p>
            <button type="button" onClick={() => setLimit(limit + PAGE_SIZE)} class="btn-secondary">
              Show {Math.min(PAGE_SIZE, filteredResults.length - limit)} more
            </button>
          </div>
        )}

        {entries && filteredResults.length === 0 && (
          <div class="surface px-6 py-14 text-center">
            <p class="display text-2xl">No matches</p>
            <p class="mx-auto mt-2 max-w-md text-gray-600">
              Try a broader term, check the spelling, or
              {filtersActive ? (
                <> <button type="button" onClick={resetFilters} class="font-medium text-primary-700 underline-offset-2 hover:underline">reset the filters</button>.</>
              ) : (
                <> <a href={`${basePath}browse/`}>browse by category</a>.</>
              )}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
