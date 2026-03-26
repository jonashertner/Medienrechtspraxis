/**
 * Content loader for the MCP server.
 * Reads the content/ directory structure at startup and caches in memory.
 */

import fs from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';

export interface TopicMeta {
  title: { de: string; en: string };
  slug: string;
  description: { de: string; en: string };
  related_articles: { law: string; articles: string[] }[];
  dach_references: { jurisdiction: string; laws: string[] }[];
  layers: Record<string, { status: string; updated: string | null }>;
  tags: string[];
  sort_order: number;
}

export interface TopicData {
  meta: TopicMeta;
  summary: { de: string | null; en: string | null };
  doctrine: { de: string | null; en: string | null };
  caselaw: { de: string | null; en: string | null };
}

export class ContentStore {
  private topics: Map<string, TopicData> = new Map();
  private contentDir: string;

  constructor(contentDir?: string) {
    this.contentDir = contentDir ?? path.resolve(process.cwd(), '..', 'content');
  }

  load(): void {
    if (!fs.existsSync(this.contentDir)) {
      console.warn(`Content directory not found: ${this.contentDir}`);
      return;
    }

    const dirs = fs.readdirSync(this.contentDir, { withFileTypes: true }).filter((d) => d.isDirectory());

    for (const dir of dirs) {
      const slug = dir.name;
      const topicDir = path.join(this.contentDir, slug);
      const metaPath = path.join(topicDir, 'meta.yaml');

      if (!fs.existsSync(metaPath)) continue;

      const raw = fs.readFileSync(metaPath, 'utf-8');
      const meta = matter(`---\n${raw}\n---`).data as unknown as TopicMeta;

      const readFile = (name: string): string | null => {
        const p = path.join(topicDir, name);
        return fs.existsSync(p) ? fs.readFileSync(p, 'utf-8') : null;
      };

      this.topics.set(slug, {
        meta,
        summary: { de: readFile('summary.md'), en: readFile('summary.en.md') },
        doctrine: { de: readFile('doctrine.md'), en: readFile('doctrine.en.md') },
        caselaw: { de: readFile('caselaw.md'), en: readFile('caselaw.en.md') },
      });
    }

    console.log(`Loaded ${this.topics.size} topics from ${this.contentDir}`);
  }

  getTopic(slug: string): TopicData | undefined {
    return this.topics.get(slug);
  }

  getAllTopics(): TopicData[] {
    return [...this.topics.values()].sort((a, b) => a.meta.sort_order - b.meta.sort_order);
  }

  searchTopics(query: string, lang: string = 'de', tags?: string[]): TopicData[] {
    const q = query.toLowerCase();
    return this.getAllTopics().filter((t) => {
      // Tag filter
      if (tags && tags.length > 0) {
        if (!tags.some((tag) => t.meta.tags.includes(tag))) return false;
      }
      // Text search across all layers
      const langKey = lang as 'de' | 'en';
      const searchText = [
        t.meta.title[langKey],
        t.meta.description[langKey],
        t.summary[langKey],
        t.doctrine[langKey],
        t.caselaw[langKey],
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return searchText.includes(q);
    });
  }

  searchCaselaw(query: string, court?: string, dateFrom?: string, dateTo?: string): { slug: string; content: string }[] {
    const q = query.toLowerCase();
    const results: { slug: string; content: string }[] = [];

    for (const [slug, topic] of this.topics) {
      const caselaw = topic.caselaw.de;
      if (!caselaw) continue;

      // Simple paragraph-level search
      const paragraphs = caselaw.split('\n\n');
      for (const para of paragraphs) {
        if (para.toLowerCase().includes(q)) {
          if (court && !para.toLowerCase().includes(court.toLowerCase())) continue;
          results.push({ slug, content: para.trim() });
        }
      }
    }

    return results;
  }

  getRecentUpdates(limit: number = 10, lang: string = 'de'): { slug: string; layer: string; date: string; title: string }[] {
    const updates: { slug: string; layer: string; date: string; title: string }[] = [];

    for (const [slug, topic] of this.topics) {
      for (const [layer, info] of Object.entries(topic.meta.layers)) {
        if (info.updated) {
          const langKey = lang as 'de' | 'en';
          updates.push({
            slug,
            layer,
            date: info.updated,
            title: topic.meta.title[langKey] ?? topic.meta.title.de,
          });
        }
      }
    }

    return updates.sort((a, b) => b.date.localeCompare(a.date)).slice(0, limit);
  }
}
