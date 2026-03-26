/**
 * Internationalisation: DE/EN string translations.
 */

export type Lang = 'de' | 'en';

const strings: Record<string, Record<Lang, string>> = {
  'site.title': {
    de: 'Medienrechtspraxis',
    en: 'Media Law Practice',
  },
  'site.subtitle': {
    de: 'Schweizer Medienrecht — KI-gestützte Rechtskommentierung',
    en: 'Swiss Media Law — AI-Powered Legal Commentary',
  },
  'nav.home': {
    de: 'Startseite',
    en: 'Home',
  },
  'nav.about': {
    de: 'Über das Projekt',
    en: 'About',
  },
  'nav.methodology': {
    de: 'Methodik',
    en: 'Methodology',
  },
  'tab.summary': {
    de: 'Praxis',
    en: 'Practice',
  },
  'tab.doctrine': {
    de: 'Doktrin',
    en: 'Doctrine',
  },
  'tab.caselaw': {
    de: 'Rechtsprechung',
    en: 'Case Law',
  },
  'home.recent': {
    de: 'Letzte Aktualisierungen',
    en: 'Recent Updates',
  },
  'home.topics': {
    de: 'Themen',
    en: 'Topics',
  },
  'topic.related': {
    de: 'Verwandte Gesetzesartikel',
    en: 'Related Statute Articles',
  },
  'topic.dach': {
    de: 'DACH-Vergleich',
    en: 'DACH Comparison',
  },
  'topic.updated': {
    de: 'Letzte Aktualisierung',
    en: 'Last Updated',
  },
  'topic.tags': {
    de: 'Schlagwörter',
    en: 'Tags',
  },
  'search.placeholder': {
    de: 'Themen durchsuchen…',
    en: 'Search topics…',
  },
  'footer.license': {
    de: 'Inhalt lizenziert unter CC-BY-SA 4.0',
    en: 'Content licensed under CC-BY-SA 4.0',
  },
  'footer.disclaimer': {
    de: 'KI-generierter Kommentar — keine Rechtsberatung',
    en: 'AI-generated commentary — not legal advice',
  },
  'content.unavailable': {
    de: 'Dieser Inhalt wird derzeit erstellt.',
    en: 'This content is currently being generated.',
  },
};

export function t(key: string, lang: Lang): string {
  return strings[key]?.[lang] ?? key;
}

export function getOtherLang(lang: Lang): Lang {
  return lang === 'de' ? 'en' : 'de';
}
