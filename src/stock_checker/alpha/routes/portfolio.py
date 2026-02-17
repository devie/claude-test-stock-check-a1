"""Portfolio API routes: watchlists, notes, snapshots, valuations."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.portfolio import (
    list_watchlists, create_watchlist, get_watchlist,
    update_watchlist, delete_watchlist,
    add_watchlist_item, remove_watchlist_item,
    list_notes, create_note, update_note, delete_note,
    save_snapshot, list_snapshots,
    save_valuation, list_valuations,
)

bp = Blueprint("alpha_portfolio", __name__)


# --- Watchlists ---

@bp.route("/api/watchlists", methods=["GET"])
def watchlists_list():
    return jsonify(list_watchlists())


@bp.route("/api/watchlists", methods=["POST"])
def watchlists_create():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    return jsonify(create_watchlist(name, data.get("description", ""))), 201


@bp.route("/api/watchlists/<int:wid>", methods=["GET"])
def watchlist_get(wid):
    return jsonify(get_watchlist(wid))


@bp.route("/api/watchlists/<int:wid>", methods=["PUT"])
def watchlist_update(wid):
    data = request.get_json()
    return jsonify(update_watchlist(wid, data.get("name"), data.get("description")))


@bp.route("/api/watchlists/<int:wid>", methods=["DELETE"])
def watchlist_delete(wid):
    delete_watchlist(wid)
    return jsonify({"ok": True})


@bp.route("/api/watchlists/<int:wid>/items", methods=["POST"])
def watchlist_add_item(wid):
    data = request.get_json()
    ticker = data.get("ticker", "").strip()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400
    return jsonify(add_watchlist_item(wid, ticker, data.get("category", ""))), 201


@bp.route("/api/watchlists/<int:wid>/items", methods=["DELETE"])
def watchlist_remove_item(wid):
    data = request.get_json()
    ticker = data.get("ticker", "").strip()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400
    remove_watchlist_item(wid, ticker)
    return jsonify({"ok": True})


# --- Notes ---

@bp.route("/api/notes", methods=["GET"])
def notes_list():
    ticker = request.args.get("ticker")
    return jsonify(list_notes(ticker))


@bp.route("/api/notes", methods=["POST"])
def notes_create():
    data = request.get_json()
    ticker = data.get("ticker", "").strip()
    title = data.get("title", "").strip()
    if not ticker or not title:
        return jsonify({"error": "Ticker and title are required"}), 400
    tags = data.get("tags", "")
    if isinstance(tags, list):
        tags = ",".join(tags)
    return jsonify(create_note(ticker, title, data.get("content", ""), tags)), 201


@bp.route("/api/notes/<int:nid>", methods=["PUT"])
def notes_update(nid):
    data = request.get_json()
    tags = data.get("tags")
    if isinstance(tags, list):
        tags = ",".join(tags)
    return jsonify(update_note(nid, data.get("title"), data.get("content"), tags))


@bp.route("/api/notes/<int:nid>", methods=["DELETE"])
def notes_delete(nid):
    delete_note(nid)
    return jsonify({"ok": True})


# --- Snapshots ---

@bp.route("/api/snapshots", methods=["GET"])
def snapshots_list():
    ticker = request.args.get("ticker")
    return jsonify(list_snapshots(ticker))


@bp.route("/api/snapshots", methods=["POST"])
def snapshots_save():
    data = request.get_json()
    ticker = data.get("ticker", "").strip()
    snapshot_data = data.get("data")
    if not ticker or not snapshot_data:
        return jsonify({"error": "Ticker and data are required"}), 400
    return jsonify(save_snapshot(ticker, snapshot_data)), 201


# --- Valuations ---

@bp.route("/api/valuations", methods=["GET"])
def valuations_list():
    ticker = request.args.get("ticker")
    return jsonify(list_valuations(ticker))


@bp.route("/api/valuations", methods=["POST"])
def valuations_save():
    data = request.get_json()
    ticker = data.get("ticker", "").strip()
    model_type = data.get("model_type", "").strip()
    assumptions = data.get("assumptions")
    results = data.get("results")
    if not ticker or not model_type:
        return jsonify({"error": "Ticker and model_type are required"}), 400
    return jsonify(save_valuation(ticker, model_type, assumptions, results)), 201
