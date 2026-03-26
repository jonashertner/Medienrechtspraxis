#!/usr/bin/env python3
"""Generate meta.yaml for all topics. Run once during initial setup."""

from pathlib import Path

import yaml

TOPICS = [
    {
        "slug": "gegendarstellung",
        "title": {"de": "Gegendarstellung", "en": "Right of Reply"},
        "description": {
            "de": "Recht auf Gegendarstellung in periodischen Medien",
            "en": "Right of reply in periodical media",
        },
        "related_articles": [
            {"law": "ZGB", "articles": ["28g", "28h", "28i", "28k", "28l"]},
            {"law": "EMRK", "articles": ["10"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["LPresseG §11"]},
            {"jurisdiction": "AT", "laws": ["MedienG §9-13"]},
        ],
        "tags": ["right-of-reply", "media", "correction"],
        "sort_order": 2,
    },
    {
        "slug": "quellenschutz",
        "title": {"de": "Quellenschutz", "en": "Protection of Journalistic Sources"},
        "description": {
            "de": "Schutz journalistischer Quellen und Redaktionsgeheimnis",
            "en": "Protection of journalistic sources and editorial secrecy",
        },
        "related_articles": [
            {"law": "BV", "articles": ["17"]},
            {"law": "StPO", "articles": ["172"]},
            {"law": "EMRK", "articles": ["10"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["StPO §53 Abs.1 Nr.5", "GG Art.5"]},
            {"jurisdiction": "AT", "laws": ["MedienG §31"]},
        ],
        "tags": ["source-protection", "journalist-privilege", "editorial-secrecy"],
        "sort_order": 3,
    },
    {
        "slug": "ehrverletzung",
        "title": {"de": "Ehrverletzung", "en": "Defamation"},
        "description": {
            "de": "Strafrechtlicher Ehrschutz: üble Nachrede, Verleumdung, Beschimpfung",
            "en": "Criminal defamation: slander, libel, insult",
        },
        "related_articles": [
            {"law": "StGB", "articles": ["173", "174", "175", "176", "177"]},
            {"law": "ZGB", "articles": ["28"]},
            {"law": "EMRK", "articles": ["10"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["StGB §185-187", "StGB §193"]},
            {"jurisdiction": "AT", "laws": ["StGB §111-113", "MedienG §6"]},
        ],
        "tags": ["defamation", "criminal-law", "honor-protection"],
        "sort_order": 4,
    },
    {
        "slug": "bildnisschutz",
        "title": {"de": "Bildnisschutz / Recht am eigenen Bild", "en": "Right to One's Own Image"},
        "description": {
            "de": "Schutz gegen unerlaubte Bildaufnahmen und -veröffentlichungen",
            "en": "Protection against unauthorized image capture and publication",
        },
        "related_articles": [
            {"law": "ZGB", "articles": ["28"]},
            {"law": "URG", "articles": ["2", "36"]},
            {"law": "EMRK", "articles": ["8"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["KUG §22-23"]},
            {"jurisdiction": "AT", "laws": ["UrhG §78"]},
        ],
        "tags": ["image-rights", "photography", "privacy"],
        "sort_order": 5,
    },
    {
        "slug": "pressefreiheit",
        "title": {"de": "Pressefreiheit", "en": "Freedom of the Press"},
        "description": {
            "de": "Verfassungsrechtlicher Rahmen der Medienfreiheit in der Schweiz",
            "en": "Constitutional framework of media freedom in Switzerland",
        },
        "related_articles": [
            {"law": "BV", "articles": ["16", "17"]},
            {"law": "EMRK", "articles": ["10"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["GG Art.5"]},
            {"jurisdiction": "AT", "laws": ["StGG Art.13", "EMRK Art.10"]},
        ],
        "tags": ["press-freedom", "constitutional-law", "media-freedom"],
        "sort_order": 6,
    },
    {
        "slug": "datenschutz-medien",
        "title": {"de": "Datenschutz & Medien", "en": "Data Protection & Media"},
        "description": {
            "de": "Datenschutzrechtliches Medienprivileg und Spannungsfeld DSG/DSGVO",
            "en": "Media privilege in data protection law and DSG/GDPR tensions",
        },
        "related_articles": [
            {"law": "DSG", "articles": ["27"]},
            {"law": "BV", "articles": ["13"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["DSGVO Art.85", "BDSG §23"]},
            {"jurisdiction": "AT", "laws": ["DSG §9"]},
        ],
        "tags": ["data-protection", "media-privilege", "gdpr"],
        "sort_order": 7,
    },
    {
        "slug": "online-medien",
        "title": {"de": "Online-Medien & Plattformhaftung", "en": "Online Media & Platform Liability"},
        "description": {
            "de": "Haftung für Online-Inhalte, DSA, Social-Media-Recht",
            "en": "Liability for online content, DSA, social media law",
        },
        "related_articles": [
            {"law": "ZGB", "articles": ["28"]},
            {"law": "OR", "articles": ["41"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["TMG §7-10", "NetzDG"]},
            {"jurisdiction": "AT", "laws": ["ECG §13-19", "KoPl-G"]},
        ],
        "tags": ["online-media", "platform-liability", "social-media", "dsa"],
        "sort_order": 8,
    },
    {
        "slug": "urheberrecht-medien",
        "title": {"de": "Urheberrecht & Medien", "en": "Copyright & Media"},
        "description": {
            "de": "Medienrelevantes Urheberrecht: Zitatrecht, Embedding, KI-generierte Inhalte",
            "en": "Media-relevant copyright: quotation right, embedding, AI-generated content",
        },
        "related_articles": [
            {"law": "URG", "articles": ["2", "10", "19", "25", "28"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["UrhG §51", "UrhG §57"]},
            {"jurisdiction": "AT", "laws": ["UrhG §42f", "UrhG §46"]},
        ],
        "tags": ["copyright", "quotation-right", "embedding", "ai-content"],
        "sort_order": 9,
    },
    {
        "slug": "lauterkeitsrecht-medien",
        "title": {"de": "Lauterkeitsrecht & Medien", "en": "Unfair Competition & Media"},
        "description": {
            "de": "Medienrelevante Bestimmungen des UWG",
            "en": "Media-relevant provisions of unfair competition law",
        },
        "related_articles": [
            {"law": "UWG", "articles": ["3", "23"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["UWG §3-7"]},
            {"jurisdiction": "AT", "laws": ["UWG §1-2"]},
        ],
        "tags": ["unfair-competition", "advertising", "media"],
        "sort_order": 10,
    },
    {
        "slug": "rundfunkrecht",
        "title": {"de": "Rundfunkrecht", "en": "Broadcasting Law"},
        "description": {
            "de": "RTVG, SRG-Konzession, UBI-Praxis",
            "en": "Broadcasting regulation, SRG concession, UBI practice",
        },
        "related_articles": [
            {"law": "BV", "articles": ["93"]},
            {"law": "RTVG", "articles": ["4", "5", "6", "83", "86", "94"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["MStV", "RStV"]},
            {"jurisdiction": "AT", "laws": ["ORF-G", "AMD-G"]},
        ],
        "tags": ["broadcasting", "rtvg", "ubi", "srg"],
        "sort_order": 11,
    },
    {
        "slug": "werbung-sponsoring",
        "title": {"de": "Werbung & Sponsoring", "en": "Advertising & Sponsoring"},
        "description": {
            "de": "Werberecht in Medien, Influencer-Recht, Sponsoring-Regulierung",
            "en": "Advertising law in media, influencer law, sponsoring regulation",
        },
        "related_articles": [
            {"law": "RTVG", "articles": ["9", "10", "11", "12", "13"]},
            {"law": "UWG", "articles": ["3"]},
        ],
        "dach_references": [
            {"jurisdiction": "DE", "laws": ["RStV §7-8", "UWG §5a"]},
            {"jurisdiction": "AT", "laws": ["AMD-G §37-42", "MedienG §26"]},
        ],
        "tags": ["advertising", "sponsoring", "influencer-law"],
        "sort_order": 12,
    },
]


def main() -> None:
    content_dir = Path("content")
    for topic in TOPICS:
        slug = topic["slug"]
        topic_dir = content_dir / slug
        topic_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "title": topic["title"],
            "slug": slug,
            "description": topic["description"],
            "related_articles": topic["related_articles"],
            "dach_references": topic["dach_references"],
            "layers": {
                "summary": {"status": "draft", "updated": None},
                "doctrine": {"status": "draft", "updated": None},
                "caselaw": {"status": "draft", "updated": None},
            },
            "tags": topic["tags"],
            "sort_order": topic["sort_order"],
        }

        meta_path = topic_dir / "meta.yaml"
        with open(meta_path, "w") as f:
            yaml.dump(meta, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"  ✓ {slug}/meta.yaml")

    print(f"\nGenerated {len(TOPICS)} topic meta.yaml files.")


if __name__ == "__main__":
    main()
