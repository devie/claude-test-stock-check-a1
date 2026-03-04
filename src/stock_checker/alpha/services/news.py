"""News aggregation service using yfinance."""

import email.utils
import re as _re
import html as _html
import urllib.request as _urllib_request
from datetime import datetime
from urllib.parse import urlparse as _urlparse
import yfinance as yf


_ALLOWED_DOMAINS = {
    'finance.yahoo.com', 'www.yahoo.com', 'news.yahoo.com',
    'reuters.com', 'www.reuters.com',
    'bloomberg.com', 'www.bloomberg.com',
    'cnbc.com', 'www.cnbc.com',
    'marketwatch.com', 'www.marketwatch.com',
    'wsj.com', 'www.wsj.com',
    'ft.com', 'www.ft.com',
    'seekingalpha.com', 'www.seekingalpha.com',
    'investopedia.com', 'www.investopedia.com',
    'barrons.com', 'www.barrons.com',
    'kontan.co.id', 'www.kontan.co.id',
    'bisnis.com', 'www.bisnis.com',
    'cnbcindonesia.com', 'www.cnbcindonesia.com',
    'detik.com', 'finance.detik.com',
    'idx.co.id', 'www.idx.co.id',
}


def _fetch_summary(url, max_chars=400):
    """Fetch a URL and extract a short summary (first meaningful paragraphs)."""
    try:
        parsed = _urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return None
        if parsed.hostname and parsed.hostname not in _ALLOWED_DOMAINS:
            return None

        req = _urllib_request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; StockAlpha/1.0)'},
        )
        with _urllib_request.urlopen(req, timeout=4) as resp:
            content = resp.read().decode('utf-8', errors='replace')

        # Remove scripts and styles
        content = _re.sub(r'<script[^>]*>.*?</script>', '', content, flags=_re.DOTALL | _re.IGNORECASE)
        content = _re.sub(r'<style[^>]*>.*?</style>', '', content, flags=_re.DOTALL | _re.IGNORECASE)

        # Extract <p> text
        paragraphs = _re.findall(r'<p[^>]*>(.*?)</p>', content, flags=_re.DOTALL | _re.IGNORECASE)
        clean = []
        for p in paragraphs:
            text = _re.sub(r'<[^>]+>', '', p)
            text = _html.unescape(text).strip()
            # Skip boilerplate (too short or looks like a nav/button label)
            if len(text) > 60 and not text.lower().startswith(('cookie', 'subscribe', 'sign in', 'log in', 'click')):
                clean.append(text)
            if len(clean) >= 2:
                break

        if clean:
            summary = ' '.join(clean)[:max_chars]
            if len(summary) >= max_chars:
                summary = summary[:max_chars].rsplit(' ', 1)[0] + '...'
            return summary
    except Exception:
        pass
    return None


def _parse_news_item(item, symbol):
    """Parse a yfinance news item (handles old and new formats)."""
    # New format: item has 'content' dict
    content = item.get('content') if isinstance(item.get('content'), dict) else None
    if content:
        url_data = content.get('canonicalUrl') or content.get('clickThroughUrl') or {}
        url = url_data.get('url') or ''
        title = content.get('title', '')
        provider = content.get('provider') or {}
        publisher = provider.get('displayName') if isinstance(provider, dict) else str(provider)
        # pubDate: "2026-02-19T19:17:11Z"
        pub_date_str = content.get('pubDate') or content.get('displayTime') or ''
        try:
            pub_ts = datetime.strptime(pub_date_str[:19], '%Y-%m-%dT%H:%M:%S').timestamp()
            pub_date = pub_date_str[:10]
        except Exception:
            pub_ts = 0
            pub_date = ''
        # Thumbnail: pick smallest resolution for fast load
        thumb = None
        thumb_data = content.get('thumbnail') or {}
        resolutions = thumb_data.get('resolutions') or []
        if resolutions:
            # Pick 170px or smallest
            small = sorted(resolutions, key=lambda r: r.get('width', 9999))
            thumb = small[0].get('url') if small else None
        elif thumb_data.get('originalUrl'):
            thumb = thumb_data['originalUrl']
        # Use yfinance summary if available
        summary = content.get('summary') or None
        return {
            'ticker': symbol,
            'title': title,
            'publisher': publisher or '',
            'url': url,
            'pub_date': pub_date,
            'pub_ts': pub_ts,
            'thumbnail': thumb,
            'summary': summary,
        }
    else:
        # Old format
        url = item.get('link') or item.get('url') or ''
        ts = item.get('providerPublishTime') or 0
        try:
            pub_date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        except Exception:
            pub_date = ''
        thumb = None
        thumb_data = item.get('thumbnail') or {}
        resolutions = thumb_data.get('resolutions') or []
        if resolutions:
            thumb = resolutions[0].get('url')
        return {
            'ticker': symbol,
            'title': item.get('title', ''),
            'publisher': item.get('publisher', ''),
            'url': url,
            'pub_date': pub_date,
            'pub_ts': ts,
            'thumbnail': thumb,
            'summary': None,
        }


def _fetch_rss_news(symbol, max_items=5):
    """Fallback: fetch news via Yahoo Finance RSS for tickers that return nothing from yfinance."""
    url = f'https://finance.yahoo.com/rss/headline?s={symbol}'
    try:
        req = _urllib_request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StockAlpha/1.0)'})
        with _urllib_request.urlopen(req, timeout=6) as resp:
            content = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return []

    result = []
    for item_xml in _re.findall(r'<item>(.*?)</item>', content, _re.DOTALL)[:max_items]:
        title_m = _re.search(r'<title>(.*?)</title>', item_xml, _re.DOTALL)
        link_m = _re.search(r'<link>(.*?)</link>', item_xml, _re.DOTALL)
        desc_m = _re.search(r'<description>(.*?)</description>', item_xml, _re.DOTALL)
        date_m = _re.search(r'<pubDate>(.*?)</pubDate>', item_xml, _re.DOTALL)

        title = _html.unescape((title_m.group(1) or '').strip()) if title_m else ''
        link = (link_m.group(1) or '').strip().split('?')[0] if link_m else ''
        desc_raw = (desc_m.group(1) or '').strip() if desc_m else ''
        desc = _html.unescape(_re.sub(r'<[^>]+>', '', desc_raw)).strip()
        pub_date_str = (date_m.group(1) or '').strip() if date_m else ''

        try:
            dt = email.utils.parsedate_to_datetime(pub_date_str)
            pub_ts = dt.timestamp()
            pub_date = dt.strftime('%Y-%m-%d')
        except Exception:
            pub_ts = 0
            pub_date = ''

        parsed_link = _urlparse(link)
        if parsed_link.hostname and parsed_link.hostname not in _ALLOWED_DOMAINS:
            continue
        if not title or not link:
            continue

        result.append({
            'ticker': symbol,
            'title': title,
            'publisher': 'Yahoo Finance',
            'url': link,
            'pub_date': pub_date,
            'pub_ts': pub_ts,
            'thumbnail': None,
            'summary': desc or None,
        })

    return result


def get_news(tickers, max_articles=5, max_per_ticker=1, days=7):
    """Fetch and aggregate news articles for a list of tickers.

    Rules:
    - Only articles published within the last `days` days (default 7).
    - Max `max_per_ticker` articles per ticker (default 2), chosen by
      cross-ticker relevance first (articles that appear in multiple tickers'
      feeds score higher) then by recency.
    - Final list sorted by recency, capped at `max_articles`.

    Args:
        tickers: list of ticker symbols
        max_articles: maximum total articles to return
        max_per_ticker: max articles kept per ticker before global dedup
        days: lookback window in days

    Returns:
        list of article dicts
    """
    cutoff_ts = datetime.utcnow().timestamp() - days * 86400

    # Pass 1 — collect all articles per ticker within the window
    by_ticker: dict[str, list[dict]] = {}
    url_ticker_count: dict[str, int] = {}  # how many tickers share this URL

    # Fallback cutoff: 90 days (for tickers with sparse news like emerging-market stocks)
    fallback_cutoff_ts = datetime.utcnow().timestamp() - 90 * 86400

    for symbol in tickers:
        ticker_articles = []
        try:
            t = yf.Ticker(symbol)
            news_items = t.news or []
            for item in news_items:
                parsed = _parse_news_item(item, symbol)
                url = parsed.get('url', '')
                ts  = parsed.get('pub_ts', 0)
                if not url or ts < cutoff_ts:
                    continue
                ticker_articles.append(parsed)
                url_ticker_count[url] = url_ticker_count.get(url, 0) + 1
        except Exception:
            pass

        # RSS fallback when yfinance returns nothing for this ticker
        if not ticker_articles:
            for parsed in _fetch_rss_news(symbol):
                url = parsed.get('url', '')
                ts = parsed.get('pub_ts', 0)
                if not url or ts < fallback_cutoff_ts:
                    continue
                ticker_articles.append(parsed)
                url_ticker_count[url] = url_ticker_count.get(url, 0) + 1

        by_ticker[symbol] = ticker_articles

    # Pass 2 — per ticker: rank by (cross-ticker count desc, recency desc), keep top N
    seen_urls: set[str] = set()
    selected: list[dict] = []

    for symbol in tickers:
        candidates = by_ticker.get(symbol, [])
        # Score: primary = number of tickers sharing this URL (trending signal)
        #        secondary = publish timestamp (recency)
        candidates.sort(
            key=lambda a: (url_ticker_count.get(a['url'], 1), a['pub_ts']),
            reverse=True,
        )
        added = 0
        for art in candidates:
            url = art['url']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            selected.append(art)
            added += 1
            if added >= max_per_ticker:
                break

    # Pass 3 — sort all selected by recency, cap, fetch summaries
    selected.sort(key=lambda a: a['pub_ts'], reverse=True)
    selected = selected[:max_articles]

    for art in selected:
        if not art.get('summary') and art.get('url'):
            art['summary'] = _fetch_summary(art['url'])

    for art in selected:
        art.pop('pub_ts', None)

    return selected
