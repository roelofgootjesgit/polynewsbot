# News Ingestion — MODULE_CONTEXT

## Wat
Nieuws ophalen uit meerdere bronnen en normaliseren naar NormalizedNewsEvent.

## Bestanden
- `base.py` — ABC NewsSource (fetch() → list[RawNewsItem])
- `rss.py` — RSSSource (feedparser), create_rss_sources(cfg)
- `newsapi_source.py` — NewsAPISource (httpx), create_newsapi_source(cfg)
- `normalizer.py` — NewsNormalizer: reliability scoring, topic extraction, dedup
- `poller.py` — NewsPoller: orchestreert alle sources, geeft nieuwe events

## NewsPoller flow
1. `setup()` — init alle sources uit config
2. `poll()` — fetch alle sources → normalize → dedup → return nieuwe events

## Deduplicatie
- MD5 hash op lowercase headline
- OrderedDict cache (max 5000 items, FIFO eviction)
- Duplicaten worden gemarkeerd (is_duplicate=True) maar niet verwijderd

## Topic extraction
Keywords per categorie: crypto, politics, economics, central_banks, regulation, geopolitics

## Config sectie: `news.*` in default.yaml

## Status
- [x] base.py — ABC interface
- [x] rss.py — RSS feed source
- [x] newsapi_source.py — NewsAPI source
- [x] normalizer.py — normalisatie + dedup + topics
- [x] poller.py — orchestratie
- [x] Unit tests (12 passing)
- [x] Integration tests (2 passing — live RSS feeds)
