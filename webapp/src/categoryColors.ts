/**
 * Category -> domain lookup. Each domain has one muted hue (see the
 * .domain-* rules in global.css) shown as a small dot on neutral chips.
 */

import taxonomy from './data/taxonomy.json';

const categoryToDomain: Record<string, string> = {};
const categoryLabels: Record<string, string> = {};
for (const domain of taxonomy.domains) {
  for (const cat of domain.categories) {
    categoryToDomain[cat.id] = domain.id;
    categoryLabels[cat.id] = cat.label;
  }
}

/** CSS class that sets --domain for a category's chip or dot. */
export function domainClass(categoryId: string): string {
  const domainId = categoryToDomain[categoryId];
  return domainId ? `domain-${domainId}` : '';
}

/** Chip classes for a category link. */
export function getCategoryClasses(categoryId: string): string {
  return `chip ${domainClass(categoryId)}`;
}

/** Human label for a category id, falling back to the id itself. */
export function categoryLabel(categoryId: string): string {
  return categoryLabels[categoryId] ?? categoryId.replace(/-/g, ' ');
}

export { categoryToDomain };
