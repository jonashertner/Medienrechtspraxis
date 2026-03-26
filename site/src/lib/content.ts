/**
 * Content loader: reads topic content from the content/ directory.
 * Uses gray-matter for YAML parsing.
 */

import fs from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';

const CONTENT_DIR = path.resolve(process.cwd(), '..', 'content');

export interface TopicMeta {
  title: { de: string; en: string };
  slug: string;
  description: { de: string; en: string };
  related_articles: { law: string; articles: string[] }[];
  dach_references: { jurisdiction: string; laws: string[] }[];
  layers: {
    summary: { status: string; updated: string | null };
    doctrine: { status: string; updated: string | null };
    caselaw: { status: string; updated: string | null };
  };
  tags: string[];
  sort_order: number;
}

export interface TopicContent {
  meta: TopicMeta;
  summary: { de: string | null; en: string | null };
  doctrine: { de: string | null; en: string | null };
  caselaw: { de: string | null; en: string | null };
}

function readFileOrNull(filePath: string): string | null {
  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return null;
  }
}

function parseYamlFile(filePath: string): Record<string, any> {
  const raw = fs.readFileSync(filePath, 'utf-8');
  // Wrap in front-matter delimiters so gray-matter can parse it
  const wrapped = `---\n${raw}\n---`;
  return matter(wrapped).data;
}

export function getTopicSlugs(): string[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];
  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .filter((d) => fs.existsSync(path.join(CONTENT_DIR, d.name, 'meta.yaml')))
    .map((d) => d.name);
}

export function getTopicMeta(slug: string): TopicMeta | null {
  const metaPath = path.join(CONTENT_DIR, slug, 'meta.yaml');
  if (!fs.existsSync(metaPath)) return null;
  return parseYamlFile(metaPath) as unknown as TopicMeta;
}

export function getTopicContent(slug: string): TopicContent | null {
  const meta = getTopicMeta(slug);
  if (!meta) return null;

  const dir = path.join(CONTENT_DIR, slug);

  return {
    meta,
    summary: {
      de: readFileOrNull(path.join(dir, 'summary.md')),
      en: readFileOrNull(path.join(dir, 'summary.en.md')),
    },
    doctrine: {
      de: readFileOrNull(path.join(dir, 'doctrine.md')),
      en: readFileOrNull(path.join(dir, 'doctrine.en.md')),
    },
    caselaw: {
      de: readFileOrNull(path.join(dir, 'caselaw.md')),
      en: readFileOrNull(path.join(dir, 'caselaw.en.md')),
    },
  };
}

export function getAllTopics(): TopicContent[] {
  return getTopicSlugs()
    .map(getTopicContent)
    .filter((t): t is TopicContent => t !== null)
    .sort((a, b) => a.meta.sort_order - b.meta.sort_order);
}

export function getRecentUpdates(limit = 10): { slug: string; layer: string; date: string; title: string }[] {
  const updates: { slug: string; layer: string; date: string; title: string }[] = [];

  for (const slug of getTopicSlugs()) {
    const meta = getTopicMeta(slug);
    if (!meta) continue;

    for (const [layer, info] of Object.entries(meta.layers)) {
      if (info.updated) {
        updates.push({
          slug,
          layer,
          date: info.updated,
          title: meta.title.de,
        });
      }
    }
  }

  return updates
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, limit);
}
