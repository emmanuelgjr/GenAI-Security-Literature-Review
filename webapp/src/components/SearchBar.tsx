import { useState, useMemo, useEffect } from 'preact/hooks';
import Fuse from 'fuse.js';

// Category -> domain color mapping (mirrors categoryColors.ts for Preact island)
const categoryDomainMap: Record<string, string> = {
  'prompt-injection': 'attacks', jailbreaking: 'attacks', 'data-poisoning': 'attacks',
  'model-extraction': 'attacks', 'membership-inference': 'attacks', 'adversarial-examples': 'attacks',
  'supply-chain-attacks': 'attacks', 'social-engineering': 'attacks', 'agentic-threats': 'attacks',
  'input-filtering': 'defenses', 'output-moderation': 'defenses', guardrails: 'defenses',
  'access-control': 'defenses', 'monitoring-detection': 'defenses', 'sandboxing-isolation': 'defenses',
  'cryptographic-controls': 'defenses', watermarking: 'defenses',
  'differential-privacy': 'privacy', 'federated-learning': 'privacy', 'data-anonymization': 'privacy',
  unlearning: 'privacy', 'confidential-computing': 'privacy',
  'risk-frameworks': 'governance', 'model-governance': 'governance', 'audit-assurance': 'governance',
  'responsible-ai': 'governance', 'incident-response': 'governance',
  'red-teaming': 'redteam', benchmarks: 'redteam', fuzzing: 'redteam', 'vulnerability-disclosure': 'redteam',
  'model-serving-security': 'infra', 'rag-security': 'infra', 'fine-tuning-security': 'infra',
  'mlops-security': 'infra', 'cloud-ai-security': 'infra',
  'agent-architecture': 'agentic', 'tool-use-security': 'agentic', 'memory-security': 'agentic',
  'human-in-the-loop': 'agentic', 'autonomous-operations': 'agentic',
  survey: 'meta', 'threat-modeling': 'meta', 'industry-report': 'meta',
  book: 'meta', 'conference-proceedings': 'meta',
};

const domainColorClasses: Record<string, string> = {
  attacks: 'bg-red-100 text-red-800',
  defenses: 'bg-emerald-100 text-emerald-800',
  privacy: 'bg-violet-100 text-violet-800',
  governance: 'bg-amber-100 text-amber-800',
  redteam: 'bg-orange-100 text-orange-800',
  infra: 'bg-cyan-100 text-cyan-800',
  agentic: 'bg-fuchsia-100 text-fuchsia-800',
  meta: 'bg-sky-100 text-sky-800',
};

function getCatColor(cat: string): string {
  const domain = categoryDomainMap[cat];
  return domainColorClasses[domain] || 'bg-gray-100 text-gray-700';
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

const typeColors: Record<string, string> = {
  paper: 'bg-blue-100 text-blue-800',
  book: 'bg-purple-100 text-purple-800',
  report: 'bg-orange-100 text-orange-800',
  tool: 'bg-green-100 text-green-800',
  standard: 'bg-red-100 text-red-800',
  talk: 'bg-gray-100 text-gray-800',
  blog: 'bg-gray-100 text-gray-800',
  dataset: 'bg-green-100 text-green-800',
};

const PAGE_SIZE = 50;
const selectClass =
  'border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-primary-500 focus:border-primary-500';

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

  return (
    <div>
      {/* Search input */}
      <div class="mb-6">
        <label for="search-query" class="sr-only">Search resources</label>
        <div class="relative">
          <svg
            class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            id="search-query"
            type="search"
            value={query}
            onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
            placeholder="Search papers, authors, topics..."
            class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-lg"
            autoFocus
          />
        </div>
      </div>

      {/* Filters */}
      <div class="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by resource type"
          value={typeFilter}
          onChange={(e) => setTypeFilter((e.target as HTMLSelectElement).value)}
          class={selectClass}
        >
          <option value="all">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <select
          aria-label="Filter by year"
          value={yearFilter}
          onChange={(e) => setYearFilter((e.target as HTMLSelectElement).value)}
          class={selectClass}
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
          class={selectClass}
        >
          <option value="all">All entries</option>
          <option value="true">Reviewed only</option>
          <option value="false">Unreviewed</option>
        </select>

        <span class="text-sm text-gray-500 self-center ml-auto" role="status" aria-live="polite">
          {entries
            ? `${filteredResults.length} result${filteredResults.length !== 1 ? 's' : ''}`
            : loadError ? '' : 'Loading…'}
        </span>
      </div>

      {loadError && (
        <div class="text-center py-12" role="alert">
          <p class="text-gray-700 text-lg">The search index could not be loaded.</p>
          <p class="text-gray-500 text-sm mt-2">
            Try reloading, or <a href={`${basePath}browse/`}>browse by category</a>.
          </p>
        </div>
      )}

      {/* Results */}
      <div class="space-y-4">
        {filteredResults.slice(0, limit).map((entry) => (
          <div key={entry.id} class="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-2 flex-wrap">
                  <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${typeColors[entry.type] || 'bg-gray-100 text-gray-800'}`}>
                    {entry.type}
                  </span>
                  {entry.reviewed ? (
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      reviewed
                    </span>
                  ) : (
                    <span
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-900"
                      title="Added automatically; not yet human-reviewed"
                    >
                      unreviewed
                    </span>
                  )}
                  <span class="text-xs text-gray-500">{entry.year}</span>
                </div>
                <h3 class="text-lg font-semibold mb-1">
                  <a href={`${basePath}entry/${entry.id}/`} class="text-primary-600 hover:text-primary-800 hover:underline">
                    {entry.title}
                  </a>
                </h3>
                <p class="text-sm text-gray-600 mb-2">
                  {entry.authors.slice(0, 3).join(', ')}
                  {entry.authors.length > 3 ? ` + ${entry.authors.length - 3} more` : ''}
                  {entry.venue && <span class="text-gray-500"> &mdash; {entry.venue}</span>}
                </p>
                {entry.abstract && (
                  <p class="text-sm text-gray-700 mb-3 line-clamp-2">{entry.abstract}</p>
                )}
                <div class="flex items-center gap-2 flex-wrap">
                  {entry.categories.slice(0, 4).map((cat) => (
                    <span key={cat} class={`text-xs px-2 py-0.5 rounded font-medium ${getCatColor(cat)}`}>
                      {cat.replace(/-/g, ' ')}
                    </span>
                  ))}
                  {(entry.citation_count ?? 0) > 0 && (
                    <span class="text-xs text-gray-500 ml-auto">
                      {entry.citation_count} citations
                    </span>
                  )}
                </div>
              </div>
              <a
                href={entry.url}
                target="_blank"
                rel="noopener noreferrer"
                class="shrink-0 text-gray-500 hover:text-primary-600"
                title="Open resource"
                aria-label={`Open resource: ${entry.title} (new tab)`}
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        ))}
        {filteredResults.length > limit && (
          <div class="text-center py-4">
            <p class="text-gray-500 mb-3">
              Showing {limit} of {filteredResults.length} results.
            </p>
            <button
              type="button"
              onClick={() => setLimit(limit + PAGE_SIZE)}
              class="bg-white text-primary-600 px-4 py-2 rounded-md text-sm font-medium border border-primary-600 hover:bg-primary-50"
            >
              Show more
            </button>
          </div>
        )}
        {entries && filteredResults.length === 0 && (
          <div class="text-center py-12">
            <p class="text-gray-500 text-lg">No results found</p>
            <p class="text-gray-500 text-sm mt-2">Try different keywords or adjust the filters</p>
          </div>
        )}
      </div>
    </div>
  );
}
