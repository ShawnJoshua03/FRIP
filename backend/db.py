import os
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "frip_db")

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[DB_NAME]
        _ensure_indexes(_db)
    return _db


def _ensure_indexes(db):
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.investments.create_index([("user_id", ASCENDING)])
    db.investments.create_index([("property_id", ASCENDING)])
    db.transactions.create_index([("user_id", ASCENDING)])
    db.transactions.create_index([("property_id", ASCENDING)])
    db.valuations.create_index([("property_id", ASCENDING), ("date", ASCENDING)])


def seed_properties():
    db = get_db()
    now = datetime.now(timezone.utc)
    from datetime import timedelta

    # Idempotent: only insert properties whose address isn't in the DB yet
    existing_addresses = {p["address"] for p in db.properties.find({}, {"address": 1})}

    all_properties = [
        # ── LOW risk: 90% funded, steady appreciation, healthy yield ──────
        {
            "address": "742 Evergreen Terrace, Portland, OR 97205",
            "description": (
                "A beautifully renovated 4-bedroom craftsman home in Portland's "
                "coveted Nob Hill neighborhood. Features original hardwood floors, "
                "a chef's kitchen with quartz countertops, and a landscaped backyard "
                "with a detached ADU currently rented at $1,200/month. Walking "
                "distance to restaurants, shops, and transit. Strong rental demand "
                "in this area makes it ideal for steady cash-flow returns."
            ),
            "total_value": 485000,
            "current_market_value": 502000,
            "total_pooled_capital": 147200,
            "expected_annual_return": 8.4,
            "rental_income": 3400,
            "image_url": "/static/placeholder-house-1.svg",
            "created_at": now,
            # Valuation history: very steady upward trend (+3.5% over 6 months)
            "_valuation_history": [485000, 487000, 490000, 493000, 497000, 502000],
        },
        {
            "address": "1500 Lake Shore Dr, Unit 12B, Chicago, IL 60610",
            "description": (
                "Luxury 2-bedroom condo on Chicago's Gold Coast with panoramic "
                "Lake Michigan views. The building offers a doorman, rooftop deck, "
                "fitness center, and heated parking. Recently updated with smart-home "
                "tech and designer finishes. Located minutes from Magnificent Mile "
                "shopping and Lincoln Park. High occupancy rate with corporate "
                "tenants and short-term rental potential."
            ),
            "total_value": 620000,
            "current_market_value": 641000,
            "total_pooled_capital": 310000,
            "expected_annual_return": 7.1,
            "rental_income": 4200,
            "image_url": "/static/placeholder-house-2.svg",
            "created_at": now,
            # Valuation history: steady appreciation (+3.4% over 6 months)
            "_valuation_history": [620000, 622000, 625000, 629000, 635000, 641000],
        },
        # ── MEDIUM risk: 15% funded, strong appreciation, higher yield ────
        {
            "address": "88 Magnolia Blvd, Austin, TX 78701",
            "description": (
                "Modern duplex in East Austin's booming tech corridor. Each unit "
                "features 3 bedrooms, open-concept living, and private patios. "
                "Both units are currently leased at above-market rates to long-term "
                "tenants. The property sits on a double lot with room for future "
                "development. Austin's rapid population growth and limited housing "
                "supply position this asset for strong appreciation."
            ),
            "total_value": 540000,
            "current_market_value": 571000,
            "total_pooled_capital": 81000,
            "expected_annual_return": 9.2,
            "rental_income": 5100,
            "image_url": "/static/placeholder-house-3.svg",
            "created_at": now,
            # Valuation history: strong but slightly uneven appreciation (+5.7%)
            "_valuation_history": [540000, 544000, 550000, 557000, 562000, 571000],
        },
        # ── LOW risk: 90% funded, very stable prices, solid yield ─────────
        {
            "address": "1847 Larimer St, Denver, CO 80202",
            "description": (
                "Fully renovated Victorian row house in Denver's vibrant LoDo "
                "district. Steps from Union Station, the city's best restaurants, "
                "and the 16th Street Mall. Currently operating as a premium "
                "short-term rental with 92% occupancy. The neighbourhood's ongoing "
                "commercial development continues to underpin strong demand and "
                "consistent value growth."
            ),
            "total_value": 410000,
            "current_market_value": 428000,
            "total_pooled_capital": 369000,
            "expected_annual_return": 8.1,
            "rental_income": 3100,
            "image_url": "/static/placeholder-house-1.svg",
            "created_at": now,
            # Valuation history: very stable month-to-month (+4.4% over 6 months)
            "_valuation_history": [410000, 413000, 415000, 419000, 422000, 428000],
        },
        # ── MEDIUM risk: 30% funded, moderate volatility ──────────────────
        {
            "address": "347 Broadway, Nashville, TN 37201",
            "description": (
                "Three-unit mixed-use building one block from Broadway's famous "
                "honky-tonk row. Ground floor is leased to a long-term retail "
                "tenant; the two upper apartments are furnished and listed on "
                "short-term rental platforms. Nashville's tourism boom and corporate "
                "relocations drive year-round occupancy. Significant upside from "
                "potential conversion to boutique hospitality."
            ),
            "total_value": 540000,
            "current_market_value": 558000,
            "total_pooled_capital": 162000,
            "expected_annual_return": 7.4,
            "rental_income": 3600,
            "image_url": "/static/placeholder-house-2.svg",
            "created_at": now,
            # Valuation history: moderate volatility, choppy upward trend (+3.3%)
            "_valuation_history": [540000, 548000, 543000, 551000, 557000, 558000],
        },
        # ── HIGH risk: 12% funded, volatile prices, depreciating ──────────
        {
            "address": "220 W Congress St, Detroit, MI 48226",
            "description": (
                "Four-unit apartment building in Detroit's downtown core, adjacent "
                "to the newly revitalised Campus Martius district. High gross yield "
                "reflects the market's current volatility and the city's uneven "
                "recovery. Units are fully occupied with month-to-month leases. "
                "Suitable for investors seeking high income with tolerance for "
                "price risk and a longer recovery horizon."
            ),
            "total_value": 195000,
            "current_market_value": 172000,
            "total_pooled_capital": 23400,
            "expected_annual_return": 13.5,
            "rental_income": 1600,
            "image_url": "/static/placeholder-house-3.svg",
            "created_at": now,
            # Valuation history: high volatility with clear downtrend (-11.8%)
            "_valuation_history": [195000, 185000, 193000, 180000, 190000, 172000],
        },
    ]

    new_props = [p for p in all_properties if p["address"] not in existing_addresses]
    if not new_props:
        return

    # Strip the helper key before inserting
    valuation_histories = [p.pop("_valuation_history") for p in new_props]

    result = db.properties.insert_many(new_props)

    # Seed 6-month valuation history for each new property
    valuations = []
    for i, prop_id in enumerate(result.inserted_ids):
        for month_offset, market_value in enumerate(valuation_histories[i]):
            date = now - timedelta(days=(5 - month_offset) * 30)
            valuations.append({
                "property_id": prop_id,
                "market_value": market_value,
                "date": date,
            })
    db.valuations.insert_many(valuations)
    print(f"[seed] Inserted {len(new_props)} properties + {len(valuations)} valuations.")