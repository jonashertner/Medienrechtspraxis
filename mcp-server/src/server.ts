/**
 * Medienrechtspraxis MCP Server
 *
 * Exposes Swiss media law content to LLMs via the Model Context Protocol.
 * Supports Streamable HTTP transport.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import express from 'express';
import { z } from 'zod';
import { ContentStore } from './lib/content_loader.js';

const PORT = parseInt(process.env.PORT ?? '3001', 10);

// Load content
const store = new ContentStore(process.env.CONTENT_DIR);
store.load();

// Create MCP server
const server = new McpServer({
  name: 'medienrechtspraxis',
  version: '0.1.0',
});

// ── Tools ──────────────────────────────────────────────────────────────────

server.tool(
  'search_topics',
  'Full-text search across all media law topic chapters',
  {
    query: z.string().describe('Search query'),
    lang: z.enum(['de', 'en']).default('de').describe('Language'),
    tags: z.array(z.string()).optional().describe('Filter by tags'),
  },
  async ({ query, lang, tags }) => {
    const results = store.searchTopics(query, lang, tags);
    const summaries = results.map((t) => ({
      slug: t.meta.slug,
      title: t.meta.title[lang as 'de' | 'en'],
      description: t.meta.description[lang as 'de' | 'en'],
      tags: t.meta.tags,
      has_summary: !!t.summary[lang as 'de' | 'en'],
      has_doctrine: !!t.doctrine[lang as 'de' | 'en'],
      has_caselaw: !!t.caselaw[lang as 'de' | 'en'],
    }));

    return {
      content: [{ type: 'text' as const, text: JSON.stringify(summaries, null, 2) }],
    };
  }
);

server.tool(
  'get_topic',
  'Get the full content of a specific topic layer',
  {
    topic_slug: z.string().describe('Topic slug (e.g., "persoenlichkeitsschutz")'),
    layer: z.enum(['summary', 'doctrine', 'caselaw']).describe('Content layer'),
    lang: z.enum(['de', 'en']).default('de').describe('Language'),
  },
  async ({ topic_slug, layer, lang }) => {
    const topic = store.getTopic(topic_slug);
    if (!topic) {
      return {
        content: [{ type: 'text' as const, text: `Topic not found: ${topic_slug}` }],
        isError: true,
      };
    }

    const content = topic[layer as keyof typeof topic] as { de: string | null; en: string | null };
    const text = content?.[lang as 'de' | 'en'];

    if (!text) {
      return {
        content: [{
          type: 'text' as const,
          text: `No ${layer} content available for "${topic_slug}" in ${lang}`,
        }],
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: `# ${topic.meta.title[lang as 'de' | 'en']} — ${layer}\n\n${text}`,
      }],
    };
  }
);

server.tool(
  'search_caselaw',
  'Search case law digests across all topics',
  {
    query: z.string().describe('Search query'),
    court: z.string().optional().describe('Filter by court (e.g., "BGer", "EGMR")'),
    date_from: z.string().optional().describe('Filter from date (YYYY-MM-DD)'),
    date_to: z.string().optional().describe('Filter to date (YYYY-MM-DD)'),
  },
  async ({ query, court, date_from, date_to }) => {
    const results = store.searchCaselaw(query, court, date_from, date_to);
    return {
      content: [{
        type: 'text' as const,
        text: results.length > 0
          ? results.map((r) => `## ${r.slug}\n\n${r.content}`).join('\n\n---\n\n')
          : 'No matching case law found.',
      }],
    };
  }
);

server.tool(
  'get_recent_updates',
  'Get the most recent content updates',
  {
    limit: z.number().min(1).max(50).default(10).describe('Number of updates to return'),
    lang: z.enum(['de', 'en']).default('de').describe('Language'),
  },
  async ({ limit, lang }) => {
    const updates = store.getRecentUpdates(limit, lang);
    return {
      content: [{ type: 'text' as const, text: JSON.stringify(updates, null, 2) }],
    };
  }
);

server.tool(
  'check_publication_risk',
  'Given a publication scenario, return relevant legal topics and key rules. Does NOT give legal advice.',
  {
    scenario_description: z.string().describe('Free-text description of the publication scenario'),
    lang: z.enum(['de', 'en']).default('de').describe('Language'),
  },
  async ({ scenario_description, lang }) => {
    // Match scenario against topic tags and content
    const langKey = lang as 'de' | 'en';
    const keywords = scenario_description.toLowerCase().split(/\s+/);
    const allTopics = store.getAllTopics();

    const scored = allTopics.map((topic) => {
      let score = 0;
      const searchText = [
        topic.meta.title[langKey],
        topic.meta.description[langKey],
        ...topic.meta.tags,
        topic.summary[langKey] ?? '',
      ].join(' ').toLowerCase();

      for (const kw of keywords) {
        if (kw.length > 2 && searchText.includes(kw)) score++;
      }

      return { topic, score };
    });

    const relevant = scored
      .filter((s) => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    if (relevant.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: lang === 'de'
            ? 'Keine direkt zutreffenden Themen gefunden. Bitte präzisieren Sie das Szenario.'
            : 'No directly matching topics found. Please provide more detail about the scenario.',
        }],
      };
    }

    const sections = relevant.map(({ topic }) => {
      const summary = topic.summary[langKey];
      return [
        `## ${topic.meta.title[langKey]}`,
        topic.meta.description[langKey],
        '',
        summary ? summary.slice(0, 500) + (summary.length > 500 ? '…' : '') : '(Content pending)',
        '',
        `Related: ${topic.meta.related_articles.map((r) => `${r.law} Art. ${r.articles.join(', ')}`).join('; ')}`,
        `Tags: ${topic.meta.tags.join(', ')}`,
      ].join('\n');
    });

    const disclaimer = lang === 'de'
      ? '\n\n---\n⚠️ Dies ist keine Rechtsberatung. Konsultieren Sie eine Fachperson.'
      : '\n\n---\n⚠️ This is not legal advice. Consult a qualified professional.';

    return {
      content: [{
        type: 'text' as const,
        text: sections.join('\n\n---\n\n') + disclaimer,
      }],
    };
  }
);

server.tool(
  'get_dach_comparison',
  'Get CH/DE/AT comparison for a topic',
  {
    topic_slug: z.string().describe('Topic slug'),
    lang: z.enum(['de', 'en']).default('de').describe('Language'),
  },
  async ({ topic_slug, lang }) => {
    const topic = store.getTopic(topic_slug);
    if (!topic) {
      return {
        content: [{ type: 'text' as const, text: `Topic not found: ${topic_slug}` }],
        isError: true,
      };
    }

    const langKey = lang as 'de' | 'en';
    const refs = topic.meta.dach_references;
    const sections: string[] = [
      `# ${topic.meta.title[langKey]} — DACH Comparison`,
      '',
      `## CH (Switzerland)`,
      topic.meta.related_articles.map((r) => `- ${r.law}: Art. ${r.articles.join(', ')}`).join('\n'),
    ];

    for (const ref of refs) {
      sections.push('', `## ${ref.jurisdiction === 'DE' ? 'DE (Germany)' : 'AT (Austria)'}`, ref.laws.map((l) => `- ${l}`).join('\n'));
    }

    // Include DACH section from doctrine if available
    const doctrine = topic.doctrine[langKey];
    if (doctrine) {
      const dachMatch = doctrine.match(/##.*(?:DACH|Rechtsvergleich|Comparison)[\s\S]*?(?=\n## |\n# |$)/i);
      if (dachMatch) {
        sections.push('', '---', '', dachMatch[0].trim());
      }
    }

    return {
      content: [{ type: 'text' as const, text: sections.join('\n') }],
    };
  }
);

// ── HTTP Server ────────────────────────────────────────────────────────────

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', topics: store.getAllTopics().length });
});

// MCP endpoint (Streamable HTTP)
app.all('/', async (req, res) => {
  try {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error('MCP request error:', err);
    if (!res.headersSent) {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

app.listen(PORT, () => {
  console.log(`Medienrechtspraxis MCP server running on port ${PORT}`);
});
