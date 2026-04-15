import { useState, useMemo } from 'preact/hooks';
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
  framework_mappings?: Record<string, string[]>;
  citation_count?: number;
  open_access?: boolean;
  reviewed?: boolean;
  tags?: string[];
}

interface Props {
  entries: Entry[];
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

export default function SearchBar({ entries, basePath }: Props) {
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [yearFilter, setYearFilter] = useState('all');
  const [reviewedFilter, setReviewedFilter] = useState('all');

  const fuse = useMemo(
    () =>
      new Fuse(entries, {
        keys: [
          { name: 'title', weight: 0.4 },
          { name: 'abstract', weight: 0.2 },
          { name: 'authors', weight: 0.15 },
          { name: 'categories', weight: 0.1 },
          { name: 'tags', weight: 0.1 },
          { name: 'venue', weight: 0.05 },
        ],
        threshold: 0.35,
        includeScore: true,
        minMatchCharLength: 2,
      }),
    [entries]
  );

  const years = useMemo(() => {
    const yrs = [...new Set(entries.map((e) => e.year))].sort((a, b) => b - a);
    return yrs;
  }, [entries]);

  const types = useMemo(() => {
    return [...new Set(entries.map((e) => e.type))].sort();
  }, [entries]);

  const filteredResults = useMemo(() => {
    let results: Entry[];

    if (query.trim().length >= 2) {
      results = fuse.search(query).map((r) => r.item);
    } else {
      results = [...entries].sort((a, b) => b.year - a.year || (b.citation_count || 0) - (a.citation_count || 0));
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
  }, [query, typeFilter, yearFilter, reviewedFilter, fuse, entries]);

  return (
    <div>
      {/* Search input */}
      <div class="mb-6">
        <div class="relative">
          <svg
            class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
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
          value={typeFilter}
          onChange={(e) => setTypeFilter((e.target as HTMLSelectElement).value)}
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="all">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <select
          value={yearFilter}
          onChange={(e) => setYearFilter((e.target as HTMLSelectElement).value)}
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="all">All years</option>
          {years.map((y) => (
            <option key={y} value={y.toString()}>{y}</option>
          ))}
        </select>

        <select
          value={reviewedFilter}
          onChange={(e) => setReviewedFilter((e.target as HTMLSelectElement).value)}
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="all">All entries</option>
          <option value="true">Reviewed only</option>
          <option value="false">Unreviewed</option>
        </select>

        <span class="text-sm text-gray-500 self-center ml-auto">
          {filteredResults.length} result{filteredResults.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Results */}
      <div class="space-y-4">
        {filteredResults.slice(0, 50).map((entry) => (
          <div key={entry.id} class="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-2 flex-wrap">
                  <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${typeColors[entry.type] || 'bg-gray-100 text-gray-800'}`}>
                    {entry.type}
                  </span>
                  {entry.reviewed && (
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      reviewed
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
                  {entry.venue && <span class="text-gray-400"> &mdash; {entry.venue}</span>}
                </p>
                {entry.abstract && (
                  <p class="text-sm text-gray-700 mb-3" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {entry.abstract}
                  </p>
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
                class="shrink-0 text-gray-400 hover:text-primary-600"
                title="Open resource"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        ))}
        {filteredResults.length > 50 && (
          <p class="text-center text-gray-500 py-4">
            Showing first 50 of {filteredResults.length} results. Refine your search to see more.
          </p>
        )}
        {filteredResults.length === 0 && (
          <div class="text-center py-12">
            <p class="text-gray-500 text-lg">No results found</p>
            <p class="text-gray-400 text-sm mt-2">Try different keywords or adjust the filters</p>
          </div>
        )}
      </div>
    </div>
  );
}
