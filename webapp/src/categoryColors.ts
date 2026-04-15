/**
 * Maps each domain to a Tailwind color for its category tags.
 * Domain -> categories get the same color family.
 */

const domainColors: Record<string, { bg: string; text: string; hover: string }> = {
  'attacks-threats':       { bg: 'bg-red-100',    text: 'text-red-800',    hover: 'hover:bg-red-200' },
  'defenses-mitigations':  { bg: 'bg-emerald-100', text: 'text-emerald-800', hover: 'hover:bg-emerald-200' },
  'privacy':               { bg: 'bg-violet-100', text: 'text-violet-800', hover: 'hover:bg-violet-200' },
  'governance-compliance':  { bg: 'bg-amber-100',  text: 'text-amber-800',  hover: 'hover:bg-amber-200' },
  'red-teaming-evaluation': { bg: 'bg-orange-100', text: 'text-orange-800', hover: 'hover:bg-orange-200' },
  'infrastructure-deployment': { bg: 'bg-cyan-100', text: 'text-cyan-800', hover: 'hover:bg-cyan-200' },
  'agentic-ai-security':   { bg: 'bg-fuchsia-100', text: 'text-fuchsia-800', hover: 'hover:bg-fuchsia-200' },
  'surveys-meta':          { bg: 'bg-sky-100',    text: 'text-sky-800',    hover: 'hover:bg-sky-200' },
};

// Build category -> domain lookup from taxonomy
import taxonomy from './data/taxonomy.json';

const categoryToDomain: Record<string, string> = {};
for (const domain of taxonomy.domains) {
  for (const cat of domain.categories) {
    categoryToDomain[cat.id] = domain.id;
  }
}

export function getCategoryColor(categoryId: string) {
  const domainId = categoryToDomain[categoryId];
  return domainColors[domainId] || { bg: 'bg-gray-100', text: 'text-gray-700', hover: 'hover:bg-gray-200' };
}

export function getCategoryClasses(categoryId: string): string {
  const c = getCategoryColor(categoryId);
  return `${c.bg} ${c.text} ${c.hover}`;
}

export { domainColors, categoryToDomain };
