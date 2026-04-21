from datetime import datetime, timezone
from functools import wraps

import bcrypt
from bson import ObjectId
from flask import Blueprint, jsonify, request, session

from .db import get_db
from .risk import calculate_risk_score, compute_twr

api = Blueprint("api", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper


def _oid(val):
    try:
        return ObjectId(val)
    except Exception:
        return None


def _serialize_doc(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    for key in ("user_id", "property_id"):
        if key in doc:
            doc[key] = str(doc[key])
    if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
        doc["created_at"] = doc["created_at"].isoformat()
    if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
        doc["timestamp"] = doc["timestamp"].isoformat()
    doc.pop("password_hash", None)
    return doc


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@api.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    result = db.users.insert_one({
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    })
    user_id = str(result.inserted_id)
    session["user_id"] = user_id
    session["user_name"] = name
    return jsonify({"message": "Registered successfully", "user_id": user_id, "name": name}), 201


@api.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    db = get_db()
    user = db.users.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = str(user["_id"])
    session["user_name"] = user["name"]
    return jsonify({"message": "Logged in", "user_id": str(user["_id"]), "name": user["name"]}), 200


@api.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@api.route("/auth/me", methods=["GET"])
def auth_me():
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "user_id": session["user_id"],
            "name": session.get("user_name", ""),
        }), 200
    return jsonify({"authenticated": False}), 200


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@api.route("/properties", methods=["GET"])
def list_properties():
    db = get_db()
    props = list(db.properties.find().sort("created_at", -1))
    result = []
    for prop in props:
        oid = prop["_id"]
        investors  = list(db.investments.find({"property_id": oid}))
        valuations = list(db.valuations.find({"property_id": oid}).sort("date", 1))
        serialized = _serialize_doc(prop)
        serialized["risk"] = calculate_risk_score(prop, investors, valuations)
        result.append(serialized)
    return jsonify(result), 200


@api.route("/properties/<property_id>", methods=["GET"])
def get_property(property_id):
    oid = _oid(property_id)
    if not oid:
        return jsonify({"error": "Invalid property ID"}), 400

    db = get_db()
    prop = db.properties.find_one({"_id": oid})
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    investments = list(db.investments.find({"property_id": oid}))
    investors = []
    for inv in investments:
        user = db.users.find_one({"_id": inv["user_id"]})
        investors.append({
            "user_id": str(inv["user_id"]),
            "name": user["name"] if user else "Unknown",
            "amount": inv["amount"],
            "ownership_share": inv["ownership_share"],
        })

    result = _serialize_doc(prop)
    result["investors"] = investors

    # Appreciation data
    result["current_market_value"] = prop.get("current_market_value", prop["total_value"])
    appreciation = result["current_market_value"] - prop["total_value"]
    result["appreciation"] = appreciation
    result["appreciation_pct"] = round((appreciation / prop["total_value"]) * 100, 2) if prop["total_value"] else 0

    # Valuation history
    valuations = list(db.valuations.find({"property_id": oid}).sort("date", 1))
    result["valuation_history"] = [
        {"date": v["date"].isoformat() if hasattr(v["date"], "isoformat") else str(v["date"]),
         "market_value": v["market_value"]}
        for v in valuations
    ]

    # Distribution history for this property
    distributions = list(
        db.transactions.find({"property_id": oid, "type": "distribute"}).sort("timestamp", -1).limit(20)
    )
    dist_list = []
    for d in distributions:
        user = db.users.find_one({"_id": d["user_id"]})
        dist_list.append({
            "user_name": user["name"] if user else "Unknown",
            "amount": d["amount"],
            "timestamp": d["timestamp"].isoformat() if hasattr(d["timestamp"], "isoformat") else str(d["timestamp"]),
        })
    result["distribution_history"] = dist_list

    # Risk score
    result["risk"] = calculate_risk_score(prop, investors, valuations)

    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Investments
# ---------------------------------------------------------------------------

@api.route("/investments", methods=["POST"])
@login_required
def invest():
    data = request.get_json(silent=True) or {}
    property_id = data.get("property_id")
    amount = data.get("amount")

    if not property_id or amount is None:
        return jsonify({"error": "property_id and amount are required"}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400
    if amount <= 0:
        return jsonify({"error": "amount must be positive"}), 400

    prop_oid = _oid(property_id)
    if not prop_oid:
        return jsonify({"error": "Invalid property ID"}), 400

    db = get_db()
    prop = db.properties.find_one({"_id": prop_oid})
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    remaining = prop["total_value"] - prop["total_pooled_capital"]
    if amount > remaining:
        return jsonify({"error": f"Maximum investment allowed is ${remaining:,.2f}"}), 400

    user_oid = ObjectId(session["user_id"])
    new_total = prop["total_pooled_capital"] + amount
    new_share = amount / new_total

    # Update all existing investments for this property
    existing = list(db.investments.find({"property_id": prop_oid}))
    for inv in existing:
        updated_share = inv["amount"] / new_total
        db.investments.update_one(
            {"_id": inv["_id"]},
            {"$set": {"ownership_share": updated_share}},
        )

    # Check if user already has an investment in this property
    user_inv = db.investments.find_one({"user_id": user_oid, "property_id": prop_oid})
    now = datetime.now(timezone.utc)

    if user_inv:
        new_amount = user_inv["amount"] + amount
        recalc_share = new_amount / new_total
        db.investments.update_one(
            {"_id": user_inv["_id"]},
            {"$set": {"amount": new_amount, "ownership_share": recalc_share, "timestamp": now}},
        )
    else:
        db.investments.insert_one({
            "user_id": user_oid,
            "property_id": prop_oid,
            "amount": amount,
            "ownership_share": new_share,
            "timestamp": now,
        })

    # Update property pooled capital
    db.properties.update_one(
        {"_id": prop_oid},
        {"$set": {"total_pooled_capital": new_total}},
    )

    # Record transaction
    db.transactions.insert_one({
        "user_id": user_oid,
        "property_id": prop_oid,
        "type": "invest",
        "amount": amount,
        "timestamp": now,
    })

    return jsonify({"message": "Investment successful", "new_total": new_total, "ownership_share": new_share}), 201


# ---------------------------------------------------------------------------
# User Portfolio / Dashboard
# ---------------------------------------------------------------------------

@api.route("/users/<user_id>/portfolio", methods=["GET"])
@login_required
def user_portfolio(user_id):
    if session["user_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    user_oid = _oid(user_id)
    if not user_oid:
        return jsonify({"error": "Invalid user ID"}), 400

    db = get_db()
    user = db.users.find_one({"_id": user_oid})
    if not user:
        return jsonify({"error": "User not found"}), 404

    investments = list(db.investments.find({"user_id": user_oid}))
    total_invested = 0
    total_estimated_annual = 0
    total_appreciation = 0
    holdings = []

    for inv in investments:
        prop = db.properties.find_one({"_id": inv["property_id"]})
        if not prop:
            continue
        est_annual = prop["rental_income"] * 12 * inv["ownership_share"]
        market_val = prop.get("current_market_value", prop["total_value"])
        user_market_share = market_val * inv["ownership_share"]
        user_appreciation = (market_val - prop["total_value"]) * inv["ownership_share"]
        total_invested += inv["amount"]
        total_estimated_annual += est_annual
        total_appreciation += user_appreciation
        prop_investors  = list(db.investments.find({"property_id": inv["property_id"]}))
        prop_valuations = list(db.valuations.find({"property_id": inv["property_id"]}).sort("date", 1))
        holdings.append({
            "property_id": str(inv["property_id"]),
            "address": prop["address"],
            "amount_invested": inv["amount"],
            "ownership_share": inv["ownership_share"],
            "estimated_annual_return": round(est_annual, 2),
            "property_total_value": prop["total_value"],
            "current_market_value": market_val,
            "user_market_share": round(user_market_share, 2),
            "user_appreciation": round(user_appreciation, 2),
            "image_url": prop.get("image_url", ""),
            "risk": calculate_risk_score(prop, prop_investors, prop_valuations),
        })

    # Total earnings from distributions
    dist_pipeline = [
        {"$match": {"user_id": user_oid, "type": "distribute"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    dist_result = list(db.transactions.aggregate(dist_pipeline))
    total_distributions = dist_result[0]["total"] if dist_result else 0

    # ROI = (distributions + appreciation) / total_invested
    total_return = total_distributions + total_appreciation
    roi_pct = round((total_return / total_invested) * 100, 2) if total_invested > 0 else 0

    # Time-Weighted Return (Modified Dietz)
    current_portfolio_value = sum(h["user_market_share"] for h in holdings)
    twr_pct = compute_twr(investments, current_portfolio_value, total_distributions)

    # Performance over time: monthly invested totals from transactions
    perf_pipeline = [
        {"$match": {"user_id": user_oid}},
        {"$sort": {"timestamp": 1}},
    ]
    all_tx = list(db.transactions.find({"user_id": user_oid}).sort("timestamp", 1))
    performance_timeline = []
    running_invested = 0
    running_earned = 0
    for tx in all_tx:
        if tx["type"] == "invest":
            running_invested += tx["amount"]
        else:
            running_earned += tx["amount"]
        ts = tx["timestamp"].isoformat() if hasattr(tx["timestamp"], "isoformat") else str(tx["timestamp"])
        performance_timeline.append({
            "date": ts,
            "total_invested": round(running_invested, 2),
            "total_earned": round(running_earned, 2),
        })

    transactions = list(
        db.transactions.find({"user_id": user_oid}).sort("timestamp", -1).limit(50)
    )
    tx_list = []
    for tx in transactions:
        prop = db.properties.find_one({"_id": tx["property_id"]})
        tx_list.append({
            "_id": str(tx["_id"]),
            "property_id": str(tx["property_id"]),
            "address": prop["address"] if prop else "Unknown",
            "type": tx["type"],
            "amount": tx["amount"],
            "timestamp": tx["timestamp"].isoformat() if hasattr(tx["timestamp"], "isoformat") else str(tx["timestamp"]),
        })

    return jsonify({
        "user_name": user["name"],
        "total_invested": round(total_invested, 2),
        "total_estimated_annual": round(total_estimated_annual, 2),
        "total_distributions": round(total_distributions, 2),
        "total_appreciation": round(total_appreciation, 2),
        "roi_pct": roi_pct,
        "twr_pct": twr_pct,
        "holdings": holdings,
        "transactions": tx_list,
        "performance_timeline": performance_timeline,
    }), 200


# ---------------------------------------------------------------------------
# Income Distribution (Admin)
# ---------------------------------------------------------------------------

@api.route("/distributions/<property_id>", methods=["POST"])
@login_required
def distribute_income(property_id):
    prop_oid = _oid(property_id)
    if not prop_oid:
        return jsonify({"error": "Invalid property ID"}), 400

    db = get_db()
    prop = db.properties.find_one({"_id": prop_oid})
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    data = request.get_json(silent=True) or {}
    rental_income = data.get("rental_income", prop.get("rental_income", 0))
    try:
        rental_income = float(rental_income)
    except (TypeError, ValueError):
        return jsonify({"error": "rental_income must be a number"}), 400

    investments = list(db.investments.find({"property_id": prop_oid}))
    if not investments:
        return jsonify({"error": "No investors for this property"}), 400

    now = datetime.now(timezone.utc)
    payouts = []
    for inv in investments:
        payout = rental_income * inv["ownership_share"]
        db.transactions.insert_one({
            "user_id": inv["user_id"],
            "property_id": prop_oid,
            "type": "distribute",
            "amount": round(payout, 2),
            "timestamp": now,
        })
        user = db.users.find_one({"_id": inv["user_id"]})
        payouts.append({
            "user_id": str(inv["user_id"]),
            "name": user["name"] if user else "Unknown",
            "payout": round(payout, 2),
            "ownership_share": inv["ownership_share"],
        })

    return jsonify({"message": "Distribution complete", "rental_income": rental_income, "payouts": payouts}), 200


# ---------------------------------------------------------------------------
# Property Valuation Update (Admin)
# ---------------------------------------------------------------------------

@api.route("/properties/<property_id>/valuation", methods=["POST"])
@login_required
def update_valuation(property_id):
    prop_oid = _oid(property_id)
    if not prop_oid:
        return jsonify({"error": "Invalid property ID"}), 400

    db = get_db()
    prop = db.properties.find_one({"_id": prop_oid})
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    data = request.get_json(silent=True) or {}
    new_value = data.get("market_value")
    if new_value is None:
        return jsonify({"error": "market_value is required"}), 400
    try:
        new_value = float(new_value)
    except (TypeError, ValueError):
        return jsonify({"error": "market_value must be a number"}), 400
    if new_value <= 0:
        return jsonify({"error": "market_value must be positive"}), 400

    now = datetime.now(timezone.utc)

    # Update property's current market value
    db.properties.update_one(
        {"_id": prop_oid},
        {"$set": {"current_market_value": new_value}},
    )

    # Record in valuations collection
    db.valuations.insert_one({
        "property_id": prop_oid,
        "market_value": new_value,
        "date": now,
    })

    old_value = prop.get("current_market_value", prop["total_value"])
    change_pct = round(((new_value - old_value) / old_value) * 100, 2) if old_value else 0

    return jsonify({
        "message": "Valuation updated",
        "previous_value": old_value,
        "new_value": new_value,
        "change_pct": change_pct,
    }), 200