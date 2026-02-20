"""News aggregation service using yfinance."""

import math
from datetime import datetime
import yfinance as yf


def _fetch_summary(url, max_chars=400):
    """Fetch a URL and extract a short summary (first meaningful paragraphs)."""
    try:
        import urllib.request
        import html
        import re

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; StockAlpha/1.0)'},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            content = resp.read().decode('utf-8', errors='replace')

        # Remove scripts and styles
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)

        # Extract <p> text
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, flags=re.DOTALL | re.IGNORECASE)
        clean = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p)
            text = html.unescape(text).strip()
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


def get_news(tickers, max_articles=15):
    """Fetch and aggregate news articles for a list of tickers.

    Args:
        tickers: list of ticker symbols
        max_articles: maximum total articles to return (sorted by date desc)

    Returns:
        list of article dicts
    """
    seen_urls = set()
    articles = []

    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            news_items = t.news or []
            for item in news_items:
                parsed = _parse_news_item(item, symbol)
                url = parsed.get('url', '')
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                articles.append(parsed)
        except Exception:
            continue

    # Sort by publish timestamp descending, take top N
    articles.sort(key=lambda a: a['pub_ts'], reverse=True)
    articles = articles[:max_articles]

    # Fetch summaries for articles that don't already have one (from yfinance)
    for art in articles:
        if not art.get('summary') and art.get('url'):
            art['summary'] = _fetch_summary(art['url'])

    # Remove internal timestamp field
    for art in articles:
        art.pop('pub_ts', None)

    return articles
