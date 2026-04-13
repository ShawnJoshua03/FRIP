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
    if db.properties.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc)

    sample_properties = [
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
        },
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
        },
    ]
    result = db.properties.insert_many(sample_properties)

    # Seed appreciation history (6 months of valuation data per property)
    from datetime import timedelta
    base_values = [485000, 620000, 540000]
    appreciation_rates = [
        [1.0, 1.005, 1.012, 1.018, 1.028, 1.035],  # Portland: +3.5%
        [1.0, 1.003, 1.008, 1.015, 1.024, 1.034],  # Chicago: +3.4%
        [1.0, 1.008, 1.018, 1.030, 1.042, 1.057],  # Austin: +5.7%
    ]
    valuations = []
    for i, prop_id in enumerate(result.inserted_ids):
        for month_offset, rate in enumerate(appreciation_rates[i]):
            date = now - timedelta(days=(5 - month_offset) * 30)
            valuations.append({
                "property_id": prop_id,
                "market_value": round(base_values[i] * rate),
                "date": date,
            })
    db.valuations.insert_many(valuations)
    print(f"[seed] Inserted {len(sample_properties)} properties + {len(valuations)} valuations.")