/**
 * Topic metadata, sorting, and tag handling.
 */

import type { TopicMeta } from './content';
import type { Lang } from './i18n';

export function getTopicTitle(meta: TopicMeta, lang: Lang): string {
  return meta.title[lang] ?? meta.title.de;
}

export function getTopicDescription(meta: TopicMeta, lang: Lang): string {
  return meta.description[lang] ?? meta.description.de;
}

export function getLatestUpdate(meta: TopicMeta): string | null {
  const dates = Object.values(meta.layers)
    .map((l) => l.updated)
    .filter((d): d is string => d !== null);
  if (dates.length === 0) return null;
  return dates.sort().reverse()[0];
}

export function getAllTags(metas: TopicMeta[]): string[] {
  const tagSet = new Set<string>();
  for (const meta of metas) {
    for (const tag of meta.tags) {
      tagSet.add(tag);
    }
  }
  return [...tagSet].sort();
}

export function formatDate(dateStr: string, lang: Lang): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString(lang === 'de' ? 'de-CH' : 'en-GB', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
