"""Watchlist, notes, and snapshot CRUD service."""

import json
from datetime import date, datetime, timezone
from stock_checker.alpha.models.database import db
from stock_checker.alpha.models.schemas import (
    Watchlist, WatchlistItem, AnalysisNote, RatioSnapshot, ValuationResult
)


# --- Watchlists ---

def list_watchlists():
    return [w.to_dict() for w in Watchlist.query.order_by(Watchlist.updated_at.desc()).all()]


def create_watchlist(name, description=""):
    w = Watchlist(name=name, description=description)
    db.session.add(w)
    db.session.commit()
    return w.to_dict()


def get_watchlist(wid):
    w = Watchlist.query.get_or_404(wid)
    return w.to_dict()


def update_watchlist(wid, name=None, description=None):
    w = Watchlist.query.get_or_404(wid)
    if name is not None:
        w.name = name
    if description is not None:
        w.description = description
    w.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return w.to_dict()


def delete_watchlist(wid):
    w = Watchlist.query.get_or_404(wid)
    db.session.delete(w)
    db.session.commit()


def add_watchlist_item(wid, ticker, category=""):
    w = Watchlist.query.get_or_404(wid)
    item = WatchlistItem(watchlist_id=w.id, ticker=ticker.upper(), category=category)
    db.session.add(item)
    w.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return item.to_dict()


def remove_watchlist_item(wid, ticker):
    item = WatchlistItem.query.filter_by(watchlist_id=wid, ticker=ticker.upper()).first_or_404()
    db.session.delete(item)
    db.session.commit()


# --- Notes ---

def list_notes(ticker=None):
    q = AnalysisNote.query.order_by(AnalysisNote.updated_at.desc())
    if ticker:
        q = q.filter_by(ticker=ticker.upper())
    return [n.to_dict() for n in q.all()]


def create_note(ticker, title, content="", tags=""):
    n = AnalysisNote(ticker=ticker.upper(), title=title, content=content, tags=tags)
    db.session.add(n)
    db.session.commit()
    return n.to_dict()


def update_note(nid, title=None, content=None, tags=None):
    n = AnalysisNote.query.get_or_404(nid)
    if title is not None:
        n.title = title
    if content is not None:
        n.content = content
    if tags is not None:
        n.tags = tags
    n.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return n.to_dict()


def delete_note(nid):
    n = AnalysisNote.query.get_or_404(nid)
    db.session.delete(n)
    db.session.commit()


# --- Snapshots ---

def save_snapshot(ticker, data):
    s = RatioSnapshot(
        ticker=ticker.upper(),
        snapshot_date=date.today(),
        data_json=json.dumps(data),
    )
    db.session.add(s)
    db.session.commit()
    return s.to_dict()


def list_snapshots(ticker=None):
    q = RatioSnapshot.query.order_by(RatioSnapshot.created_at.desc())
    if ticker:
        q = q.filter_by(ticker=ticker.upper())
    return [s.to_dict() for s in q.all()]


# --- Valuations ---

def save_valuation(ticker, model_type, assumptions, results):
    v = ValuationResult(
        ticker=ticker.upper(),
        model_type=model_type,
        assumptions_json=json.dumps(assumptions),
        results_json=json.dumps(results),
    )
    db.session.add(v)
    db.session.commit()
    return v.to_dict()


def list_valuations(ticker=None):
    q = ValuationResult.query.order_by(ValuationResult.created_at.desc())
    if ticker:
        q = q.filter_by(ticker=ticker.upper())
    return [v.to_dict() for v in q.all()]
