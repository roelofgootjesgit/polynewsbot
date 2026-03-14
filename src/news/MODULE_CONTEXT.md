# News Ingestion — MODULE_CONTEXT

## Wat
Nieuws ophalen uit meerdere bronnen en normaliseren naar NormalizedNewsEvent.

## Te bouwen (Fase 2)
- `base.py` — ABC NewsSource met fetch() → list[RawNewsItem]
- `rss.py` — RSS feed source (feedparser)
- `newsapi.py` — NewsAPI source
- `polymarket_feed.py` — Polymarket activity/comment feed
- `normalizer.py` — RawNewsItem → NormalizedNewsEvent (source tier, reliability, dedup)

## Interfaces
- **Input:** externe bronnen (RSS, API's)
- **Output:** list[NormalizedNewsEvent] → gaat naar filter module

## Config sectie: `news.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 2
