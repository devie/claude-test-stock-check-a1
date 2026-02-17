"""Database models for the Alpha module."""

from datetime import datetime, timezone
from stock_checker.alpha.models.database import db


class Watchlist(db.Model):
    __tablename__ = "watchlist"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    items = db.relationship("WatchlistItem", backref="watchlist",
                            cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "items": [i.to_dict() for i in self.items],
        }


class WatchlistItem(db.Model):
    __tablename__ = "watchlist_item"
    id = db.Column(db.Integer, primary_key=True)
    watchlist_id = db.Column(db.Integer, db.ForeignKey("watchlist.id"), nullable=False)
    ticker = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), default="")
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "category": self.category,
            "added_at": self.added_at.isoformat(),
        }


class AnalysisNote(db.Model):
    __tablename__ = "analysis_note"
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default="")
    tags = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "title": self.title,
            "content": self.content,
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RatioSnapshot(db.Model):
    __tablename__ = "ratio_snapshot"
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    snapshot_date = db.Column(db.Date, nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "ticker": self.ticker,
            "snapshot_date": self.snapshot_date.isoformat(),
            "data": json.loads(self.data_json),
            "created_at": self.created_at.isoformat(),
        }


class ValuationResult(db.Model):
    __tablename__ = "valuation_result"
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    model_type = db.Column(db.String(20), nullable=False)
    assumptions_json = db.Column(db.Text, nullable=False)
    results_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "ticker": self.ticker,
            "model_type": self.model_type,
            "assumptions": json.loads(self.assumptions_json),
            "results": json.loads(self.results_json),
            "created_at": self.created_at.isoformat(),
        }


class ComparisonSession(db.Model):
    __tablename__ = "comparison_session"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), default="")
    tickers_json = db.Column(db.Text, nullable=False)
    results_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "name": self.name,
            "tickers": json.loads(self.tickers_json),
            "results": json.loads(self.results_json),
            "created_at": self.created_at.isoformat(),
        }
